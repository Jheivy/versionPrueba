"""Escala real y plano de la mesa de una malla de Object Capture, a partir de la hoja de marcadores.

Si la hoja A4 de marcadores estaba bajo la pieza al grabar el vídeo, sale en la textura del modelo. Se buscan los
marcadores ArUco en el atlas de textura, se llevan sus esquinas a 3D con las coordenadas UV de la malla y se ajusta una
semejanza (Umeyama) entre esas esquinas y su posición conocida en la hoja (mm): da la escala, el plano de la hoja y el
error del ajuste. Sin marcadores en la textura devuelve None y el trabajo sigue como antes (escala estimada o cota).
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import trimesh

from ..views.markers import DICT, marker_corners_mm

MAX_RMS_MM = 3.0           # más error que esto y el ajuste no es de fiar
MIN_POINTS = 4


def _geometries(path: Path):
    """(vértices, caras, uv, imagen BGR/gris) de cada trozo con textura de la malla."""
    loaded = trimesh.load(path, process=False)
    geoms = list(loaded.geometry.values()) if isinstance(loaded, trimesh.Scene) else [loaded]
    for g in geoms:
        vis = getattr(g, "visual", None)
        uv = getattr(vis, "uv", None)
        mat = getattr(vis, "material", None)
        img = getattr(mat, "image", None)
        if img is None:
            img = getattr(mat, "baseColorTexture", None)
        if uv is None or img is None or len(g.faces) == 0:
            continue
        yield np.asarray(g.vertices, float), np.asarray(g.faces), np.asarray(uv, float), np.asarray(img.convert("L"))


def _detect(gray: np.ndarray) -> dict[int, np.ndarray]:
    """{id: esquinas (4, 2) en píxeles del atlas} de los marcadores de la hoja."""
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(DICT), params)
    known = marker_corners_mm()
    found: dict[int, np.ndarray] = {}
    for scale in (1.0, 0.5):                 # un atlas enorme o muy nítido a veces se lee mejor reducido
        img = gray if scale == 1.0 else cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        corners, ids, _ = det.detectMarkers(img)
        for c, i in zip(corners, ids.flatten() if ids is not None else []):
            if int(i) in known and int(i) not in found:
                found[int(i)] = c.reshape(4, 2) / scale
    return found


def _to_3d(points_uv: np.ndarray, verts: np.ndarray, faces: np.ndarray, uv: np.ndarray) -> list[np.ndarray | None]:
    """Cada punto del atlas (u, v) -> su posición 3D por coordenadas baricéntricas en el triángulo que lo contiene."""
    tri = uv[faces]                                            # (F, 3, 2)
    lo, hi = tri.min(axis=1), tri.max(axis=1)
    out: list[np.ndarray | None] = []
    for p in points_uv:
        cand = np.nonzero(np.all((p >= lo - 1e-9) & (p <= hi + 1e-9), axis=1))[0]
        hit = None
        for f in cand:
            a, b, c = tri[f]
            den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(den) < 1e-14:
                continue                                       # triángulo degenerado en el atlas
            w0 = ((b[1] - c[1]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[1])) / den
            w1 = ((c[1] - a[1]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[1])) / den
            w2 = 1 - w0 - w1
            if min(w0, w1, w2) >= -1e-6:
                hit = w0 * verts[faces[f][0]] + w1 * verts[faces[f][1]] + w2 * verts[faces[f][2]]
                break
        out.append(hit)
    return out


def _umeyama(src: np.ndarray, dst: np.ndarray):
    """Semejanza dst ≈ c·R·src + t (mínimos cuadrados, R propia)."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    xs, xd = src - mu_s, dst - mu_d
    u, d, vt = np.linalg.svd(xd.T @ xs / len(src))
    s = np.eye(3)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        s[2, 2] = -1
    r = u @ s @ vt
    var = (xs ** 2).sum() / len(src)
    c = float(np.trace(np.diag(d) @ s) / var)
    return c, r, mu_d - c * r @ mu_s


def sheet_alignment(obj: Path) -> dict | None:
    """Escala y plano de la hoja en la malla `obj`:
    {mm_per_unit, rms_mm, markers, origin (punto del plano, en unidades de la malla),
    normal (unitaria, hacia el lado donde está la pieza)}."""
    known = marker_corners_mm()
    src, dst, ids = [], [], set()
    for verts, faces, uv, gray in _geometries(obj):
        h, w = gray.shape
        for mid, corners in _detect(gray).items():
            # OBJ: v = 0 es el borde de abajo de la imagen; en la imagen, la fila 0 es la de arriba
            pts_uv = np.stack([corners[:, 0] / w, 1 - corners[:, 1] / h], axis=1)
            pts3 = _to_3d(pts_uv, verts, faces, uv)
            if any(p is None for p in pts3):
                continue
            src += [(*xy, 0.0) for xy in known[mid]]
            dst += pts3
            ids.add(mid)
    if len(src) < MIN_POINTS:
        return None
    src, dst = np.array(src, float), np.array(dst, float)
    c, r, t = _umeyama(src, dst)
    if not np.isfinite(c) or c <= 0:
        return None
    rms_mm = float(np.sqrt(((dst - (c * (src @ r.T) + t)) ** 2).sum(axis=1).mean()) / c)
    if rms_mm > MAX_RMS_MM:
        return None
    normal = r[:, 2]
    mesh = trimesh.load(obj, force="mesh", process=False)
    if float(np.mean((np.asarray(mesh.vertices) - t) @ normal)) < 0:       # la pieza está del lado de la normal
        normal = -normal
    return {"mm_per_unit": 1.0 / c, "rms_mm": round(rms_mm, 2), "markers": len(ids),
            "origin": t, "normal": normal / np.linalg.norm(normal)}
