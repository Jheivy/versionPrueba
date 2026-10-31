import cv2
import numpy as np
import pytest
import trimesh
from fastapi.testclient import TestClient

from app import main, pipeline, pipeline_video
from app.photogrammetry.frames import extract_frames
from app.photogrammetry.mesh import postprocess


def make_video(path, n=150, fps=30, blur_every=3):
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 240))
    rng = np.random.default_rng(0)
    base = rng.integers(0, 255, (240, 320, 3), dtype=np.uint8)
    for i in range(n):
        f = np.roll(base, i * 2, axis=1)
        if i % blur_every:
            f = cv2.GaussianBlur(f, (0, 0), 4)
        w.write(f)
    w.release()


def test_extract_picks_sharp_frames(tmp_path):
    make_video(tmp_path / "v.mp4")
    n = extract_frames(tmp_path / "v.mp4", tmp_path / "f", step_s=0.4)
    assert 10 <= n <= 13  # 5 s / 0,4 s
    from app.photogrammetry.frames import _sharpness
    sharp = [_sharpness(cv2.imread(str(p))) for p in sorted((tmp_path / "f").glob("*.jpg"))]
    assert min(sharp) > 500  # se eligieron los no borrosos


def test_too_short_video(tmp_path):
    make_video(tmp_path / "v.mp4", n=30)
    with pytest.raises(ValueError, match="fotogramas"):
        extract_frames(tmp_path / "v.mp4", tmp_path / "f")


def fake_obj(path):
    """Caja 0,10 x 0,03 x 0,05 m (x,y-arriba,z) + fragmento flotante pequeño."""
    box = trimesh.creation.box([0.10, 0.03, 0.05])
    junk = trimesh.creation.box([0.005] * 3)
    junk.apply_translation([0.2, 0.2, 0.2])
    trimesh.util.concatenate([box, junk]).export(path)


def test_postprocess_orient_scale(tmp_path):
    fake_obj(tmp_path / "m.obj")
    info = postprocess(tmp_path / "m.obj", tmp_path / "o.stl")
    m = trimesh.load(tmp_path / "o.stl")
    assert np.allclose(m.extents, [100, 50, 30], atol=0.1)  # Y-up -> Z-up, m -> mm, sin fragmento
    assert m.bounds[0][2] == pytest.approx(0, abs=1e-6) and info["scale_estimated"]
    info = postprocess(tmp_path / "m.obj", tmp_path / "o2.stl", largo_mm=200)
    assert np.allclose(trimesh.load(tmp_path / "o2.stl").extents, [200, 100, 60], atol=0.2)
    assert not info["scale_estimated"]


def test_video_job_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORAGE", tmp_path / "jobs")
    monkeypatch.setattr(pipeline, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(pipeline, "_notify", lambda p: None)

    calls = []

    def fake_capture(frames, out, detail="medium"):
        calls.append(detail)
        assert len(list(frames.glob("*.jpg"))) >= 10
        out.mkdir()
        fake_obj(out / "model.obj")
        return out / "model.obj"
    monkeypatch.setattr(pipeline_video, "run_object_capture", fake_capture)

    make_video(tmp_path / "v.mp4")
    c = TestClient(main.app)
    r = c.post("/api/jobs", data={"mode": "video"}, files=[("files", ("v.mp4", (tmp_path / "v.mp4").read_bytes(), "video/mp4"))])
    jid = r.json()["id"]
    job = c.get(f"/api/jobs/{jid}").json()
    assert job["status"] == "done", job
    assert job["mesh"]["scale_estimated"] and job["dims"]["ancho"] == pytest.approx(100, abs=0.1)
    c.post(f"/api/jobs/{jid}/params", json={"largo": 50})
    job = c.get(f"/api/jobs/{jid}").json()
    assert job["dims"]["ancho"] == pytest.approx(50, abs=0.1) and not job["mesh"]["scale_estimated"]
    assert calls == ["medium"]  # el reescalado reutilizó el .obj
    c.post(f"/api/jobs/{jid}/params", json={"largo": 80, "detalle": "full"})
    assert calls == ["medium", "full"]  # otro detalle sí reconstruye
    assert list((tmp_path / "out").glob("*.stl"))


def test_clear_error_without_mac(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORAGE", tmp_path / "jobs")
    monkeypatch.setattr(pipeline_video.sys, "platform", "linux")
    make_video(tmp_path / "v.mp4")
    c = TestClient(main.app)
    jid = c.post("/api/jobs", data={"mode": "video"}, files=[("files", ("v.mp4", (tmp_path / "v.mp4").read_bytes(), "video/mp4"))]).json()["id"]
    assert "solo está disponible en el Mac" in c.get(f"/api/jobs/{jid}").json()["error"]
