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


def _upload_L(c):
    shots = {
        "planta": [("rect", 0, (60, 100, 40, 20))],
        "alzado": [("poly", 0, [(60, 130), (100, 130), (100, 120), (70, 120), (70, 100), (60, 100)])],
        "perfil": [("rect", 0, (60, 100, 20, 30))],
    }
    files = [("files", (f"{n}.jpg", cv2.imencode(".jpg", photo(SHEET, s))[1].tobytes(), "image/jpeg"))
             for n, s in shots.items()]
    return c.post("/api/jobs", data={"mode": "views", "views": ",".join(shots)}, files=files).json()["id"]


def test_params_rescale_and_holgura(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import main
    monkeypatch.setattr(main, "STORAGE", tmp_path)
    c = TestClient(main.app)
    jid = _upload_L(c)
    job = c.get(f"/api/jobs/{jid}").json()
    assert job["status"] == "done" and job["dims"]["ancho"] == pytest.approx(40, abs=1)

    assert c.post(f"/api/jobs/{jid}/params", json={"ancho": 44.0, "alto": 33.0}).status_code == 200
    job = c.get(f"/api/jobs/{jid}").json()
    assert job["status"] == "done" and job["params"] == {"ancho": 44.0, "alto": 33.0}
    m = trimesh.load(tmp_path / jid / "output" / "pieza.stl")
    assert np.allclose(m.extents, [44, 20, 33], atol=1.2)

    c.post(f"/api/jobs/{jid}/params", json={"holgura": 0.5})
    m = trimesh.load(tmp_path / jid / "output" / "pieza.stl")
    assert m.extents[0] == pytest.approx(41, abs=1.2)  # +0,5 por cada lado
