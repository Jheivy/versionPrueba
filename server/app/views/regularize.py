"""Endereza contornos: aristas casi horizontales/verticales pasan a serlo exactamente y los
ángulos casi rectos a 90°, sin tocar piezas redondas ni inclinadas a propósito.

Cada arista se ajusta a una recta (las casi ejes, a x = c o y = c) y cada vértice nuevo es la
intersección de las rectas vecinas. Si el resultado se aleja demasiado del original se devuelve
el contorno sin tocar.
"""
from __future__ import annotations

import math

import numpy as np

ANGLE_TOL = 4.0        # grados respecto a un eje para considerar una arista «recta»
MIN_EDGE = 0.5         # mm: las aristas más cortas son ruido y se eliminan
CHAIN_DEV = 0.3        # mm: desviación máxima para fundir tramos inclinados consecutivos en una recta
JITTER = 0.15          # mm: desviación máxima para aceptar como recta una arista corta
MIN_AXIS_SHARE = 0.5   # fracción del perímetro en rectas para tratar el contorno como rectilíneo
MAX_AREA_CHANGE = 0.04
MAX_SHIFT = 1.5        # mm (mínimo): desplazamiento máximo de un vértice; crece con el tamaño de la pieza


def _area(p: np.ndarray) -> float:
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _drop_short(p: np.ndarray) -> np.ndarray:
    """Elimina aristas diminutas fundiendo sus extremos en el punto medio."""
    p = p.copy()
    while len(p) > 4:
        e = np.roll(p, -1, axis=0) - p
        length = np.hypot(e[:, 0], e[:, 1])
        i = int(np.argmin(length))
        if length[i] >= MIN_EDGE:
            break
        j = (i + 1) % len(p)
        p[i] = (p[i] + p[j]) / 2
        p = np.delete(p, j, axis=0)
    return p


def _chain_merge(p: np.ndarray) -> np.ndarray:
    """Funde en una sola arista los tramos consecutivos que siguen siendo una recta (±CHAIN_DEV).
    Se hace ANTES de clasificar: así el ruido de un tramo corto no parte una arista larga."""
    n = len(p)
    if n < 5:
        return p
    prev, nxt = p - np.roll(p, 1, axis=0), np.roll(p, -1, axis=0) - p
    turn = np.abs(np.arctan2(prev[:, 0] * nxt[:, 1] - prev[:, 1] * nxt[:, 0], (prev * nxt).sum(1)))
    p = np.roll(p, -int(np.argmax(turn)), axis=0)  # arranca en una esquina real
    pts = np.vstack([p, p[:1]])
    keep, a = [0], 0
    while a < n:
        b = a + 1
        while b + 1 <= n and _straight(pts[a:b + 2]):
            b += 1
        keep.append(b)
        a = b
    return pts[sorted(set(keep) - {n})]


def _straight(chain: np.ndarray) -> bool:
    a, b = chain[0], chain[-1]
    d = b - a
    norm = math.hypot(*d)
    if norm == 0:
        return False
    inner = chain[1:-1]
    return bool(np.all(np.abs(d[0] * (inner[:, 1] - a[1]) - d[1] * (inner[:, 0] - a[0])) / norm <= CHAIN_DEV))


def _kind(dx: float, dy: float) -> str | None:
    length = math.hypot(dx, dy)
    slack = max(length * math.sin(math.radians(ANGLE_TOL)), JITTER)
    if abs(dy) <= slack and abs(dx) > abs(dy):
        return "h"
    if abs(dx) <= slack and abs(dy) > abs(dx):
        return "v"
    return None


def _line(kind: str | None, a: np.ndarray, b: np.ndarray, off: float):
    """Recta como (nx, ny, c): n·x = c."""
    if kind == "h":
        return 0.0, 1.0, off
    if kind == "v":
        return 1.0, 0.0, off
    d = b - a
    n = np.array([d[1], -d[0]]) / (np.hypot(*d) or 1.0)
    return float(n[0]), float(n[1]), float(n @ a)


def regularize(points, closed: bool = True) -> list[tuple[float, float]]:
    """Devuelve el contorno enderezado (misma lista de tuplas si no procede tocarlo)."""
    orig = [tuple(map(float, q)) for q in points]
    if len(orig) < 4:
        return orig
    p = _chain_merge(_drop_short(np.asarray(orig, float)))
    n = len(p)
    e = np.roll(p, -1, axis=0) - p
    length = np.hypot(e[:, 0], e[:, 1])
    kinds = [_kind(*e[i]) for i in range(n)]
    axis_len = sum(length[i] for i in range(n) if kinds[i])
    if axis_len < MIN_AXIS_SHARE * length.sum():
        return orig  # contorno curvo o inclinado: no se toca

    # una arista = [tipo, desplazamiento, longitud, vértice inicial, vértice final]
    edges = []
    for i in range(n):
        a, b = p[i], p[(i + 1) % n]
        off = (a[1] + b[1]) / 2 if kinds[i] == "h" else (a[0] + b[0]) / 2 if kinds[i] == "v" else 0.0
        edges.append([kinds[i], off, float(length[i]), a, b])

    merged = []
    for ed in edges:
        last = merged[-1] if merged else None
        if last and ed[0] and ed[0] == last[0]:  # mismo eje consecutivo: una sola recta (aunque esté algo torcida)
            tot = last[2] + ed[2]
            last[1] = (last[1] * last[2] + ed[1] * ed[2]) / tot
            last[2], last[4] = tot, ed[4]
        else:
            merged.append(list(ed))
    if len(merged) > 1 and merged[0][0] and merged[0][0] == merged[-1][0]:
        first, last = merged[0], merged.pop()
        tot = first[2] + last[2]
        first[1] = (first[1] * first[2] + last[1] * last[2]) / tot
        first[2], first[3] = tot, last[3]
    m = len(merged)
    if m < 3:
        return orig

    lines = [_line(k, a, b, off) for k, off, _, a, b in merged]
    out = []
    for i in range(m):  # vértice i = intersección de la arista anterior y la actual
        (a1, b1, c1), (a2, b2, c2) = lines[i - 1], lines[i]
        det = a1 * b2 - a2 * b1
        if abs(det) < 1e-6:
            out.append(tuple(map(float, merged[i][3])))  # paralelas: se conserva el vértice original
        else:
            out.append(((c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det))
    q = np.asarray(out)

    if _area(p) == 0 or abs(_area(q) - _area(p)) / _area(p) > MAX_AREA_CHANGE:
        return orig
    near = np.min(np.hypot(q[:, None, 0] - p[None, :, 0], q[:, None, 1] - p[None, :, 1]), axis=1)
    diag = math.hypot(*(p.max(axis=0) - p.min(axis=0)))
    if near.max() > max(MAX_SHIFT, 0.03 * diag):
        return orig
    return [(float(x), float(y)) for x, y in q]


def regularize_view(contours):
    """Endereza todos los contornos de una vista y reencaja la caja del exterior en (0, 0).
    Devuelve (contornos, (dx, dy)): lo que se restó, para mover los círculos igual."""
    reg = [regularize(c) for c in contours]
    xs = [x for x, _ in reg[0]]
    ys = [y for _, y in reg[0]]
    dx, dy = min(xs), min(ys)
    return [[(x - dx, y - dy) for x, y in c] for c in reg], (dx, dy)
