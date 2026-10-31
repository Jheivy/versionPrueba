"""Scan2Print hub: recibe fotos desde el móvil y gestiona trabajos de reconstrucción."""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import re
import shutil
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from fastapi import BackgroundTasks, Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import jobs
from .pipeline import process_views
from .pipeline_video import process_video
from .views.contours import NoShapeFound
from .views.detect import analyze
from .views.markers import render_sheet
from .views.preview import render_preview
from .views.rectify import MarkersNotFound

STORAGE = Path(os.environ.get("SCAN2PRINT_STORAGE", Path.home() / "Scan2Print" / "jobs"))
WEB_DIR = Path(__file__).resolve().parents[2] / "web"
MODES = {"views", "video"}
VIEW_NAMES = {"planta", "alzado", "perfil"}
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")

async def _announce(state: dict) -> None:
    """Anuncia scan2print.local por mDNS (si `zeroconf` está instalado) sin bloquear el arranque."""
    try:
        import socket

        from zeroconf import ServiceInfo
        from zeroconf.asyncio import AsyncZeroconf
        port = int(os.environ.get("SCAN2PRINT_PORT", 8443))
        ip = await asyncio.to_thread(socket.gethostbyname, socket.gethostname())
        info = ServiceInfo("_https._tcp.local.", "Scan2Print._https._tcp.local.",
                           addresses=[socket.inet_aton(ip)], port=port, server="scan2print.local.")
        azc = AsyncZeroconf()
        await asyncio.wait_for(azc.async_register_service(info), 5)
        state["azc"], state["info"] = azc, info
    except Exception:
        pass  # el anuncio es opcional


@asynccontextmanager
async def lifespan(_: FastAPI):
    jobs.recover_stale(STORAGE)
    state: dict = {}
    task = asyncio.create_task(_announce(state))
    yield
    task.cancel()
    if "azc" in state:
        await state["azc"].async_unregister_service(state["info"])
        await state["azc"].async_close()


app = FastAPI(title="Scan2Print", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1024)  # JS/CSS/JSON/STL de texto: 3-5x menos bytes por Wi-Fi


