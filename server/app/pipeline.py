"""Trabajo 'views': fotos de planta/alzado/perfil -> .scad -> .stl."""
from __future__ import annotations

import json
import logging
import math
import os
import re
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import cv2

from . import jobs
from .views import coherence, parallax
from .views.contours import NoShapeFound, extract
from .views.holes import finalize, split_circles
from .views.rectify import MarkersNotFound, rectify
from .views.regularize import regularize_view
from .views.scad_writer import build_scad

log = logging.getLogger("scan2print")
PX = 10.0
OUT_DIR = Path(os.environ.get("SCAN2PRINT_OUT", Path.home() / "Scan2Print" / "out"))
WEBHOOK = os.environ.get("SCAN2PRINT_WEBHOOK")  # URL que recibe un POST JSON al terminar
PARAM_KEYS = ("ancho", "fondo", "alto", "holgura", "enderezar", "unificar", "paralaje")  # cotas, holgura, flags 0/1
HOLE_KEY = re.compile(r"d_(planta|alzado|perfil)_(\d+)")  # Ø medido de un agujero, p. ej. d_planta_1


def _openscad(scad: Path, stl: Path) -> None:
    """Genera el STL; si falla, el motivo real va al registro y al usuario le llega una frase clara."""
    try:
        subprocess.run(["openscad", "-q", "-o", str(stl), str(scad)], check=True, capture_output=True,
                       text=True, timeout=300)
    except subprocess.TimeoutExpired:
        raise RuntimeError("OpenSCAD tardó más de 5 minutos: la pieza es demasiado compleja. "
                           "Prueba con «Enderezar contornos» o una foto más limpia.") from None
    except subprocess.CalledProcessError as e:
        lines = [x for x in (e.stderr or "").strip().splitlines() if x.strip()]
        log.error("OpenSCAD falló (código %s):\n%s", e.returncode, "\n".join(lines[-15:]))
        raise RuntimeError("OpenSCAD no pudo generar el STL" + (f": {lines[-1][:160]}" if lines else "")
                           + ". Los detalles están en el registro del servidor.") from None


def _set(d: Path, **kw):
    jobs.update(d, **kw)


