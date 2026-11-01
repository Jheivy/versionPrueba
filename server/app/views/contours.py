"""Extrae el contorno de la pieza (y sus huecos) de una hoja rectificada, en mm."""
from __future__ import annotations

import cv2
import numpy as np

from .markers import marker_corners_mm


class NoShapeFound(Exception):
    pass


CHROMA_MIN = 24.0        # distancia de color (Lab) al papel a partir de la cual algo es pieza y no sombra
FLAT_STEP = 16           # el fondo se ajusta sobre una rejilla cada 16 px (1,6 mm)


def _flat_background(gray: np.ndarray, skip: np.ndarray | None = None) -> np.ndarray:
    """Luz del papel en cada punto, ajustando una superficie cuadrática a los píxeles claros (descarta la pieza,
    que es oscura, por rechazo iterativo de atípicos). Así un degradado de luz no se confunde con la pieza.
    `skip` marca lo que no es papel (los marcadores) y no cuenta para el ajuste."""
    small = cv2.GaussianBlur(gray[::FLAT_STEP, ::FLAT_STEP].astype(np.float32), (0, 0), 1.0)
    out = np.zeros(small.shape, bool) if skip is None else skip[::FLAT_STEP, ::FLAT_STEP]
    small = np.where(out, 0.0, small).astype(np.float32)
    h, w = small.shape
    yy, xx = np.mgrid[0:h, 0:w]
    x, y = xx / w - 0.5, yy / h - 0.5
    A = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], axis=-1).reshape(-1, 6)
    v = small.astype(np.float64).reshape(-1)
    local_max = cv2.dilate(small, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))   # ~10 cm de lado
    keep = ((small >= 0.9 * local_max) & ~out).reshape(-1)    # papel: casi tan claro como lo más claro de su entorno
    for _ in range(4):
        coef, *_ = np.linalg.lstsq(A[keep], v[keep], rcond=None)
        res = v - A @ coef
        mad = max(np.median(np.abs(res[keep])) * 1.4826, 1.0)
        # las sombras y la pieza quedan por debajo del ajuste; el papel, dentro del ruido
        keep = (res > -2.5 * mad) & ~out.reshape(-1)
    fit = (A @ coef).reshape(h, w).astype(np.float32)
    return np.maximum(cv2.resize(fit, (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_LINEAR), 30.0)


def _foreground(sheet: np.ndarray, px_per_mm: float) -> tuple[np.ndarray, np.ndarray]:
    """Máscara de la pieza (más oscura que el papel tras quitar el degradado de luz, o de otro color) y
    `signal` (uint8): cuánto se aparta cada píxel del papel, de 0 (papel) a 255."""
    color = sheet if sheet.ndim == 3 else cv2.cvtColor(sheet, cv2.COLOR_GRAY2BGR)
    h, w = color.shape[:2]
    markers = np.zeros((h, w), bool)
    pad = 2.0
    for c in marker_corners_mm().values():
        x0, y0 = (c.min(axis=0) - pad) * px_per_mm
        x1, y1 = (c.max(axis=0) + pad) * px_per_mm
        markers[max(int(y0), 0):int(y1), max(int(x0), 0):int(x1)] = True
    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    bg = _flat_background(gray, markers)
    norm = cv2.convertScaleAbs(np.minimum(cv2.divide(gray.astype(np.float32), bg, scale=255.0), 255.0))
    norm[markers] = 255                 # los marcadores no son pieza
    sigma = 0.3 * px_per_mm / 3
    norm = cv2.GaussianBlur(norm, (0, 0), sigma)
    _, mask = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    signal = 255 - norm
    if sheet.ndim == 3:   # las piezas de color claro (amarillas, azules…) apenas se distinguen del papel por su brillo
        half = cv2.resize(color, (w // 2, h // 2), interpolation=cv2.INTER_AREA)   # el color no pide toda la resolución
        lab = cv2.cvtColor(half, cv2.COLOR_BGR2LAB).astype(np.float32)
        paper = cv2.resize(norm, (w // 2, h // 2), interpolation=cv2.INTER_AREA) > 225
        paper &= ~cv2.resize(markers.astype(np.uint8), (w // 2, h // 2), interpolation=cv2.INTER_NEAREST).astype(bool)
        if paper.sum() > 1000:
            a0, b0 = np.median(lab[..., 1][paper]), np.median(lab[..., 2][paper])   # tinte de la luz (papel «neutro»)
            chroma = cv2.GaussianBlur(np.hypot(lab[..., 1] - a0, lab[..., 2] - b0), (0, 0), sigma / 2)
            chroma = cv2.resize(chroma, (w, h), interpolation=cv2.INTER_LINEAR)
            chroma[markers] = 0
            mask = np.maximum(mask, ((chroma > CHROMA_MIN) * 255).astype(np.uint8))
            signal = np.maximum(signal, cv2.convertScaleAbs(chroma, alpha=2.55))
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)), signal


def _edge_contrast(contour: np.ndarray, signal: np.ndarray, px_per_mm: float) -> float:
    """Diferencia media (0-1) de `signal` entre una franja justo dentro y otra justo fuera del contorno exterior."""
    region = np.zeros(signal.shape, np.uint8)
    cv2.drawContours(region, [contour], -1, 255, -1)
    w = max(2, round(0.5 * px_per_mm))
    k = np.ones((3, 3), np.uint8)
    inner = (cv2.subtract(cv2.erode(region, k, iterations=w), cv2.erode(region, k, iterations=3 * w)) > 0)
    outer = (cv2.subtract(cv2.dilate(region, k, iterations=3 * w), cv2.dilate(region, k, iterations=w)) > 0)
    if not inner.any() or not outer.any():
        return 0.0
    return float(signal[inner].mean() - signal[outer].mean()) / 255


def extract(sheet: np.ndarray, px_per_mm: float = 10.0, min_area_mm2: float = 25.0,
            epsilon_mm: float = 0.15, return_origin: bool = False, info: dict | None = None):
    """Devuelve [exterior, hueco1, ...] como listas de (x, y) en mm, con el origen en
    la esquina inferior izquierda de la caja de la pieza (eje y hacia arriba).
    Si se pasa `info`, se rellena con `contrast` (0-1): cuánto se distingue el borde de la pieza del papel."""
    mask, signal = _foreground(sheet, px_per_mm)

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
    if info is not None:
        info["contrast"] = round(_edge_contrast(found[best], signal, px_per_mm), 3)

    polys = []
    for k, i in enumerate([best] + holes):
        eps = epsilon_mm if k == 0 else epsilon_mm * 0.4  # huecos más finos: así los círculos se reconocen
        ap = cv2.approxPolyDP(found[i], eps * px_per_mm, True).reshape(-1, 2) / px_per_mm
        polys.append(ap)
    x0, y1 = polys[0][:, 0].min(), polys[0][:, 1].max()
    out = [[(float(x - x0), float(y1 - y)) for x, y in p] for p in polys]
    return (out, (float(x0), float(y1))) if return_origin else out  # origen: mm en la hoja
