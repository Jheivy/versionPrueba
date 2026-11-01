"""Limpia la malla de Object Capture, la orienta, la escala en mm y la guarda como STL."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

PLANE_MARGIN_MM = 1.5      # lo que queda a esta altura de la hoja (o por debajo) es el papel, no la pieza


def _square_up(mesh: trimesh.Trimesh) -> None:
    """Gira la pieza sobre Z para que su huella quede alineada con X/Y (rectángulo de menor área), lado largo en X:
    sin esto «ancho» y «fondo» dependen de cómo orientó Object Capture el modelo."""
    t, _ = trimesh.bounds.oriented_bounds_2D(np.asarray(mesh.vertices)[:, :2])
    rot = np.eye(4)
    rot[:2, :2] = t[:2, :2]
    mesh.apply_transform(rot)
    if mesh.extents[1] > mesh.extents[0]:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))


def postprocess(src: Path, dst: Path, largo_mm: float | None = None, units_to_mm: float = 1000.0,
                sheet: dict | None = None) -> dict:
    """- Une los materiales/escenas en una sola malla y se queda con el mayor fragmento.
    - Object Capture usa Y hacia arriba y metros: se pasa a Z arriba y mm.
    - `largo_mm`: medida real (calibre) de la dimensión más larga; si falta, se asume
      que la escala de Object Capture es correcta (`scale_estimated=True`).
    - `sheet` (de `scale.sheet_alignment`): la hoja de marcadores da la escala real, el plano de la mesa (que pasa a
      ser Z=0, así se quita el papel y la pieza queda apoyada) y la orientación; sustituye a «Y arriba, metros».
    - Apoya la pieza en Z=0 y la centra en X/Y."""
    mesh = trimesh.load(src, force="mesh", process=True)
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise ValueError("la malla reconstruida está vacía")
    if sheet:
        mesh.apply_translation(-np.asarray(sheet["origin"]))
        mesh.apply_scale(sheet["mm_per_unit"])
        up = trimesh.geometry.align_vectors(np.asarray(sheet["normal"]), [0, 0, 1])
        mesh.apply_transform(up)                                                   # la mesa pasa a ser el plano Z=0
        keep = (mesh.vertices[mesh.faces][:, :, 2] > PLANE_MARGIN_MM).any(axis=1)  # fuera el papel
        if not keep.any():
            raise ValueError("no queda pieza sobre la hoja de marcadores")
        mesh.update_faces(keep)
        mesh.remove_unreferenced_vertices()
    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        mesh = max(parts, key=lambda p: len(p.faces))
    if not sheet:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))  # Y-up -> Z-up
        mesh.apply_scale(units_to_mm)
    _square_up(mesh)
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
            "scale_estimated": not (largo_mm or sheet),
            "scale_source": "calibre" if largo_mm else "marcadores" if sheet else "estimada"}
