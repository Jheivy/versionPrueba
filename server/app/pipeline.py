"""Trabajo 'views': fotos de planta/alzado/perfil -> .scad -> .stl."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import cv2

from .views.contours import extract
from .views.rectify import rectify
from .views.scad_writer import build_scad

PX = 10.0
PARAM_KEYS = ("ancho", "fondo", "alto", "holgura")  # cotas objetivo (mm) y holgura


def _set(d: Path, **kw):
    job = json.loads((d / "job.json").read_text())
    job.update(kw)
    (d / "job.json").write_text(json.dumps(job, indent=2))


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
        _set(d, status="done", outputs=outputs, detected=detected, params=params,
             dims={a: detected[a] * k[a] for a in k})
    except Exception as e:  # el estado de error se muestra en la app
        _set(d, status="error", error=str(e))