def _job_dir(job_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise HTTPException(404, "trabajo no encontrado")
    d = STORAGE / job_id
    if not (d / "job.json").exists():
        raise HTTPException(404, "trabajo no encontrado")
    return d


def _read_job(d: Path) -> dict:
    return jobs.read(d)


BUSY = "El trabajo se está procesando; espera a que termine."


def _enqueue(background: BackgroundTasks, d: Path, fn, *args) -> None:
    """Encola un procesado; 409 si ese trabajo ya tiene uno en curso o en cola."""
    if not jobs.reserve(d):
        raise HTTPException(409, BUSY)
    background.add_task(fn, d, *args)


@app.post("/api/jobs", status_code=201)
async def create_job(
    background: BackgroundTasks,
    mode: str = Form(...),
    files: list[UploadFile] = File(...),
    views: str = Form(""),
    review: str = Form(""),
    name: str = Form(""),
):
    """Sube fotos. En modo 'views', `views` es una lista separada por comas
    (planta,alzado,perfil) en el mismo orden que los ficheros."""
    if mode not in MODES:
        raise HTTPException(400, f"modo inválido; usa uno de {sorted(MODES)}")
    labels = [v.strip() for v in views.split(",")] if views else []
    if mode == "views":
        if len(labels) != len(files) or not set(labels) <= VIEW_NAMES:
            raise HTTPException(400, "indica una vista (planta/alzado/perfil) por fichero")

    job_id = uuid.uuid4().hex
    d = STORAGE / job_id / "input"
    d.mkdir(parents=True)
    saved = []
    for i, f in enumerate(files):
        fname = SAFE_NAME.sub("_", Path(f.filename or f"file{i}").name)
        if labels:
            fname = f"{labels[i]}_{fname}"
        (d / fname).write_bytes(await f.read())
        saved.append(fname)

    job = {
        "id": job_id,
        "mode": mode,
        "status": "uploaded",
        "created": datetime.now(timezone.utc).isoformat(),
        "inputs": saved,
        "outputs": [],
        "name": name.strip()[:60],
        "step": None,
    }
    jobs.write(STORAGE / job_id, job)
    if mode == "views":
        _enqueue(background, STORAGE / job_id, process_views, None, review == "1")
    else:
        _enqueue(background, STORAGE / job_id, process_video)
    return job


@app.get("/api/jobs")
def list_jobs():
    if not STORAGE.exists():
        return []
    jobs = [_read_job(p) for p in STORAGE.iterdir() if (p / "job.json").exists()]
    return sorted(jobs, key=lambda j: j["created"], reverse=True)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    return _read_job(_job_dir(job_id))


@app.post("/api/jobs/{job_id}/params")
def set_params(job_id: str, background: BackgroundTasks, params: dict = Body(...)):
    """views: ancho/fondo/alto/holgura (mm). video: largo (mm) y detalle. Regenera la pieza."""
    d = _job_dir(job_id)
    fn = process_views if _read_job(d)["mode"] == "views" else process_video
    _enqueue(background, d, fn, params)
    return {"status": "queued"}


def _write_job(d: Path, **kw) -> dict:
    return jobs.update(d, **kw)


@app.patch("/api/jobs/{job_id}")
def rename_job(job_id: str, body: dict = Body(...)):
    d = _job_dir(job_id)
    return _write_job(d, name=str(body.get("name", "")).strip()[:60])


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(job_id: str):
    d = _job_dir(job_id)
    if jobs.is_busy(d):
        raise HTTPException(409, BUSY)
    shutil.rmtree(d)


@app.post("/api/jobs/{job_id}/confirm")
def confirm_job(job_id: str, background: BackgroundTasks):
    """Da por buenos los contornos detectados y genera el modelo."""
    d = _job_dir(job_id)
    if _read_job(d)["status"] != "review":
        raise HTTPException(409, "el trabajo no está esperando revisión")
    _enqueue(background, d, process_views, None, False)
    _write_job(d, status="processing", step="modeling")
    return {"status": "queued"}


@app.post("/api/jobs/{job_id}/inputs")
async def replace_view(job_id: str, background: BackgroundTasks, view: str = Form(...), file: UploadFile = File(...)):
    """Sustituye la foto de una vista y vuelve a pedir revisión."""
    d = _job_dir(job_id)
    job = _read_job(d)
    if job["mode"] != "views" or view not in VIEW_NAMES:
        raise HTTPException(400, "vista inválida")
    if not jobs.reserve(d):
        raise HTTPException(409, BUSY)
    inp = d / "input"
    for old in inp.glob(f"{view}_*"):
        old.unlink()
    name = f"{view}_{SAFE_NAME.sub('_', Path(file.filename or 'foto.jpg').name)}"
    (inp / name).write_bytes(await file.read())
    inputs = sorted({*(i for i in job["inputs"] if not i.startswith(f"{view}_")), name})
    _write_job(d, inputs=inputs, status="processing", error=None, error_view=None)
    background.add_task(process_views, d, None, True)  # reservado arriba
    return {"status": "queued"}


@app.get("/api/jobs/{job_id}/preview/{view}.png")
def preview(job_id: str, view: str):
    d = _job_dir(job_id)
    if view not in VIEW_NAMES:
        raise HTTPException(404, "vista inválida")
    for p in sorted((d / "input").glob(f"{view}_*")):
        img = cv2.imread(str(p))
        if img is None:
            break
        try:
            png, info = render_preview(img)
        except (MarkersNotFound, NoShapeFound) as e:
            raise HTTPException(422, "no se detectó la hoja o la pieza") from e
        return Response(png, media_type="image/png", headers={
            "X-Preview-Info": json.dumps(info), "Cache-Control": "no-store"})
    raise HTTPException(404, "no hay foto de esa vista")


@app.get("/api/jobs/{job_id}/thumb.jpg")
def thumb(job_id: str):
    d = _job_dir(job_id)
    t = d / "thumb.jpg"
    if not t.exists():
        for p in sorted((d / "input").iterdir()):
            img = cv2.imread(str(p))
            if img is not None:
                s = 240 / max(img.shape[:2])
                cv2.imwrite(str(t), cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
                break
        else:
            raise HTTPException(404, "sin miniatura")
    return FileResponse(t, headers={"Cache-Control": "max-age=3600"})


@app.post("/api/detect")
async def detect(file: UploadFile = File(...)):
    """Diagnóstico de un fotograma de la cámara (hoja visible, nitidez, luz)."""
    img = cv2.imdecode(np.frombuffer(await file.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "imagen inválida")
    return analyze(img)


@app.get("/api/health")
def health():
    from . import pipeline
    exe = os.environ.get("SCAN2PRINT_OBJECT_CAPTURE") or shutil.which("scan2print-object-capture")
    return {"version": "0.2", "openscad": bool(shutil.which("openscad")),
            "object_capture": sys.platform == "darwin" and bool(exe),
            "storage": str(STORAGE), "out_dir": str(pipeline.OUT_DIR), "webhook": bool(pipeline.WEBHOOK)}


@app.get("/api/marker-sheet.pdf")
def marker_sheet():
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(render_sheet(300)).save(buf, "PDF", resolution=300)
    return Response(buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="scan2print-marcadores.pdf"'})


@app.get("/api/jobs/{job_id}/files/{name}")
def get_file(job_id: str, name: str, request: Request):
    """Con `?v=<rev>` (revisión del trabajo) la respuesta es inmutable: el navegador no vuelve a pedirla."""
    d = _job_dir(job_id)
    for sub in ("output", "input"):
        p = d / sub / SAFE_NAME.sub("_", name)
        if p.is_file():
            cache = "public, max-age=31536000, immutable" if "v" in request.query_params else "no-cache"
            return FileResponse(p, headers={"Cache-Control": cache})
    raise HTTPException(404, "fichero no encontrado")


_SW_CACHE: dict = {}


def _sw_source() -> str:
    """sw.js con la versión y las listas de archivos calculadas a partir de web/ (sin mantenimiento manual).
    VERSION cambia con cualquier edición de la app; las dependencias inmutables (three.js, fuente, iconos)
    tienen su propia versión, así actualizar la app no obliga a volver a bajar three.js."""
    files = sorted(
        p for p in WEB_DIR.rglob("*")
        if p.is_file() and p.name != "sw.js" and p.suffix not in (".md", ".txt"))
    sig = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files)
    if _SW_CACHE.get("sig") != sig:
        rel = [p.relative_to(WEB_DIR).as_posix() for p in files]
        is_vendor = [r.startswith(("vendor/", "fonts/", "icons/")) for r in rel]
        shell = [r for r, v in zip(rel, is_vendor, strict=True) if not v]
        vendor = [r for r, v in zip(rel, is_vendor, strict=True) if v]
        h = hashlib.sha1()
        for r in shell:
            h.update(r.encode())
            h.update((WEB_DIR / r).read_bytes())
        hv = hashlib.sha1("\n".join(vendor).encode()).hexdigest()[:10]
        src = (WEB_DIR / "sw.js").read_text()
        src = src.replace('"/*VERSION*/dev"', json.dumps(h.hexdigest()[:10]))
        src = src.replace('"/*VENDOR*/dev"', json.dumps(hv))
        src = src.replace("/*SHELL*/[]", json.dumps(["./", *shell]))
        src = src.replace("/*VENDORLIST*/[]", json.dumps(vendor))
        _SW_CACHE.update(sig=sig, src=src)
    return _SW_CACHE["src"]


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return Response(_sw_source(), media_type="text/javascript", headers={"Cache-Control": "no-cache"})


class WebFiles(StaticFiles):
    """La PWA: lo versionado por nombre (vendor/, fonts/) es inmutable; el resto se revalida con ETag
    (un 304 casi gratis), así una actualización llega sin vaciar cachés."""

    IMMUTABLE = ("vendor/", "fonts/")

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            long = path.startswith(self.IMMUTABLE)
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable" if long else "no-cache"
        return response


if WEB_DIR.exists():
    app.mount("/", WebFiles(directory=WEB_DIR, html=True), name="web")
