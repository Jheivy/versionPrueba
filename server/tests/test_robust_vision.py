import json

import cv2
import numpy as np
import pytest
from synth import scene

from app.pipeline import process_views
from app.views.contours import NoShapeFound, extract
from app.views.markers import render_sheet
from app.views.rectify import rectify_full

SHEET = render_sheet()
PX = 10.0


def measure(img, **kw):
    info = {}
    poly = extract(rectify_full(img, PX)[0], PX, info=info, **kw)[0]
    return max(x for x, _ in poly), max(y for _, y in poly), info["contrast"]


@pytest.mark.parametrize("name,kw,tol", [
    ("negro", dict(color=(0, 0, 0)), 0.5),
    ("gris oscuro", dict(color=(50, 50, 50)), 0.5),
    ("gris medio", dict(color=(120, 120, 120)), 0.5),
    ("amarillo claro", dict(color=(60, 200, 235)), 0.5),     # casi igual de brillante que el papel: lo separa el color
    ("azul", dict(color=(200, 90, 40)), 0.5),
    ("ruido del sensor", dict(color=(0, 0, 0), noise=8), 0.6),
    ("degradado de luz del 55 %", dict(color=(0, 0, 0), gradient=0.55), 0.5),    # antes: toda la hoja era «pieza»
    ("sombra suave", dict(color=(0, 0, 0), shadow=0.45), 0.5),
    ("pieza gris con sombra y degradado", dict(color=(110, 110, 110), shadow=0.4, gradient=0.4), 1.3),
])
def test_contour_survives_real_lighting(name, kw, tol):
    w, h, _ = measure(scene(SHEET, **kw))
    assert w == pytest.approx(40, abs=tol) and h == pytest.approx(20, abs=tol), name


def test_tinted_light_does_not_turn_paper_into_piece():
    img = scene(SHEET, color=(0, 0, 0)).astype(np.float32) * np.array([0.8, 0.95, 1.1], np.float32)   # luz cálida
    w, h, _ = measure(np.clip(img, 0, 255).astype(np.uint8))
    assert w == pytest.approx(40, abs=0.5) and h == pytest.approx(20, abs=0.5)


def test_contrast_tells_a_clear_piece_from_a_dark_one():
    dark = measure(scene(SHEET, color=(0, 0, 0)))[2]
    clear = measure(scene(SHEET, color=(228, 228, 228)))[2]
    assert dark > 0.9 and clear < 0.2


def test_empty_sheet_still_finds_nothing():
    with pytest.raises(NoShapeFound):
        extract(rectify_full(scene(SHEET, box=(60, 100, 0.1, 0.1)), PX)[0], PX)


def test_rectify_reports_quality():
    info = rectify_full(scene(SHEET), PX)[2]
    assert info["markers"] == 4 and info["inliers"] == 16 and info["rms_mm"] < 0.2


def test_barrel_distortion_raises_the_error():
    img = scene(SHEET)
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)
    k = 0.12 * (nx ** 2 + ny ** 2)
    bent = cv2.remap(img, (xx + nx * k * w / 2).astype(np.float32), (yy + ny * k * h / 2).astype(np.float32),
                     cv2.INTER_LINEAR, borderValue=(200, 200, 200))
    assert rectify_full(bent, PX)[2]["rms_mm"] > 0.5 > rectify_full(img, PX)[2]["rms_mm"]


def _job(tmp_path, shots):
    (tmp_path / "input").mkdir()
    for n, img in shots.items():
        cv2.imwrite(str(tmp_path / "input" / f"{n}_x.png"), img)
    (tmp_path / "job.json").write_text(json.dumps({"id": "x", "status": "uploaded"}))
    process_views(tmp_path)
    return json.loads((tmp_path / "job.json").read_text())


def test_pipeline_records_quality_and_warns_on_a_clear_piece(tmp_path):
    job = _job(tmp_path, {"planta": scene(SHEET, color=(228, 228, 228))})
    assert job["quality"]["planta"]["markers"] == 4
    kinds = [w["kind"] for w in job["quality_warnings"]]
    assert kinds == ["contrast"] and job["quality_warnings"][0]["view"] == "planta"


def test_pipeline_has_no_warnings_on_a_good_photo(tmp_path):
    job = _job(tmp_path, {"planta": scene(SHEET, color=(0, 0, 0))})
    assert job["status"] == "done" and job["quality_warnings"] == []


def test_two_visible_markers_work_but_are_flagged(tmp_path):
    img = scene(SHEET)
    img[img.shape[0] * 2 // 3:] = 200                  # tapa los dos marcadores de abajo
    assert rectify_full(img, PX)[2]["markers"] == 2
    job = _job(tmp_path, {"planta": img})
    assert job["status"] == "done"
    assert [w["kind"] for w in job["quality_warnings"]] == ["markers"]
    assert "2 marcadores" in job["quality_warnings"][0]["message"]
