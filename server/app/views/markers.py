"""Hoja A4 con 4 marcadores ArUco en las esquinas (posiciones conocidas en mm)."""
from __future__ import annotations

import cv2
import numpy as np

A4_W, A4_H = 210.0, 297.0   # mm
MARKER_MM = 30.0            # lado del marcador
MARGIN_MM = 10.0            # distancia al borde de la hoja
DICT = cv2.aruco.DICT_4X4_50


def _dictionary():
    return cv2.aruco.getPredefinedDictionary(DICT)


def marker_corners_mm() -> dict[int, np.ndarray]:
    """Esquinas (TL,TR,BR,BL) de cada marcador en mm, origen arriba-izquierda de la hoja."""
    s, m = MARKER_MM, MARGIN_MM
    origins = {0: (m, m), 1: (A4_W - m - s, m), 2: (A4_W - m - s, A4_H - m - s), 3: (m, A4_H - m - s)}
    return {i: np.array([[x, y], [x + s, y], [x + s, y + s], [x, y + s]], np.float32)
            for i, (x, y) in origins.items()}


def render_sheet(dpi: int = 300) -> np.ndarray:
    px = dpi / 25.4
    img = np.full((round(A4_H * px), round(A4_W * px)), 255, np.uint8)
    side = round(MARKER_MM * px)
    for i, c in marker_corners_mm().items():
        m = cv2.aruco.generateImageMarker(_dictionary(), i, side, borderBits=1)
        x, y = (round(v * px) for v in c[0])
        img[y:y + side, x:x + side] = m
    return img
