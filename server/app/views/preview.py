"""Imagen de revisión: hoja rectificada con el contorno y los huecos detectados encima."""
from __future__ import annotations

import cv2
import numpy as np

from .contours import extract
from .rectify import rectify

PX = 10.0


def render_preview(image: np.ndarray, max_side: int = 900) -> tuple[bytes, dict]:
    """Devuelve (PNG, info): vista recortada alrededor de la pieza con el contorno exterior
    (azul) y los huecos (naranja) dibujados encima."""
    sheet = rectify(image, PX)
    polys, (ox, oy) = extract(sheet, PX, return_origin=True)
    pts = [np.array([[(ox + x) * PX, (oy - y) * PX] for x, y in p]) for p in polys]  # px en la hoja
    allp = np.concatenate(pts)
    pad = 8 * PX
    x0, y0 = int(max(allp[:, 0].min() - pad, 0)), int(max(allp[:, 1].min() - pad, 0))
    x1, y1 = int(min(allp[:, 0].max() + pad, sheet.shape[1])), int(min(allp[:, 1].max() + pad, sheet.shape[0]))
    crop = sheet[y0:y1, x0:x1]
    crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR) if crop.ndim == 2 else crop.copy()
    for k, p in enumerate(pts):
        poly = np.round(p - [x0, y0]).astype(np.int32)
        cv2.polylines(crop, [poly], True, (235, 111, 31) if k == 0 else (0, 140, 255), 3, cv2.LINE_AA)
    scale = max_side / max(crop.shape[:2])
    if scale < 1:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    outer = np.array(polys[0])
    return cv2.imencode(".png", crop)[1].tobytes(), {
        "ancho": round(float(outer[:, 0].max()), 1), "alto": round(float(outer[:, 1].max()), 1),
        "huecos": len(polys) - 1}
