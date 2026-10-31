"""Trabajo 'video': vídeo/fotos -> Object Capture (Mac) -> malla limpia -> .stl."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .photogrammetry.frames import extract_frames
from .photogrammetry.mesh import postprocess
from .pipeline import _export, _notify, _set, _step

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic"}


def run_object_capture(frames_dir: Path, out_dir: Path, detail: str = "medium") -> Path:
    """Lanza el CLI de Swift (mac/ObjectCaptureCLI). Devuelve el .obj generado."""
    exe = os.environ.get("SCAN2PRINT_OBJECT_CAPTURE") or shutil.which("scan2print-object-capture")
    if sys.platform != "darwin" or not exe:
        raise RuntimeError("Object Capture solo está disponible en el Mac: compila mac/ObjectCaptureCLI "
                           "y define SCAN2PRINT_OBJECT_CAPTURE con su ruta")
    subprocess.run([exe, str(frames_dir), str(out_dir), detail], check=True, timeout=3600,
                   capture_output=True)
    objs = sorted(out_dir.rglob("*.obj"))
    if not objs:
        raise RuntimeError("Object Capture no generó ningún .obj")
    return objs[0]


def _cached_obj(d: Path, detalle: str) -> Path | None:
    """Devuelve el .obj guardado si existe y se hizo con el mismo nivel de detalle."""
    meta = d / "work" / "obj.json"
    try:
        info = json.loads(meta.read_text())
    except (OSError, ValueError):
        return None
    obj = d / "work" / "obj" / info["file"]
    return obj if info["detalle"] == detalle and obj.exists() else None


def _store_obj(d: Path, src_dir: Path, obj: Path, detalle: str) -> Path:
    dst = d / "work" / "obj"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src_dir, dst)
    rel = obj.relative_to(src_dir)
    (d / "work" / "obj.json").write_text(json.dumps({"file": str(rel), "detalle": detalle}))
    return dst / rel


def process_video(d: Path, params: dict | None = None) -> None:
    """`params`: largo (mm, dimensión más larga medida con calibre), detalle (preview/reduced/medium/full)."""
    try:
        params = dict(params or {})
        _set(d, status="processing", error=None)
        detalle = str(params.get("detalle", "medium"))
        out = d / "output"
        out.mkdir(exist_ok=True)
        obj = _cached_obj(d, detalle)  # reescalar no repite la reconstrucción
        if obj is None:
            _step(d, "frames")
            inputs = sorted((d / "input").iterdir())
            images = [p for p in inputs if p.suffix.lower() in IMAGE_EXT]
            with tempfile.TemporaryDirectory() as tmp:
                frames = Path(tmp) / "frames"
                if images:
                    frames.mkdir()
                    for p in images:
                        shutil.copy(p, frames / p.name)
                else:
                    extract_frames(inputs[0], frames)
                _step(d, "reconstruction")
                built = run_object_capture(frames, Path(tmp) / "obj", detalle)
                obj = _store_obj(d, built.parent, built, detalle)
        largo = float(params["largo"]) if params.get("largo") not in (None, "") else None
        _step(d, "cleaning")
        info = postprocess(obj, out / "pieza.stl", largo_mm=largo)
        _step(d, "exporting")
        dims = {k: info[k] for k in ("ancho", "fondo", "alto")}
        exported = _export(d, d.name)
        _set(d, status="done", step=None, outputs=["pieza.stl"], params={k: v for k, v in params.items() if k in ("largo", "detalle")},
             dims=dims, mesh={k: info[k] for k in ("watertight", "triangles", "scale_estimated")}, exported=exported)
        _notify({"event": "job.done", "id": d.name, "dims": dims, "files": exported})
    except Exception as e:
        _set(d, status="error", step=None, error=str(e))
