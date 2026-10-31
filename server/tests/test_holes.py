import math
import shutil
import subprocess

import numpy as np
import pytest
import trimesh
from synth import photo

from app import jobs, main, pipeline
from app.views.holes import as_circle, finalize, split_circles
from app.views.markers import render_sheet
from app.views.scad_writer import build_scad

SHEET = render_sheet()


def circle_poly(cx, cy, d, n=24):
    return [(cx + d / 2 * math.cos(2 * math.pi * i / n), cy + d / 2 * math.sin(2 * math.pi * i / n)) for i in range(n)]


def test_detects_circle_and_rejects_other_shapes():
    cx, cy, d = as_circle(circle_poly(10, 5, 8))
    assert (round(cx, 2), round(cy, 2), round(d, 2)) == (10, 5, 8)
    assert as_circle([(0, 0), (6, 0), (6, 6), (0, 6)]) is None                     # cuadrado
    assert as_circle(circle_poly(0, 0, 8, n=6)) is None                            # hexágono (alojamiento de tuerca)
    assert as_circle([(x, y) for x, y in circle_poly(0, 0, 8, n=24)][:14]) is None  # arco, no un círculo cerrado
    slot = [(0, 0), (10, 0), (10, 3), (0, 3)]
    assert as_circle(slot) is None


def test_split_keeps_outline_and_non_circular_holes():
    outer = [(0, 0), (40, 0), (40, 20), (0, 20)]
    square = [(30, 5), (35, 5), (35, 10), (30, 10)]
    kept, circles = split_circles([outer, circle_poly(30, 10, 4), square, circle_poly(10, 10, 6)])
    assert kept == [outer, square]
    assert [round(c[0]) for c in circles] == [10, 30]  # ordenados por posición


def test_standard_size_is_only_a_hint():
    assert finalize(3.27) == (3.3, "M3")   # el valor medido se conserva; la etiqueta solo sugiere
    assert finalize(8.43) == (8.4, "M8")
    assert finalize(5.09) == (5.1, None)   # un Ø5,0 real NO se convierte en M5 (5,3)
    assert finalize(7.96) == (8.0, None)


def test_scad_has_parametric_holes():
    outline = [(0, 0), (40, 0), (40, 20), (0, 20)]
    s = build_scad([outline], altura=10, circles={"planta": [(10, 10, 3.2, "M3"), (30, 10, 6.0, None)]})
    assert "diam_agujero_planta_1 = 3.200;  // posible M3 (paso medio)" in s
    assert "pos_agujero_planta_2 = [30.000, 10.000];" in s
    assert "circle(d=diam_agujero_planta_2" in s


@pytest.mark.skipif(not shutil.which("openscad"), reason="openscad no instalado")
def test_hole_volume(tmp_path):
    box = [(0, 0), (40, 0), (40, 20), (0, 20)]
    side = [(0, 0), (40, 0), (40, 30), (0, 30)]
    prof = [(0, 0), (20, 0), (20, 30), (0, 30)]
    (tmp_path / "p.scad").write_text(build_scad([box], [side], [prof], circles={"planta": [(20, 10, 6.0, None)]}))
    subprocess.run(["openscad", "-q", "-o", str(tmp_path / "p.stl"), str(tmp_path / "p.scad")], check=True)
    m = trimesh.load(tmp_path / "p.stl")
    assert m.volume == pytest.approx(40 * 20 * 30 - math.pi * 9 * 30, rel=0.005)  # caja menos cilindro Ø6


def _job(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORAGE", tmp_path / "jobs")
    monkeypatch.setattr(pipeline, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(pipeline, "_notify", lambda p: None)
    d = tmp_path / "jobs" / ("c" * 32)
    (d / "input").mkdir(parents=True)
    import cv2
    shots = {"planta": [("rect", 0, (60, 100, 40, 20)), ("circle", 255, (70, 110, 4))],
             "alzado": [("rect", 0, (60, 100, 40, 30))], "perfil": [("rect", 0, (60, 100, 20, 30))]}
    for n, s in shots.items():
        cv2.imwrite(str(d / "input" / f"{n}_x.jpg"), photo(SHEET, s))
    jobs.write(d, {"id": d.name, "mode": "views", "status": "uploaded", "created": "x", "inputs": [], "outputs": []})
    return d


def test_pipeline_detects_and_overrides_hole(tmp_path, monkeypatch):
    d = _job(tmp_path, monkeypatch)
    pipeline.process_views(d)
    job = jobs.read(d)
    assert job["status"] == "done", job
    (hole,) = job["holes"]
    assert hole["view"] == "planta" and hole["n"] == 1 and hole["diam"] == pytest.approx(8.0, abs=0.15)
    assert hole["x"] == pytest.approx(10, abs=0.6) and hole["y"] == pytest.approx(10, abs=0.6)
    assert "diam_agujero_planta_1" in (d / "output" / "pieza.scad").read_text()

    pipeline.process_views(d, {"d_planta_1": 9.0})  # Ø medido con calibre
    assert "diam_agujero_planta_1 = 9.000;" in (d / "output" / "pieza.scad").read_text()
    m = trimesh.load(d / "output" / "pieza.stl")
    assert m.volume == pytest.approx(np.prod(m.extents) - math.pi * 4.5**2 * 30, rel=0.03)
    assert jobs.read(d)["holes"][0]["diam"] == 9.0
