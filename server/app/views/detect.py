"""Diagnóstico rápido de un fotograma de cámara: ¿se ve la hoja, está nítido, hay luz?"""
from __future__ import annotations

import cv2
import numpy as np

from .markers import DICT, marker_corners_mm

MIN_SHARPNESS = 60.0   # varianza del Laplaciano (imagen reducida a 480 px)
MIN_BRIGHTNESS = 70.0  # media de gris 0-255
MAX_BRIGHTNESS = 245.0  # una hoja blanca bien expuesta ronda 230


def analyze(image: np.ndarray) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    small = cv2.resize(gray, (480, max(1, round(480 * gray.shape[0] / gray.shape[1]))))
    sharp = float(cv2.Laplacian(small, cv2.CV_64F).var())
    bright = float(small.mean())
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(DICT), cv2.aruco.DetectorParameters())
    _, ids, _ = det.detectMarkers(small)
    known = marker_corners_mm()
    markers = sorted({int(i) for i in (ids.flatten() if ids is not None else []) if int(i) in known})
    if len(markers) < 2:
        hint = "No veo la hoja: encuádrala entera"
    elif sharp < MIN_SHARPNESS:
        hint = "Imagen borrosa: sujeta firme o acércate despacio"
    elif bright < MIN_BRIGHTNESS:
        hint = "Poca luz: busca luz difusa"
    elif bright > MAX_BRIGHTNESS:
        hint = "Demasiada luz o reflejos"
    else:
        hint = "Listo para disparar"
    return {"markers": len(markers), "sharpness": round(sharp, 1), "brightness": round(bright, 1),
            "ok": hint == "Listo para disparar", "hint": hint}
