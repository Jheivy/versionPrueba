"""Detecta agujeros circulares y ranuras y los convierte en parámetros (Ø o ancho y largo, y posición)."""
from __future__ import annotations

import math

import cv2
import numpy as np

# Ø de paso medio (ISO 273) para tornillería métrica. Solo se SUGIERE la etiqueta: la medida
# fotográfica tiene ±0,1 mm de error y un agujero de Ø5,0 no debe convertirse en 5,3.
STANDARD = {3.2: "M3", 4.3: "M4", 5.3: "M5", 6.4: "M6", 8.4: "M8", 10.5: "M10"}
HINT_MM = 0.15
MIN_VERTICES = 8


def fit_circle(pts) -> tuple[float, float, float]:
    """Ajuste algebraico (Kåsa) por mínimos cuadrados: devuelve (cx, cy, r)."""
    p = np.asarray(pts, float)
    a = np.c_[2 * p, np.ones(len(p))]
    (cx, cy, c), *_ = np.linalg.lstsq(a, (p ** 2).sum(1), rcond=None)
    return float(cx), float(cy), math.sqrt(max(c + cx * cx + cy * cy, 0.0))


def as_circle(pts) -> tuple[float, float, float] | None:
    """(cx, cy, Ø) si el polígono es un círculo; None si es otra forma (cuadrado, hexágono, ranura…)."""
    if len(pts) < MIN_VERTICES:
        return None
    cx, cy, r = fit_circle(pts)
    if r <= 0:
        return None
    p = np.asarray(pts, float)
    tol = max(0.3, 0.05 * r)
    if np.abs(np.hypot(p[:, 0] - cx, p[:, 1] - cy) - r).max() > tol:
        return None
    mid = (p + np.roll(p, -1, axis=0)) / 2  # los puntos medios de los lados también deben estar en el círculo
    if np.abs(np.hypot(mid[:, 0] - cx, mid[:, 1] - cy) - r).max() > tol:
        return None
    ang = np.sort(np.arctan2(p[:, 1] - cy, p[:, 0] - cx))
    if np.diff(np.r_[ang, ang[0] + 2 * np.pi]).max() > math.pi / 2:  # un arco no es un agujero
        return None
    return cx, cy, 2 * r


MIN_SLOT_RATIO = 1.35     # largo/ancho mínimo para que un hueco de extremos redondos sea ranura y no círculo


def as_slot(pts) -> tuple[float, float, float, float, float] | None:
    """(cx, cy, ancho, largo, ángulo°) si el polígono es una ranura (dos semicírculos unidos por dos rectas);
    `largo` es el total, de punta a punta, y el ángulo (0-180°) el del eje largo. None si es otra forma."""
    if len(pts) < 10:
        return None
    p = np.asarray(pts, float)
    box = cv2.boxPoints(cv2.minAreaRect(p.astype(np.float32)))
    e0, e1 = box[1] - box[0], box[2] - box[1]
    long_edge, short_edge = (e0, e1) if np.hypot(*e0) >= np.hypot(*e1) else (e1, e0)
    a, b = float(np.hypot(*long_edge)), float(np.hypot(*short_edge))
    if b < 1.0 or a / b < MIN_SLOT_RATIO:
        return None
    u = long_edge / a
    c = box.mean(axis=0)
    half, r = (a - b) / 2, b / 2
    p1 = c - u * half

    def off_axis(q):                      # distancia de cada punto al segmento p1-p2 (el «hueso» de la ranura)
        t = np.clip((q - p1) @ u, 0, 2 * half)
        return np.hypot(*(q - (p1 + np.outer(t, u))).T)

    tol = max(0.3, 0.05 * r)
    mid = (p + np.roll(p, -1, axis=0)) / 2
    if np.abs(off_axis(p) - r).max() > tol or np.abs(off_axis(mid) - r).max() > tol:
        return None                       # un rectángulo, un óvalo o una forma libre no encaja
    along = (p - c) @ u
    if (along < -half).sum() < 3 or (along > half).sum() < 3:
        return None                       # faltan los extremos redondos
    ang = math.degrees(math.atan2(u[1], u[0])) % 180
    return float(c[0]), float(c[1]), b, a, float(ang)


def split_holes(contours):
    """Separa los huecos circulares y las ranuras del resto. Devuelve (contornos sin ellos, círculos, ranuras):
    círculos (cx, cy, Ø) y ranuras (cx, cy, ancho, largo, ángulo), cada grupo ordenado por posición."""
    kept, circles, slots = [list(contours[0])], [], []
    for hole in contours[1:]:
        c = as_circle(hole)
        s = None if c else as_slot(hole)
        (circles.append(c) if c else slots.append(s) if s else kept.append(list(hole)))
    key = lambda h: (round(h[0], 1), round(h[1], 1))      # noqa: E731
    return kept, sorted(circles, key=key), sorted(slots, key=key)


def split_circles(contours):
    """Separa los huecos circulares. Devuelve (contornos sin ellos, [(cx, cy, Ø)] ordenados)."""
    kept, circles = [list(contours[0])], []
    for hole in contours[1:]:
        c = as_circle(hole)
        (circles.append(c) if c else kept.append(list(hole)))
    return kept, sorted(circles, key=lambda c: (round(c[0], 1), round(c[1], 1)))


def finalize(diam: float) -> tuple[float, str | None]:
    """Redondea el Ø a 0,1 mm y devuelve la etiqueta métrica si está a ≤ 0,15 mm de una medida estándar."""
    label = next((lbl for std, lbl in STANDARD.items() if abs(diam - std) <= HINT_MM), None)
    return round(diam, 1), label
