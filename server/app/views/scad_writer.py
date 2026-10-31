"""Genera un .scad paramétrico a partir de las tres vistas ortográficas.

Convenciones (todas en mm, origen en la esquina inferior izquierda de cada vista):
  - planta  : polígono en (x, y)  -> extruido en Z
  - alzado  : polígono en (x, z)  -> extruido en Y
  - perfil  : polígono en (y, z)  -> extruido en X
Cada vista es una lista de contornos; el primero es el exterior y el resto huecos.
Los agujeros circulares pueden pasarse aparte (`circles`) y se escriben como parámetros
editables (`diam_agujero_planta_1`, `pos_agujero_planta_1`).
El sólido final es la intersección de las tres extrusiones (visual hull ortográfico).
"""
from __future__ import annotations

from collections.abc import Sequence

Point = tuple[float, float]
Contours = Sequence[Sequence[Point]]
Circle = tuple[float, float, float, str | None]  # (cx, cy, Ø, etiqueta estándar)


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


def _view_module(name: str, contours: Contours, circles: Sequence[Circle]) -> str:
    """Módulo 2D de una vista: contorno + agujeros circulares paramétricos."""
    if not circles:
        return f"module {name}() {{ offset(delta=holgura) {_polygon(contours)} }}"
    holes = " ".join(
        f"translate(pos_agujero_{name}_{i}) circle(d=diam_agujero_{name}_{i}, $fn=64);"
        for i in range(1, len(circles) + 1))
    return (f"module {name}() {{ offset(delta=holgura) difference() {{ {_polygon(contours)} {holes} }} }}")


def _circle_vars(name: str, circles: Sequence[Circle]) -> list[str]:
    out = []
    for i, (cx, cy, d, std) in enumerate(circles, 1):
        note = f"  // posible {std} (paso medio)" if std else ""
        out.append(f"diam_agujero_{name}_{i} = {d:.3f};{note}")
        out.append(f"pos_agujero_{name}_{i} = [{cx:.3f}, {cy:.3f}];")
    return out


def build_scad(
    planta: Contours,
    alzado: Contours | None = None,
    perfil: Contours | None = None,
    holgura: float = 0.0,
    altura: float | None = None,
    circles: dict[str, Sequence[Circle]] | None = None,
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

    circles = circles or {}
    margen = 1  # mm extra para que las extrusiones atraviesen por completo
    lines = [
        "// Generado por Scan2Print — editable",
        f"ancho = {ancho:.3f};  // X",
        f"fondo = {fondo:.3f};  // Y",
        f"alto = {alto:.3f};    // Z",
        f"holgura = {holgura:.3f}; // offset de contorno (+ agranda, - encoge)",
        f"margen = {margen};",
    ]
    present = {"planta": planta, "alzado": alzado, "perfil": perfil}
    var_lines = [v for n, c in present.items() if c for v in _circle_vars(n, circles.get(n, ()))]
    if var_lines:
        lines += ["", "// Agujeros: Ø en mm y posición [x, y] en el plano de cada vista", *var_lines]
    lines.append("")
    for n, c in present.items():
        if c:
            lines.append(_view_module(n, c, circles.get(n, ())))
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
