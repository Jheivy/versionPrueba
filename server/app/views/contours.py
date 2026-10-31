"""Extrae el contorno de la pieza (y sus huecos) de una hoja rectificada, en mm."""
from __future__ import annotations

import cv2
import numpy as np

from .markers import MARGIN_MM, MARKER_MM, marker_corners_mm


class NoShapeFound(Exception):
    pass


def extract(sheet: np.ndarray, px_per_mm: float = 10.0, min_area_mm2: float = 25.0,
            epsilon_mm: float = 0.15):
    """Devuelve [exterior, hueco1, ...] como listas de (x, y) en mm, con el origen en
    la esquina inferior izquierda de la caja de la pieza (eje y hacia arriba)."""
    gray = sheet if sheet.ndim == 2 else cv2.cvtColor(sheet, cv2.COLOR_BGR2GRAY)
    gray = gray.copy()
    pad = 2.0
    for c in marker_corners_mm().values():  # borra los marcadores
        x0, y0 = (c.min(axis=0) - pad) * px_per_mm
        x1, y1 = (c.max(axis=0) + pad) * px_per_mm
        gray[max(int(y0), 0):int(y1), max(int(x0), 0):int(x1)] = 255
    gray = cv2.GaussianBlur(gray, (0, 0), 0.3 * px_per_mm / 3)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    found, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        raise NoShapeFound("no se encontró ninguna pieza en la hoja")
    hier = hier[0]
    px2 = px_per_mm ** 2
    outer = [i for i, h in enumerate(hier) if h[3] == -1 and cv2.contourArea(found[i]) / px2 >= min_area_mm2]
    if not outer:
        raise NoShapeFound("no se encontró ninguna pieza en la hoja")
    best = max(outer, key=lambda i: cv2.contourArea(found[i]))
    holes = [i for i, h in enumerate(hier) if h[3] == best and cv2.contourArea(found[i]) / px2 >= 4.0]

    polys = []
    for i in [best] + holes:
        ap = cv2.approxPolyDP(found[i], epsilon_mm * px_per_mm, True).reshape(-1, 2) / px_per_mm
        polys.append(ap)
    x0, y1 = polys[0][:, 0].min(), polys[0][:, 1].max()
    return [[(float(x - x0), float(y1 - y)) for x, y in p] for p in polys]
