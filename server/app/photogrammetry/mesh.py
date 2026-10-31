"""Limpia la malla de Object Capture, la orienta, la escala en mm y la guarda como STL."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh


def postprocess(src: Path, dst: Path, largo_mm: float | None = None, units_to_mm: float = 1000.0) -> dict:
    """- Une los materiales/escenas en una sola malla y se queda con el mayor fragmento.
    - Object Capture usa Y hacia arriba y metros: se pasa a Z arriba y mm.
    - `largo_mm`: medida real (calibre) de la dimensión más larga; si falta, se asume
      que la escala de Object Capture es correcta (`scale_estimated=True`).
    - Apoya la pieza en Z=0 y la centra en X/Y."""
    mesh = trimesh.load(src, force="mesh", process=True)
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise ValueError("la malla reconstruida está vacía")
    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        mesh = max(parts, key=lambda p: len(p.faces))
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))  # Y-up -> Z-up
    mesh.apply_scale(units_to_mm)
    if largo_mm:
        mesh.apply_scale(largo_mm / mesh.extents.max())
    mesh.fill_holes()
    mesh.remove_unreferenced_vertices()
    b = mesh.bounds
    mesh.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
    mesh.export(dst)
    ex = mesh.extents
    return {"ancho": float(ex[0]), "fondo": float(ex[1]), "alto": float(ex[2]),
            "watertight": bool(mesh.is_watertight), "triangles": int(len(mesh.faces)),
            "scale_estimated": not largo_mm}
