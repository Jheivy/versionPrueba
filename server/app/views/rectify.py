"""Detecta la hoja de marcadores y devuelve la vista cenital con escala en mm."""
from __future__ import annotations

import cv2
import numpy as np

from .markers import A4_H, A4_W, DICT, marker_corners_mm


class MarkersNotFound(Exception):
    pass


RMS_WARN_MM = 0.5        # error de reproyección de los marcadores a partir del cual se avisa
_PARAMS = cv2.aruco.DetectorParameters()
_PARAMS.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX   # esquinas con precisión de subpíxel


def rectify_full(image: np.ndarray, px_per_mm: float = 10.0, min_markers: int = 2):
    """Hoja A4 rectificada (1 mm = `px_per_mm` píxeles), homografía imagen -> hoja en mm y calidad del ajuste:
    `markers` usados, `inliers` de sus esquinas y `rms_mm`, el error medio con que los marcadores caen en su sitio."""
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(DICT), _PARAMS)
    corners, ids, _ = det.detectMarkers(image)
    ref = marker_corners_mm()
    src, dst = [], []
    for c, i in zip(corners, ids.flatten() if ids is not None else []):
        if int(i) in ref:
            src.append(c.reshape(4, 2))
            dst.append(ref[int(i)])
    if len(src) < min_markers:
        raise MarkersNotFound(f"se detectaron {len(src)} marcadores, hacen falta {min_markers}")
    src_pts, dst_pts = np.concatenate(src), np.concatenate(dst) * px_per_mm
    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)
    if H is None:
        raise MarkersNotFound("los marcadores no encajan con la hoja; repite la foto")
    back = cv2.perspectiveTransform(src_pts.reshape(-1, 1, 2).astype(np.float64), H).reshape(-1, 2)
    err = np.linalg.norm(back - dst_pts, axis=1) / px_per_mm
    size = (round(A4_W * px_per_mm), round(A4_H * px_per_mm))
    sheet = cv2.warpPerspective(image, H, size, flags=cv2.INTER_LINEAR, borderValue=255)
    info = {"markers": len(src), "inliers": int(mask.sum()), "rms_mm": round(float(np.sqrt((err ** 2).mean())), 3)}
    return sheet, np.diag([1 / px_per_mm, 1 / px_per_mm, 1.0]) @ H, info


def rectify(image: np.ndarray, px_per_mm: float = 10.0, min_markers: int = 2, return_h: bool = False):
    """Devuelve la hoja A4 completa rectificada: 1 mm = `px_per_mm` píxeles.
    Con `return_h` devuelve además la homografía imagen -> hoja en mm (para estimar la cámara)."""
    sheet, h_mm, _ = rectify_full(image, px_per_mm, min_markers)
    return (sheet, h_mm) if return_h else sheet
