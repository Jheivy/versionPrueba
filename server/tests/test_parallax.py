import json

import cv2
import numpy as np
import pytest
from synth import photo3d

from app.pipeline import process_views
from app.views import parallax
from app.views.markers import render_sheet
from app.views.rectify import rectify

SHEET = render_sheet()
BOX = (40.0, 20.0, 30.0)     # ancho, fondo, alto


def _views(dist):
    a, f, h = BOX
    return {                  # cada vista: la caja de pie sobre la cara correspondiente
        "planta": photo3d(SHEET, (85, 138.5, a, f, h), dist),
        "alzado": photo3d(SHEET, (85, 134, a, h, f), dist),
        "perfil": photo3d(SHEET, (95, 134, f, h, a), dist),
    }


def _run(tmp_path, dist, params=None):
    (tmp_path / "input").mkdir(exist_ok=True)
    for n, img in _views(dist).items():
        cv2.imwrite(str(tmp_path / "input" / f"{n}_x.png"), img)
    (tmp_path / "job.json").write_text(json.dumps({"id": "x", "status": "uploaded"}))
    process_views(tmp_path, params)
    return json.loads((tmp_path / "job.json").read_text())


def test_camera_pose_recovers_distance():
    img = photo3d(SHEET, (85, 120, 40, 20, 0.01), 300.0)
    _, h = rectify(img, 10.0, return_h=True)
    pose = parallax.camera_pose(h, img.shape)
    assert pose["dist"] == pytest.approx(300, rel=0.03)
    assert pose["nadir"] == pytest.approx((105, 148.5), abs=8)


def test_without_correction_the_box_is_inflated(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_PARALLAX", "off")
    job = _run(tmp_path, 300.0)
    assert job["dims"]["ancho"] > 42      # ~7-11 % de más con la cámara a 30 cm


@pytest.mark.parametrize("dist", [250.0, 300.0, 450.0])
def test_correction_recovers_true_size(tmp_path, monkeypatch, dist):
    monkeypatch.setenv("SCAN2PRINT_PARALLAX", "on")
    job = _run(tmp_path, dist)
    assert job["status"] == "done", job
    for dim, true in zip(("ancho", "fondo", "alto"), BOX, strict=True):
        assert job["dims"][dim] == pytest.approx(true, abs=1.2), (dim, job["dims"])
    assert job["parallax"]["planta"]["factor"] < 1
    assert job["parallax"]["planta"]["dist"] == pytest.approx(dist, rel=0.05)
    assert not job["warnings"]


def test_user_can_disable_it(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_PARALLAX", "on")
    job = _run(tmp_path, 300.0, {"paralaje": 0})
    assert job["parallax"] == {} and job["dims"]["ancho"] > 42


def test_factor_rejects_unreliable_cases():
    assert parallax.factor(30, 300) == pytest.approx(0.9)
    assert parallax.factor(150, 300) is None      # pieza enorme respecto a la distancia
    assert parallax.camera_pose(np.zeros((3, 3)), (2000, 1600)) is None


def test_off_center_piece_keeps_small_residual(tmp_path, monkeypatch):
    """Con la pieza lejos del punto bajo la cámara, el borde cercano se ve por su base y no por su cara
    superior: queda un residuo pequeño (el aviso de vistas lo señala si pasa de 0,8 mm)."""
    monkeypatch.setenv("SCAN2PRINT_PARALLAX", "on")
    (tmp_path / "input").mkdir()
    a, f, h = BOX
    shots = {"planta": (85, 120, a, f, h), "alzado": (85, 134, a, h, f), "perfil": (95, 134, f, h, a)}
    for n, box in shots.items():
        cv2.imwrite(str(tmp_path / "input" / f"{n}_x.png"), photo3d(SHEET, box, 300.0))
    (tmp_path / "job.json").write_text(json.dumps({"id": "x", "status": "uploaded"}))
    process_views(tmp_path)
    job = json.loads((tmp_path / "job.json").read_text())
    for dim, true in zip(("ancho", "fondo", "alto"), BOX, strict=True):
        assert job["dims"][dim] == pytest.approx(true, abs=1.6)
