"""Scan2Print hub: recibe fotos desde el móvil y gestiona trabajos de reconstrucción."""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

STORAGE = Path(os.environ.get("SCAN2PRINT_STORAGE", Path.home() / "Scan2Print" / "jobs"))
WEB_DIR = Path(__file__).resolve().parents[2] / "web"
MODES = {"views", "video"}
VIEW_NAMES = {"planta", "alzado", "perfil"}
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")

app = FastAPI(title="Scan2Print")


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
    mode: str = Form(...),
    files: list[UploadFile] = File(...),
    views: str = Form(""),
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
    }
    (STORAGE / job_id / "job.json").write_text(json.dumps(job, indent=2))
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