def _export(d: Path, job_id: str) -> dict:
    """Copia el resultado a OUT_DIR con nombre estable (para Orca o tus agentes)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob(f"*_{job_id[:8]}.*"):     # una regeneración sustituye a la exportación anterior
        if old.suffix in (".stl", ".scad"):
            old.unlink(missing_ok=True)
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


def _step(d: Path, step: str) -> None:
    _set(d, step=step)


STEP_LABELS = {  # para la interfaz
    "rectifying": "Corrigiendo perspectiva", "contours": "Detectando contornos", "review": "Esperando tu revisión",
    "modeling": "Generando el modelo", "exporting": "Exportando STL",
    "frames": "Eligiendo fotogramas", "reconstruction": "Reconstruyendo en 3D", "cleaning": "Limpiando la malla",
}


class ViewError(ValueError):
    """Error atribuible a una foto concreta (la interfaz ofrece repetirla)."""

    def __init__(self, view: str, msg: str):
        super().__init__(msg)
        self.view = view


def _scale(contours, sx, sy):
    return [[(x * sx, y * sy) for x, y in c] for c in contours]


def _scale_circles(circles, sx, sy):
    # el contorno pasa por los píxeles del borde del material: el hueco sale ~1 píxel (0,1 mm) más grande
    return [(cx * sx, cy * sy, (d - 1 / PX) * math.sqrt(sx * sy)) for cx, cy, d in circles]


def _fix_parallax(views, circles, origins, poses, params) -> dict:
    """Deshace el agrandamiento por perspectiva de la cara superior (ver views/parallax.py). Modifica
    `views` y `circles` y devuelve, por vista, la distancia de la cámara y el factor aplicado."""
    raw = coherence.sizes(views)
    known = {dim: params[dim] for dim in ("ancho", "fondo", "alto") if dim in params}   # cotas medidas con calibre
    dims = {}
    for _ in range(3):   # la profundidad de cada vista sale de las otras: se refina en pocas vueltas
        ks = {}
        for v, pose in poses.items():
            depth = parallax.depths({**dims, **known}).get(v, 0.0)
            ks[v] = (parallax.factor(depth, pose["dist"]) if pose and depth else None) or 1.0
        fixed = {v: (raw[v][0] * ks[v], raw[v][1] * ks[v]) for v in raw}
        dims = {dim: sum(x for _, x in vals) / len(vals)
                for dim, vals in coherence.shared_dims(fixed).items() if vals}
    info = {}
    for v, k in ks.items():
        pose = poses[v]
        if pose is None:
            continue
        info[v] = {"dist": round(pose["dist"]), "factor": round(k, 3)}
        if k != 1.0:
            views[v], circles[v] = parallax.correct(views[v], circles[v], origins[v], pose["nadir"], k)
    return info


def process_views(d: Path, params: dict | None = None, pause_for_review: bool = False) -> None:
    """Procesa las fotos de `input/`. `params` admite ancho/fondo/alto (cotas medidas
    con calibre, mm; reescalan la pieza) y holgura (offset de contorno, mm)."""
    with jobs.running(d):
        try:
            params = {k: float(v) for k, v in (params or {}).items()
                      if (k in PARAM_KEYS or HOLE_KEY.fullmatch(k)) and v not in (None, "")}
            _set(d, status="processing", error=None, error_view=None)
            views, circles, origins, poses = {}, {}, {}, {}
            for p in sorted((d / "input").iterdir()):
                name = p.name.split("_", 1)[0]
                if name in ("planta", "alzado", "perfil"):
                    img = cv2.imread(str(p))
                    if img is None:
                        raise ViewError(name, f"No se pudo leer la foto de {name}. Vuelve a hacerla.")
                    _step(d, "rectifying")
                    try:
                        sheet, h_mm = rectify(img, PX, return_h=True)
                    except MarkersNotFound:
                        raise ViewError(name, f"No vi la hoja de marcadores en la foto de {name}. "
                                              "Encuádrala entera y con buena luz.")
                    _step(d, "contours")
                    try:
                        polys, origins[name] = extract(sheet, PX, return_origin=True)
                        views[name], circles[name] = split_circles(polys)
                        poses[name] = parallax.camera_pose(h_mm, img.shape, parallax.focal_35(p))
                    except NoShapeFound:
                        raise ViewError(name, f"No encontré la pieza en la foto de {name}. "
                                              "Colócala sobre la hoja con fondo claro.")
            if "planta" not in views:
                raise ViewError("planta", "Falta la foto de planta.")
            info = {}
            if parallax.enabled() and params.get("paralaje", 1.0) != 0:
                info = _fix_parallax(views, circles, origins, poses, params)
            if params.get("enderezar", 1.0) != 0:  # antes de medir: las revisiones y el modelo ven lo mismo
                for name in views:
                    views[name], (dx, dy) = regularize_view(views[name])
                    circles[name] = [(cx - dx, cy - dy, dm) for cx, cy, dm in circles[name]]
            sizes = coherence.sizes(views)
            if pause_for_review:
                _set(d, status="review", step="review", warnings=coherence.check(sizes), parallax=info)
                return
            _step(d, "modeling")

            shared = coherence.shared_dims(sizes)
            # sin cota ni unificación el sólido es la intersección: manda la vista más pequeña
            detected = {dim: min(v for _, v in vals) if vals else None for dim, vals in shared.items()}
            if detected["alto"] is None:  # solo planta: extrusión plana
                detected["alto"] = params.get("alto", 5.0)
            target = coherence.targets(sizes, params, unify=params.get("unificar", 0.0) != 0)
            factors = {}  # cada vista se ajusta a la medida final desde SU propio tamaño
            for view, (dx_, dy_) in coherence.VIEW_AXES.items():
                if view in views:
                    own = sizes[view]
                    factors[view] = tuple(target[dim] / own[i] if dim in target and own[i] else 1.0
                                          for i, dim in enumerate((dx_, dy_)))
                    views[view] = _scale(views[view], *factors[view])
            altura = target.get("alto", detected["alto"])
            final, holes = {}, []
            for view, cs in circles.items():
                final[view] = []
                for n, (cx, cy, dm) in enumerate(_scale_circles(cs, *factors[view]), 1):
                    measured = params.get(f"d_{view}_{n}")
                    diam, std = finalize(measured if measured else dm)
                    final[view].append((cx, cy, diam, std))
                    holes.append({"view": view, "n": n, "diam": diam, "x": round(cx, 2), "y": round(cy, 2), "std": std})
            warnings = coherence.check(coherence.sizes(views))  # lo que siga sin cuadrar tras ajustar

            out = d / "output"
            out.mkdir(exist_ok=True)
            scad = build_scad(views["planta"], views.get("alzado"), views.get("perfil"),
                              holgura=params.get("holgura", 0.0), altura=altura, circles=final)
            (out / "pieza.scad").write_text(scad)
            outputs = ["pieza.scad"]
            (out / "pieza.stl").unlink(missing_ok=True)
            _step(d, "exporting")
            if shutil.which("openscad"):
                _openscad(out / "pieza.scad", out / "pieza.stl")
                outputs.append("pieza.stl")
            dims = {dim: target.get(dim, detected[dim]) for dim in detected}
            exported = _export(d, d.name)
            rev = time.time_ns() // 1_000_000  # nueva revisión: invalida las cachés del navegador
            _set(d, status="done", rev=rev, step=None, outputs=outputs, detected=detected, params=params,
                 dims=dims, holes=holes, warnings=warnings, parallax=info, exported=exported)
            _notify({"event": "job.done", "id": d.name, "dims": dims, "files": exported})
        except ViewError as e:
            _set(d, status="error", step=None, error=str(e), error_view=e.view)
        except Exception as e:  # el estado de error se muestra en la app
            log.exception("el trabajo %s falló", d.name)
            _set(d, status="error", step=None, error=str(e) or type(e).__name__, error_view=None)
