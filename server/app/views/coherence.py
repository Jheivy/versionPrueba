"""Coherencia entre vistas: cada dimensión aparece en dos vistas y debe medir lo mismo.

    ancho (X): planta (x)  y alzado (x)
    fondo (Y): planta (y)  y perfil (x)
    alto  (Z): alzado (y)  y perfil (y)

Si no cuadran, el sólido (intersección de las tres extrusiones) se recorta al menor de los dos.
"""
from __future__ import annotations

MISMATCH_MM = 0.8    # diferencia mínima para avisar (la foto tiene ~±0,2 mm de error)
MISMATCH_PCT = 0.02  # o el 2 % de la medida en piezas grandes

# dimensión -> [(vista, índice del eje en esa vista)]
SHARED = {
    "ancho": (("planta", 0), ("alzado", 0)),
    "fondo": (("planta", 1), ("perfil", 0)),
    "alto": (("alzado", 1), ("perfil", 1)),
}
VIEW_AXES = {"planta": ("ancho", "fondo"), "alzado": ("ancho", "alto"), "perfil": ("fondo", "alto")}


def sizes(views) -> dict[str, tuple[float, float]]:
    """Tamaño (x, y) en mm del contorno exterior de cada vista (cajas ya reencajadas en 0,0)."""
    return {n: (max(p[0] for p in c[0]), max(p[1] for p in c[0])) for n, c in views.items()}


def shared_dims(view_sizes) -> dict[str, list[tuple[str, float]]]:
    """Para cada dimensión, las medidas que dan las vistas presentes: [(vista, mm)]."""
    return {dim: [(v, view_sizes[v][i]) for v, i in pairs if v in view_sizes] for dim, pairs in SHARED.items()}


def _mismatch(a: float, b: float) -> bool:
    return abs(a - b) > max(MISMATCH_MM, MISMATCH_PCT * max(a, b))


def check(view_sizes) -> list[dict]:
    """Avisos de las dimensiones que dos vistas miden distinto."""
    out = []
    for dim, vals in shared_dims(view_sizes).items():
        if len(vals) == 2 and _mismatch(vals[0][1], vals[1][1]):
            (va, a), (vb, b) = vals
            out.append({"dim": dim, "views": [va, vb], "values": [round(a, 1), round(b, 1)],
                        "diff": round(abs(a - b), 1)})
    return out


def targets(view_sizes, params: dict, unify: bool = False) -> dict[str, float]:
    """Medida final de cada dimensión: la cota dada con calibre; si no, el promedio de las dos
    vistas cuando se pide unificar y no cuadran. Lo demás se deja como está."""
    out = {}
    for dim, vals in shared_dims(view_sizes).items():
        if dim in params:
            out[dim] = params[dim]
        elif unify and len(vals) == 2 and _mismatch(vals[0][1], vals[1][1]):
            out[dim] = (vals[0][1] + vals[1][1]) / 2
    return out
