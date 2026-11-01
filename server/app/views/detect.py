"""Diagnóstico rápido de un fotograma de cámara: ¿se ve la hoja, está nítido, hay luz?"""
from __future__ import annotations

import cv2
import numpy as np

from . import parallax
from .markers import DICT, marker_corners_mm
from .rectify import MarkersNotFound, rectify_full

MIN_SHARPNESS = 60.0   # varianza del Laplaciano (imagen reducida a 480 px)
MIN_BRIGHTNESS = 70.0  # media de gris 0-255
MAX_BRIGHTNESS = 245.0  # una hoja blanca bien expuesta ronda 230
NEAR_MM = 250.0        # más cerca, el paralaje de la cara superior de la pieza pesa demasiado


def analyze(image: np.ndarray) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    small = cv2.resize(gray, (480, max(1, round(480 * gray.shape[0] / gray.shape[1]))))
    sharp = float(cv2.Laplacian(small, cv2.CV_64F).var())
    bright = float(small.mean())
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(DICT), cv2.aruco.DetectorParameters())
    _, ids, _ = det.detectMarkers(small)
    known = marker_corners_mm()
    markers = sorted({int(i) for i in (ids.flatten() if ids is not None else []) if int(i) in known})
    checks = {"hoja": len(markers) >= 2, "nitidez": sharp >= MIN_SHARPNESS,
              "luz": MIN_BRIGHTNESS <= bright <= MAX_BRIGHTNESS}
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
    dist = None
    if len(markers) >= 2:
        try:
            pose = parallax.camera_pose(rectify_full(small, 10.0)[1], small.shape)
            dist = round(pose["dist"]) if pose else None
        except MarkersNotFound:
            pass
    if hint == "Listo para disparar" and dist and dist < NEAR_MM:
        hint = "Listo · aleja la cámara o usa zoom para medir mejor"
    elif hint == "Listo para disparar" and len(markers) < 4:
        hint = f"Listo · se ven {len(markers)} de 4 marcadores: encuádralos todos para medir mejor"
    return {"markers": len(markers), "sharpness": round(sharp, 1), "brightness": round(bright, 1),
            "ok": hint.startswith("Listo"), "hint": hint, "checks": checks, "distance": dist}
