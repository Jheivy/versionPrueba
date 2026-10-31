"""Scan2Print hub: recibe fotos desde el móvil y gestiona trabajos de reconstrucción."""
from __future__ import annotations

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

from fastapi import Body, BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
import cv2
import numpy as np
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .pipeline import process_views
from .pipeline_video import process_video
from .views.detect import analyze
from .views.markers import render_sheet
from .views.preview import render_preview
from .views.rectify import MarkersNotFound
from .views.contours import NoShapeFound

STORAGE = Path(os.environ.get("SCAN2PRINT_STORAGE", Path.home() / "Scan2Print" / "jobs"))
WEB_DIR = Path(__file__).resolve().parents[2] / "web"
MODES = {"views", "video"}
VIEW_NAMES = {"planta", "alzado", "perfil"}
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Anuncia scan2print.local por mDNS si `zeroconf` está instalado."""
    zc = info = None
    try:
        import socket

        from zeroconf import ServiceInfo, Zeroconf
        port = int(os.environ.get("SCAN2PRINT_PORT", 8443))
        ip = socket.gethostbyname(socket.gethostname())
        info = ServiceInfo("_https._tcp.local.", "Scan2Print._https._tcp.local.",
                           addresses=[socket.inet_aton(ip)], port=port, server="scan2print.local.")
        zc = Zeroconf()
        zc.register_service(info)
    except Exception:
        zc = None
    yield
    if zc:
        zc.unregister_service(info)
        zc.close()


app = FastAPI(title="Scan2Print", lifespan=lifespan)


def _job_dir(job_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise HTTPException(404, "trabajo no encontrado")
    d = STORAGE / job_id
    if not (d / "job.json").exists():
        raise HTTPException(404, "trabajo no encontrado")
    return d


def _read_job(d: Path) -> dict:
    return json.loads((d / "job.json").read_text())


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
        name = SAFE_NAME.sub("_", Path(f.filename or f"file{i}").name)
        if labels:
            name = f"{labels[i]}_{name}"
        (d / name).write_bytes(await f.read())
        saved.append(name)

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
    (STORAGE / job_id / "job.json").write_text(json.dumps(job, indent=2))
    if mode == "views":
        background.add_task(process_views, STORAGE / job_id, None, review == "1")
    else:
        background.add_task(process_video, STORAGE / job_id)
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
    background.add_task(fn, d, params)
    return {"status": "queued"}


def _write_job(d: Path, **kw) -> dict:
    job = _read_job(d)
    job.update(kw)
    (d / "job.json").write_text(json.dumps(job, indent=2))
    return job


@app.patch("/api/jobs/{job_id}")
def rename_job(job_id: str, body: dict = Body(...)):
    d = _job_dir(job_id)
    return _write_job(d, name=str(body.get("name", "")).strip()[:60])


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(job_id: str):
    shutil.rmtree(_job_dir(job_id))


@app.post("/api/jobs/{job_id}/confirm")
def confirm_job(job_id: str, background: BackgroundTasks):
    """Da por buenos los contornos detectados y genera el modelo."""
    d = _job_dir(job_id)
    if _read_job(d)["status"] != "review":
        raise HTTPException(409, "el trabajo no está esperando revisión")
    _write_job(d, status="processing", step="modeling")
    background.add_task(process_views, d, None, False)
    return {"status": "queued"}


@app.post("/api/jobs/{job_id}/inputs")
async def replace_view(job_id: str, background: BackgroundTasks, view: str = Form(...), file: UploadFile = File(...)):
    """Sustituye la foto de una vista y vuelve a pedir revisión."""
    d = _job_dir(job_id)
    job = _read_job(d)
    if job["mode"] != "views" or view not in VIEW_NAMES:
        raise HTTPException(400, "vista inválida")
    inp = d / "input"
    for old in inp.glob(f"{view}_*"):
        old.unlink()
    name = f"{view}_{SAFE_NAME.sub('_', Path(file.filename or 'foto.jpg').name)}"
    (inp / name).write_bytes(await file.read())
    inputs = sorted({*(i for i in job["inputs"] if not i.startswith(f"{view}_")), name})
    _write_job(d, inputs=inputs, status="processing", error=None, error_view=None)
    background.add_task(process_views, d, None, True)
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
def get_file(job_id: str, name: str):
    d = _job_dir(job_id)
    for sub in ("output", "input"):
        p = d / sub / SAFE_NAME.sub("_", name)
        if p.is_file():
            return FileResponse(p)
    raise HTTPException(404, "fichero no encontrado")


if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
