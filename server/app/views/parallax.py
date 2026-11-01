"""Corrección de paralaje.

La hoja se rectifica con el plano del papel, pero la cara superior de la pieza está más cerca de la cámara
y se ve más grande: un punto a altura h de una cámara a distancia D (sobre el papel) aparece alejado del
punto nadir de la cámara por un factor D / (D - h). Con la cámara a 30 cm y una pieza de 4 cm son un 15 %.

Aquí se estima D y el nadir a partir de la homografía de la hoja (intrínsecos: EXIF o un valor típico de
móvil) y se deshace ese factor con la profundidad de la pieza en esa vista, que sale de las otras vistas.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np

DEFAULT_F35 = 26.0            # distancia focal equivalente a 35 mm de un móvil típico (cámara principal)
DIAG_35 = 43.27               # diagonal de un fotograma de 35 mm, en mm
MIN_DIST, MAX_DIST = 80.0, 3000.0     # distancias creíbles cámara-papel (mm)
MAX_RATIO = 0.4               # no se corrige si la pieza ocupa más de este tanto de la distancia
VIEW_DEPTH = {"planta": "alto", "alzado": "fondo", "perfil": "ancho"}   # dimensión que va hacia la cámara


def enabled() -> bool:
    return os.environ.get("SCAN2PRINT_PARALLAX", "on").strip().lower() not in ("off", "0", "false", "no")


def focal_35(path: Path | str) -> float | None:
    """Focal equivalente a 35 mm leída del EXIF, si la foto la trae."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            v = im.getexif().get_ifd(0x8769).get(0xA405)      # FocalLengthIn35mmFilm
        return float(v) if v else None
    except Exception:
        return None


def camera_pose(h_mm: np.ndarray, shape: tuple[int, int], f35: float | None = None) -> dict | None:
    """Distancia cámara-papel (mm) y punto nadir (x, y en mm sobre la hoja) a partir de la homografía
    imagen -> hoja en mm. None si el resultado no es creíble."""
    h, w = shape[:2]
    f = (f35 or DEFAULT_F35) / DIAG_35 * math.hypot(w, h)
    K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])
    try:
        M = np.linalg.inv(K) @ np.linalg.inv(h_mm)            # hoja -> rayos de cámara
    except np.linalg.LinAlgError:
        return None
    lam = 1 / np.linalg.norm(M[:, 0])
    r1, r2, t = lam * M[:, 0], lam * M[:, 1], lam * M[:, 2]
    if t[2] < 0:
        r1, r2, t = -r1, -r2, -t
    R = np.stack([r1, r2, np.cross(r1, r2)], axis=1)
    c = -R.T @ t                                              # centro de la cámara en coordenadas de la hoja
    dist = abs(float(c[2]))
    if not (MIN_DIST <= dist <= MAX_DIST) or not np.isfinite(c).all():
        return None
    return {"dist": dist, "nadir": (float(c[0]), float(c[1]))}


def factor(depth: float, dist: float) -> float | None:
    """Factor (<1) que hay que aplicar a lo medido en esa vista; None si no es fiable."""
    if dist <= 0 or depth / dist > MAX_RATIO:
        return None
    return 1 - max(depth, 0.0) / dist


def depths(dims: dict[str, float]) -> dict[str, float]:
    return {view: dims.get(d, 0.0) for view, d in VIEW_DEPTH.items()}


def correct(contours, circles, origin, nadir, k):
    """Escala contornos y círculos (mm, origen en la caja de la pieza, y hacia arriba) por `k` respecto al
    nadir, y los devuelve reencajados en (0, 0). `origin` = (x0, y1): posición de esa caja sobre la hoja."""
    x0, y1 = origin
    nx, ny = nadir

    def fwd(x, y):                       # caja -> hoja (y hacia abajo) -> escalado respecto al nadir
        sx, sy = x + x0, y1 - y
        return nx + k * (sx - nx), ny + k * (sy - ny)

    pts = [[fwd(x, y) for x, y in c] for c in contours]
    minx = min(p[0] for p in pts[0])
    maxy = max(p[1] for p in pts[0])
    back = lambda sx, sy: (sx - minx, maxy - sy)       # noqa: E731
    out = [[back(*p) for p in c] for c in pts]
    circ = []
    for cx, cy, d in circles:
        sx, sy = fwd(cx, cy)
        circ.append((*back(sx, sy), d * k))
    return out, circ
