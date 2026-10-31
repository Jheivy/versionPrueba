import math
import re

import cv2
import numpy as np
import pytest
import trimesh
from synth import photo

from app import jobs, main, pipeline
from app.views.markers import render_sheet
from app.views.regularize import regularize, regularize_view

SHEET = render_sheet()
RNG = np.random.default_rng(1)


def jitter(pts, amp=0.12):
    return [(x + RNG.uniform(-amp, amp), y + RNG.uniform(-amp, amp)) for x, y in pts]


def densify(pts, step=3.0):
    """Añade puntos intermedios en cada arista (como deja approxPolyDP en un borde ruidoso)."""
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1], strict=True):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) // step))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    return out


def axis_aligned(poly, tol=1e-9):
    return all(abs(a[0] - b[0]) < tol or abs(a[1] - b[1]) < tol for a, b in zip(poly, poly[1:] + poly[:1], strict=True))


def test_noisy_rectangle_becomes_exact_rectangle():
    noisy = jitter(densify([(0, 0), (40, 0), (40, 20), (0, 20)]))
    out = regularize(noisy)
    assert len(out) == 4 and axis_aligned(out)
    xs, ys = sorted({round(x, 1) for x, _ in out}), sorted({round(y, 1) for _, y in out})
    assert xs == pytest.approx([0, 40], abs=0.15) and ys == pytest.approx([0, 20], abs=0.15)


def test_l_shape_with_tiny_steps():
    shape = [(0, 0), (40, 0), (40, 10), (10, 10), (10, 30), (0, 30)]
    out = regularize(jitter(densify(shape)) + [])
    assert len(out) == 6 and axis_aligned(out)


def rotate(pts, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


@pytest.mark.parametrize("tilt", [0, 1, 3])
@pytest.mark.parametrize("name,shape,vertices", [
    ("rect", [(0, 0), (40, 0), (40, 20), (0, 20)], 4),
    ("L", [(0, 0), (40, 0), (40, 10), (10, 10), (10, 30), (0, 30)], 6),
    ("U", [(0, 0), (30, 0), (30, 20), (22, 20), (22, 6), (8, 6), (8, 20), (0, 20)], 8),
])
def test_tilted_noisy_shapes_give_exact_vertices(name, shape, vertices, tilt):
    out = regularize(jitter(densify(rotate(shape, tilt))))  # ruido ±0,12 mm y hasta 3° de inclinación
    assert len(out) == vertices and axis_aligned(out), name


def test_small_jog_is_removed():
    jog = [(0, 0), (20, 0), (20, 0.4), (40, 0.4), (40, 20), (0, 20)]  # escalón de 0,4 mm = ruido
    out = regularize(jog)
    assert len(out) == 4 and axis_aligned(out)


def test_real_step_is_kept():
    step = [(0, 0), (20, 0), (20, 3), (40, 3), (40, 20), (0, 20)]  # escalón de 3 mm: es parte de la pieza
    out = regularize(step)
    assert len(out) == 6 and axis_aligned(out)


def test_slanted_edges_are_kept():
    trap = [(0, 0), (40, 0), (30, 20), (10, 20)]  # trapecio: los lados inclinados no son ejes
    out = regularize(trap)
    assert out == trap or len(out) == 4
    left = math.degrees(math.atan2(out[3][1] - out[0][1], out[3][0] - out[0][0]))
    assert left == pytest.approx(63.4, abs=1.0)  # el ángulo del lado inclinado no cambia


def test_slanted_edges_merge_noisy_points():
    trap = [(0, 0), (40, 0), (32, 20), (8, 20)]
    out = regularize(jitter(densify(trap), 0.1))
    assert len(out) == 4  # los lados inclinados también pasan a ser una sola recta


def test_rotated_rectangle_is_untouched():
    c, s = math.cos(math.radians(15)), math.sin(math.radians(15))
    rot = [(x * c - y * s, x * s + y * c) for x, y in [(0, 0), (40, 0), (40, 20), (0, 20)]]
    assert regularize(rot) == rot  # inclinada 15°: no es una pieza «recta»


def test_circle_is_untouched():
    circle = [(30 * math.cos(t), 30 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    assert regularize(circle) == [tuple(p) for p in circle]


def test_view_is_renormalized_and_returns_shift():
    outer = [(0.3, 0.2), (40.1, 0.1), (40.2, 20.3), (0.1, 20.1)]
    hole = [(10.0, 5.0), (15.0, 5.0), (15.0, 10.0), (10.0, 10.0)]
    (o, h), (dx, dy) = regularize_view([outer, hole])
    assert min(x for x, _ in o) == pytest.approx(0, abs=1e-9) and min(y for _, y in o) == pytest.approx(0, abs=1e-9)
    assert (dx, dy) == pytest.approx((0.2, 0.15), abs=0.1)
    assert axis_aligned(h)


def _job(tmp_path, monkeypatch, tilt_deg):
    monkeypatch.setattr(main, "STORAGE", tmp_path / "jobs")
    monkeypatch.setattr(pipeline, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(pipeline, "_notify", lambda p: None)
    d = tmp_path / "jobs" / ("d" * 32)
    (d / "input").mkdir(parents=True)
    c, s = math.cos(math.radians(tilt_deg)), math.sin(math.radians(tilt_deg))
    quad = [(60 + x * c - y * s, 100 + x * s + y * c) for x, y in [(0, 0), (40, 0), (40, 20), (0, 20)]]
    side = [("poly", 0, [(60, 130), (100, 130), (100, 100), (60, 100)])]
    side2 = [("poly", 0, [(60, 130), (80, 130), (80, 100), (60, 100)])]
    for n, shapes in {"planta": [("poly", 0, quad)], "alzado": side, "perfil": side2}.items():
        cv2.imwrite(str(d / "input" / f"{n}_x.jpg"), photo(SHEET, shapes))
    jobs.write(d, {"id": d.name, "mode": "views", "status": "uploaded", "created": "x", "inputs": [], "outputs": []})
    return d


def test_pipeline_straightens_slightly_tilted_part(tmp_path, monkeypatch):
    d = _job(tmp_path, monkeypatch, tilt_deg=1.5)  # dibujo ligeramente torcido sobre la hoja
    pipeline.process_views(d)
    job = jobs.read(d)
    assert job["status"] == "done", job
    assert job["dims"]["ancho"] == pytest.approx(40.0, abs=0.3) and job["dims"]["fondo"] == pytest.approx(20.0, abs=0.3)
    scad = (d / "output" / "pieza.scad").read_text()
    planta = re.search(r"module planta\(\).*?points=\[(.*?)\], paths", scad).group(1)
    assert planta.count("],[") == 3  # 4 vértices
    m = trimesh.load(d / "output" / "pieza.stl")
    assert m.volume == pytest.approx(40 * 20 * 30, rel=0.02)

    pipeline.process_views(d, {"enderezar": 0})  # sin enderezar, la caja del contorno inclinado es mayor
    assert jobs.read(d)["dims"]["ancho"] > 40.3
    assert jobs.read(d)["params"] == {"enderezar": 0.0}


def test_preview_reports_straightened_size(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    d = _job(tmp_path, monkeypatch, tilt_deg=2.0)
    r = TestClient(main.app).get(f"/api/jobs/{d.name}/preview/planta.png")
    info = __import__("json").loads(r.headers["X-Preview-Info"])
    assert info["ancho"] == pytest.approx(40.0, abs=0.4) and info["alto"] == pytest.approx(20.0, abs=0.4)
