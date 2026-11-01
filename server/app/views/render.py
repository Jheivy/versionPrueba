"""Miniatura de una pieza: render isométrico con sombreado plano, sin GPU ni dependencias nuevas.

Proyección ortográfica con la cámara girada 35° y elevada 28°, caras ocultas descartadas y orden de
atrás hacia delante (algoritmo del pintor). Se dibuja al triple de tamaño y se reduce para suavizar los bordes;
el fondo es transparente, así que sirve igual en tema claro y oscuro.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
import trimesh

FILAMENT = (242, 96, 26)   # naranja de filamento (RGB), el color de la pieza en toda la app
YAW, PITCH = math.radians(35), math.radians(28)
LIGHT = np.array([-0.40, 0.78, -0.48])   # (derecha, arriba, profundidad): luz desde arriba, a la izquierda y delante
SS = 3                     # supermuestreo


def render_model(stl_path, size: int = 192) -> bytes:
    """PNG (RGBA) de `size`×`size` con la pieza centrada."""
    mesh = trimesh.load(stl_path, force="mesh")
    v, f = np.asarray(mesh.vertices, float), np.asarray(mesh.faces)
    v = v - (v.min(0) + v.max(0)) / 2
    cy, sy, cp, sp = math.cos(YAW), math.sin(YAW), math.cos(PITCH), math.sin(PITCH)
    x1, y1, z1 = v[:, 0] * cy - v[:, 1] * sy, v[:, 0] * sy + v[:, 1] * cy, v[:, 2]   # giro alrededor de Z
    scr = np.c_[x1, y1 * sp + z1 * cp]                  # pantalla: x a la derecha, y hacia arriba
    depth = y1 * cp - z1 * sp                           # más grande = más lejos
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    nx, ny = n[:, 0] * cy - n[:, 1] * sy, n[:, 0] * sy + n[:, 1] * cy                # la normal, en el mismo giro
    nview = np.c_[nx, ny * sp + n[:, 2] * cp, ny * cp - n[:, 2] * sp]                # (derecha, arriba, profundidad)
    facing = nview[:, 2] < 0                            # mira a la cámara
    shade = 0.42 + 0.58 * np.clip(nview @ (LIGHT / np.linalg.norm(LIGHT)), 0, 1)
    order = np.argsort(-depth[f].mean(1))               # de atrás hacia delante
    order = order[facing[order]]

    span = (scr.max(0) - scr.min(0)).max() or 1.0
    big = size * SS
    k = big * 0.78 / span
    pts = (scr - (scr.min(0) + scr.max(0)) / 2) * k * np.array([1, -1]) + big / 2
    pts[:, 1] += big * 0.02
    rgb = np.empty((big, big, 3), np.uint8)
    rgb[:] = FILAMENT                                    # el borde se funde con el color de la pieza, no con negro
    mask = np.zeros((big, big), np.uint8)
    for i in order:
        poly = np.round(pts[f[i]]).astype(np.int32)
        color = tuple(int(c * shade[i]) for c in FILAMENT)
        cv2.fillConvexPoly(rgb, poly, color)
        cv2.fillConvexPoly(mask, poly, 255)
    rgb = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_AREA)
    alpha = cv2.resize(mask, (size, size), interpolation=cv2.INTER_AREA)
    bgra = np.dstack([rgb[:, :, ::-1], alpha])
    return cv2.imencode(".png", bgra)[1].tobytes()
