"""Genera un .scad paramétrico a partir de las tres vistas ortográficas.

Convenciones (todas en mm, origen en la esquina inferior izquierda de cada vista):
  - planta  : polígono en (x, y)  -> extruido en Z
  - alzado  : polígono en (x, z)  -> extruido en Y
  - perfil  : polígono en (y, z)  -> extruido en X
Cada vista es una lista de contornos; el primero es el exterior y el resto huecos.
El sólido final es la intersección de las tres extrusiones (visual hull ortográfico).
"""
from __future__ import annotations

from collections.abc import Sequence

Point = tuple[float, float]
Contours = Sequence[Sequence[Point]]


def _bbox(contours: Contours) -> tuple[float, float]:
    xs = [p[0] for c in contours for p in c]
    ys = [p[1] for c in contours for p in c]
    return max(xs), max(ys)


def _polygon(contours: Contours) -> str:
    points, paths, i = [], [], 0
    for c in contours:
        points.extend(f"[{x:.3f},{y:.3f}]" for x, y in c)
        paths.append("[" + ",".join(str(i + k) for k in range(len(c))) + "]")
        i += len(c)
    return f"polygon(points=[{','.join(points)}], paths=[{','.join(paths)}]);"


def build_scad(
    planta: Contours,
    alzado: Contours | None = None,
    perfil: Contours | None = None,
    holgura: float = 0.0,
    altura: float | None = None,
) -> str:
    """Devuelve el código OpenSCAD. Con solo `planta` hace una extrusión simple
    de altura `altura`."""
    if not planta:
        raise ValueError("la planta es obligatoria")
    ancho, fondo = _bbox(planta)
    if alzado:
        alto = _bbox(alzado)[1]
    elif perfil:
        alto = _bbox(perfil)[1]
    elif altura:
        alto = altura
    else:
        raise ValueError("indica alzado, perfil o altura")

    margen = 1  # mm extra para que las extrusiones atraviesen por completo
    lines = [
        "// Generado por Scan2Print — editable",
        f"ancho = {ancho:.3f};  // X",
        f"fondo = {fondo:.3f};  // Y",
        f"alto = {alto:.3f};    // Z",
        f"holgura = {holgura:.3f}; // offset de contorno (+ agranda, - encoge)",
        f"margen = {margen};",
        "",
        f"module planta() {{ offset(delta=holgura) {_polygon(planta)} }}",
    ]
    if alzado:
        lines.append(f"module alzado() {{ offset(delta=holgura) {_polygon(alzado)} }}")
    if perfil:
        lines.append(f"module perfil() {{ offset(delta=holgura) {_polygon(perfil)} }}")
    lines += ["", "intersection() {"]
    lines.append("  translate([0,0,-margen]) linear_extrude(alto + 2*margen) planta();")
    if alzado:
        lines.append(
            "  translate([0,fondo+margen,0]) rotate([90,0,0]) "
            "linear_extrude(fondo + 2*margen) alzado();"
        )
    if perfil:
        lines.append(
            "  translate([-margen,0,0]) rotate([90,0,90]) "
            "linear_extrude(ancho + 2*margen) perfil();"
        )
    if not (alzado or perfil):
        lines.append("  cube([ancho+2*margen, fondo+2*margen, alto]);")
    lines.append("}")
    return "\n".join(lines) + "\n"
