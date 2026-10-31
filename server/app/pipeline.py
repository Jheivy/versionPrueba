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


def _set(d: Path, **kw):
    job = json.loads((d / "job.json").read_text())
    job.update(kw)
    (d / "job.json").write_text(json.dumps(job, indent=2))


def process_views(d: Path, holgura: float = 0.0, altura: float | None = None) -> None:
    try:
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
        out = d / "output"
        out.mkdir(exist_ok=True)
        scad = build_scad(views["planta"], views.get("alzado"), views.get("perfil"),
                          holgura=holgura, altura=altura)
        (out / "pieza.scad").write_text(scad)
        outputs = ["pieza.scad"]
        if shutil.which("openscad"):
            subprocess.run(["openscad", "-q", "-o", str(out / "pieza.stl"), str(out / "pieza.scad")],
                           check=True, capture_output=True, timeout=300)
            outputs.append("pieza.stl")
        _set(d, status="done", outputs=outputs)
    except Exception as e:  # el estado de error se muestra en la app
        _set(d, status="error", error=str(e))
