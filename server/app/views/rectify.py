"""Detecta la hoja de marcadores y devuelve la vista cenital con escala en mm."""
from __future__ import annotations

import cv2
import numpy as np

from .markers import A4_H, A4_W, DICT, marker_corners_mm


class MarkersNotFound(Exception):
    pass


def rectify(image: np.ndarray, px_per_mm: float = 10.0, min_markers: int = 2) -> np.ndarray:
    """Devuelve la hoja A4 completa rectificada: 1 mm = `px_per_mm` píxeles."""
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(DICT), cv2.aruco.DetectorParameters())
    corners, ids, _ = det.detectMarkers(image)
    ref = marker_corners_mm()
    src, dst = [], []
    for c, i in zip(corners, ids.flatten() if ids is not None else []):
        if int(i) in ref:
            src.append(c.reshape(4, 2))
            dst.append(ref[int(i)])
    if len(src) < min_markers:
        raise MarkersNotFound(f"se detectaron {len(src)} marcadores, hacen falta {min_markers}")
    H, _ = cv2.findHomography(np.concatenate(src), np.concatenate(dst) * px_per_mm, cv2.RANSAC, 3.0)
    size = (round(A4_W * px_per_mm), round(A4_H * px_per_mm))
    return cv2.warpPerspective(image, H, size, flags=cv2.INTER_LINEAR, borderValue=255)
