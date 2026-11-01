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


def stadium(cx, cy, w, length, ang_deg, n=14):
    """Polígono de una ranura: dos semicírculos de Ø `w` con centros separados `length - w`, girada `ang_deg`."""
    half, t = (length - w) / 2, math.radians(ang_deg)
    pts = [(half + w / 2 * math.cos(a), w / 2 * math.sin(a)) for a in np.linspace(-math.pi / 2, math.pi / 2, n)]
    pts += [(-half - w / 2 * math.cos(a), -w / 2 * math.sin(a)) for a in np.linspace(-math.pi / 2, math.pi / 2, n)]
    return [(cx + x * math.cos(t) - y * math.sin(t), cy + x * math.sin(t) + y * math.cos(t)) for x, y in pts]


@pytest.mark.parametrize("ang", [0, 30, 90, 135])
def test_detects_slot_with_size_and_angle(ang):
    from app.views.holes import as_slot
    cx, cy, w, length, got = as_slot(stadium(20, 10, 5, 14, ang))
    assert (round(cx, 1), round(cy, 1), round(w, 1), round(length, 1)) == (20, 10, 5, 14)
    assert got == pytest.approx(ang % 180, abs=1.0) or abs(got - ang % 180) in (0, 180)


def test_slot_is_not_a_circle_rectangle_or_oval():
    from app.views.holes import as_slot
    assert as_slot(circle_poly(0, 0, 8)) is None                                  # círculo: lo reconoce as_circle
    assert as_slot([(0, 0), (14, 0), (14, 5), (0, 5)]) is None                    # rectángulo (esquinas vivas)
    oval = [(7 * math.cos(a), 3 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    assert as_slot(oval) is None                                                  # elipse
    assert as_slot(stadium(0, 0, 5, 5.5, 0)) is None                              # casi círculo: no es ranura
    assert as_circle(stadium(0, 0, 5, 14, 0)) is None


def test_split_holes_separates_circles_slots_and_the_rest():
    from app.views.holes import split_holes
    outer = [(0, 0), (60, 0), (60, 30), (0, 30)]
    square = [(50, 5), (55, 5), (55, 10), (50, 10)]
    kept, circles, slots = split_holes([outer, circle_poly(10, 10, 4), stadium(30, 15, 5, 14, 0), square])
    assert kept == [outer, square] and len(circles) == 1 and len(slots) == 1
    assert slots[0][:2] == pytest.approx((30, 15), abs=0.1)


def test_scad_has_parametric_slots():
    s = build_scad([[(0, 0), (60, 0), (60, 30), (0, 30)]], altura=10, slots={"planta": [(30, 15, 5.0, 14.0, 20.0)]})
    for line in ("ancho_ranura_planta_1 = 5.000;", "largo_ranura_planta_1 = 14.000;", "ang_ranura_planta_1 = 20.0;",
                 "pos_ranura_planta_1 = [30.000, 15.000];", "hull()"):
        assert line in s


@pytest.mark.skipif(not shutil.which("openscad"), reason="openscad no instalado")
def test_slot_volume(tmp_path):
    box = [(0, 0), (60, 0), (60, 30), (0, 30)]
    side = [(0, 0), (60, 0), (60, 20), (0, 20)]
    prof = [(0, 0), (30, 0), (30, 20), (0, 20)]
    slot_area = math.pi * 2.5**2 + 9 * 5                       # 2 semicírculos + rectángulo (9 x 5) = Ø5, 14 de largo
    (tmp_path / "p.scad").write_text(build_scad([box], [side], [prof], slots={"planta": [(30, 15, 5.0, 14.0, 0.0)]}))
    subprocess.run(["openscad", "-q", "-o", str(tmp_path / "p.stl"), str(tmp_path / "p.scad")], check=True)
    assert trimesh.load(tmp_path / "p.stl").volume == pytest.approx(60 * 30 * 20 - slot_area * 20, rel=0.005)


def test_pipeline_detects_a_slot_and_lets_you_measure_it(tmp_path, monkeypatch):
    import cv2
    monkeypatch.setattr(main, "STORAGE", tmp_path / "jobs")
    monkeypatch.setattr(pipeline, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(pipeline, "_notify", lambda p: None)
    d = tmp_path / "jobs" / ("d" * 32)
    (d / "input").mkdir(parents=True)
    slot = [(60 + x, 100 + y) for x, y in stadium(30, 10, 5, 16, 0, n=20)]
    shots = {"planta": [("rect", 0, (60, 100, 60, 20)), ("poly", 255, slot)],
             "alzado": [("rect", 0, (60, 100, 60, 30))], "perfil": [("rect", 0, (60, 100, 20, 30))]}
    for n, s in shots.items():
        cv2.imwrite(str(d / "input" / f"{n}_x.jpg"), photo(SHEET, s))
    jobs.write(d, {"id": d.name, "mode": "views", "status": "uploaded", "created": "x", "inputs": [], "outputs": []})
    pipeline.process_views(d)
    job = jobs.read(d)
    assert job["status"] == "done", job
    (slot_hole,) = job["holes"]
    assert slot_hole["kind"] == "slot" and slot_hole["view"] == "planta"
    assert slot_hole["width"] == pytest.approx(5.0, abs=0.3) and slot_hole["length"] == pytest.approx(16.0, abs=0.3)
    assert slot_hole["angle"] % 180 == pytest.approx(0, abs=2) or slot_hole["angle"] % 180 == pytest.approx(180, abs=2)
    text = (d / "output" / "pieza.scad").read_text()
    assert "ancho_ranura_planta_1" in text and "diam_agujero" not in text
    pipeline.process_views(d, {"w_planta_1": 6.0, "l_planta_1": 20.0})        # medidos con calibre
    assert "ancho_ranura_planta_1 = 6.000;" in (d / "output" / "pieza.scad").read_text()
    assert "largo_ranura_planta_1 = 20.000;" in (d / "output" / "pieza.scad").read_text()
    assert jobs.read(d)["holes"][0]["length"] == 20.0
