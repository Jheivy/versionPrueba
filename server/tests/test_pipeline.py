import json

import cv2
import numpy as np
import pytest
import trimesh
from synth import photo

from app.pipeline import process_views
from app.views.contours import extract
from app.views.markers import render_sheet
from app.views.rectify import rectify

SHEET = render_sheet()


def test_extract_rect_with_hole():
    img = photo(SHEET, [("rect", 0, (60, 100, 40, 20)), ("circle", 255, (70, 110, 4))])
    polys = extract(rectify(img, 10.0), 10.0)
    xs = [p[0] for p in polys[0]]; ys = [p[1] for p in polys[0]]
    assert max(xs) == pytest.approx(40, abs=0.6) and max(ys) == pytest.approx(20, abs=0.6)
    assert len(polys) == 2  # exterior + agujero


def test_full_job_makes_stl(tmp_path):
    # pieza en L: planta 40x20, alzado en L (40x30), perfil 20x30
    inp = tmp_path / "input"; inp.mkdir()
    shots = {
        "planta": [("rect", 0, (60, 100, 40, 20))],
        "alzado": [("poly", 0, [(60, 130), (100, 130), (100, 120), (70, 120), (70, 100), (60, 100)])],
        "perfil": [("rect", 0, (60, 100, 20, 30))],
    }
    for name, shapes in shots.items():
        cv2.imwrite(str(inp / f"{name}_x.jpg"), photo(SHEET, shapes))
    (tmp_path / "job.json").write_text(json.dumps({"id": "x", "status": "uploaded"}))
    process_views(tmp_path)
    job = json.loads((tmp_path / "job.json").read_text())
    assert job["status"] == "done", job
    m = trimesh.load(tmp_path / "output" / "pieza.stl")
    assert np.allclose(m.extents, [40, 20, 30], atol=1.0)
    assert m.is_watertight
