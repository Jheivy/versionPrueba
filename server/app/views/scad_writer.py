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
Slot = tuple[float, float, float, float, float]   # (cx, cy, ancho, largo total, ángulo°)


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


def _view_module(name: str, contours: Contours, circles: Sequence[Circle], slots: Sequence[Slot] = ()) -> str:
    """Módulo 2D de una vista: contorno + agujeros circulares y ranuras paramétricos."""
    if not circles and not slots:
        return f"module {name}() {{ offset(delta=holgura) {_polygon(contours)} }}"
    holes = [f"translate(pos_agujero_{name}_{i}) circle(d=diam_agujero_{name}_{i}, $fn=64);"
             for i in range(1, len(circles) + 1)]
    for i in range(1, len(slots) + 1):
        w, half = f"ancho_ranura_{name}_{i}", f"(largo_ranura_{name}_{i} - ancho_ranura_{name}_{i}) / 2"
        holes.append(f"translate(pos_ranura_{name}_{i}) rotate(ang_ranura_{name}_{i}) hull() {{ "
                     f"translate([-{half}, 0]) circle(d={w}, $fn=48); translate([{half}, 0]) circle(d={w}, $fn=48); }}")
    return f"module {name}() {{ offset(delta=holgura) difference() {{ {_polygon(contours)} {' '.join(holes)} }} }}"


def _slot_vars(name: str, slots: Sequence[Slot]) -> list[str]:
    out = []
    for i, (cx, cy, w, length, ang) in enumerate(slots, 1):
        out += [f"ancho_ranura_{name}_{i} = {w:.3f};", f"largo_ranura_{name}_{i} = {length:.3f};  // de punta a punta",
                f"ang_ranura_{name}_{i} = {ang:.1f};", f"pos_ranura_{name}_{i} = [{cx:.3f}, {cy:.3f}];"]
    return out


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
    slots: dict[str, Sequence[Slot]] | None = None,
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

    circles, slots = circles or {}, slots or {}
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
    var_lines = [v for n, c in present.items() if c
                 for v in _circle_vars(n, circles.get(n, ())) + _slot_vars(n, slots.get(n, ()))]
    if var_lines:
        lines += ["", "// Agujeros y ranuras: medidas en mm y posición [x, y] en el plano de cada vista", *var_lines]
    lines.append("")
    for n, c in present.items():
        if c:
            lines.append(_view_module(n, c, circles.get(n, ()), slots.get(n, ())))
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
