"""Trabajo 'views': fotos de planta/alzado/perfil -> .scad -> .stl."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

import cv2

from .views.contours import extract
from .views.rectify import rectify
from .views.scad_writer import build_scad

PX = 10.0
OUT_DIR = Path(os.environ.get("SCAN2PRINT_OUT", Path.home() / "Scan2Print" / "out"))
WEBHOOK = os.environ.get("SCAN2PRINT_WEBHOOK")  # URL que recibe un POST JSON al terminar
PARAM_KEYS = ("ancho", "fondo", "alto", "holgura")  # cotas objetivo (mm) y holgura


def _set(d: Path, **kw):
    job = json.loads((d / "job.json").read_text())
    job.update(kw)
    (d / "job.json").write_text(json.dumps(job, indent=2))


def _export(d: Path, job_id: str) -> dict:
    """Copia el resultado a OUT_DIR con nombre estable (para Orca o tus agentes)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = f"{datetime.now():%Y%m%d-%H%M%S}_{job_id[:8]}"
    files = {}
    for ext in ("stl", "scad"):
        src = d / "output" / f"pieza.{ext}"
        if src.exists():
            files[ext] = str(shutil.copy(src, OUT_DIR / f"{base}.{ext}"))
    return files


def _notify(payload: dict) -> None:
    if not WEBHOOK:
        return
    try:
        req = urllib.request.Request(WEBHOOK, json.dumps(payload).encode(),
                                     {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).close()
    except Exception:
        pass  # el aviso es opcional; nunca rompe el trabajo


def _scale(contours, sx, sy):
    return [[(x * sx, y * sy) for x, y in c] for c in contours]


def _dims(views, altura=None):
    ancho, fondo = (max(p[i] for c in views["planta"] for p in c) for i in (0, 1))
    other = views.get("alzado") or views.get("perfil")
    alto = max(p[1] for c in other for p in c) if other else altura
    return {"ancho": ancho, "fondo": fondo, "alto": alto}


def process_views(d: Path, params: dict | None = None) -> None:
    """Procesa las fotos de `input/`. `params` admite ancho/fondo/alto (cotas medidas
    con calibre, mm; reescalan la pieza) y holgura (offset de contorno, mm)."""
    try:
        params = {k: float(v) for k, v in (params or {}).items() if k in PARAM_KEYS and v not in (None, "")}
        _set(d, status="processing", error=None)
        views = {}
        for p in sorted((d / "input").iterdir()):
            name = p.name.split("_", 1)[0]
            if name in ("planta", "alzado", "perfil"):
                img = cv2.imread(str(p))
                if img is None:
                    raise ValueError(f"no se pudo leer {p.name}")
                views[name] = extract(rectify(img, PX), PX)
        if "planta" not in views:
            raise ValueError("falta la foto de planta")

        detected = _dims(views)
        if detected["alto"] is None:  # solo planta: extrusión plana
            detected["alto"] = params.get("alto", 5.0)
        k = {a: params[a] / detected[a] if a in params and detected[a] else 1.0 for a in ("ancho", "fondo", "alto")}
        views["planta"] = _scale(views["planta"], k["ancho"], k["fondo"])
        if "alzado" in views:
            views["alzado"] = _scale(views["alzado"], k["ancho"], k["alto"])
        if "perfil" in views:
            views["perfil"] = _scale(views["perfil"], k["fondo"], k["alto"])
        altura = detected["alto"] * k["alto"]

        out = d / "output"
        out.mkdir(exist_ok=True)
        scad = build_scad(views["planta"], views.get("alzado"), views.get("perfil"),
                          holgura=params.get("holgura", 0.0), altura=altura)
        (out / "pieza.scad").write_text(scad)
        outputs = ["pieza.scad"]
        (out / "pieza.stl").unlink(missing_ok=True)
        if shutil.which("openscad"):
            subprocess.run(["openscad", "-q", "-o", str(out / "pieza.stl"), str(out / "pieza.scad")],
                           check=True, capture_output=True, timeout=300)
            outputs.append("pieza.stl")
        dims = {a: detected[a] * k[a] for a in k}
        exported = _export(d, d.name)
        _set(d, status="done", outputs=outputs, detected=detected, params=params,
             dims=dims, exported=exported)
        _notify({"event": "job.done", "id": d.name, "dims": dims, "files": exported})
    except Exception as e:  # el estado de error se muestra en la app
        _set(d, status="error", error=str(e))
