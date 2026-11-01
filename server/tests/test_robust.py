import json
import os
import time

import pytest
from fastapi.testclient import TestClient

from app import jobs, pipeline, storage


def client(tmp_path, monkeypatch):
    from app import main
    monkeypatch.setattr(main, "STORAGE", tmp_path)
    return TestClient(main.app)


def _job(tmp_path, name, size=1000, status="done", age_days=0.0):
    d = tmp_path / name
    (d / "input").mkdir(parents=True)
    (d / "input" / "f.bin").write_bytes(b"x" * size)
    jobs.write(d, {"id": name, "status": status, "created": "2020-01-01T00:00:00+00:00", "inputs": [], "outputs": []})
    t = time.time() - age_days * 86400
    os.utime(d / "job.json", (t, t))
    return d


def test_chunked_body_without_content_length_is_cut(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_MAX_VIDEO_MB", "0.5")      # tope de la petición ~8,5 MB
    c = client(tmp_path, monkeypatch)

    def body():
        for _ in range(20):
            yield b"x" * (1024 * 1024)                          # 20 MB en trozos: no hay Content-Length

    r = c.post("/api/jobs", content=body(), headers={"content-type": "multipart/form-data; boundary=x"})
    assert r.status_code == 413 and "límite" in r.json()["detail"]
    assert list(tmp_path.iterdir()) == []


def test_normal_upload_still_passes_the_limit_middleware(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    r = c.post("/api/jobs", data={"mode": "video"}, files=[("files", ("v.mp4", b"x" * 5000, "video/mp4"))])
    assert r.status_code == 201


def test_make_room_evicts_oldest_idle_jobs_only(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_MAX_STORAGE_GB", "0.000015")    # ~16 KB
    old = _job(tmp_path, "a" * 32, 4000, age_days=30)
    mid = _job(tmp_path, "b" * 32, 4000, age_days=10)
    stuck = _job(tmp_path, "c" * 32, 4000, status="processing", age_days=90)
    assert storage.make_room(tmp_path, 4000) == 1
    assert not old.exists() and mid.exists() and stuck.exists()        # nunca toca lo que se procesa


def test_make_room_507_when_nothing_can_go(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_MAX_STORAGE_GB", "0.00001")
    _job(tmp_path, "a" * 32, 9000, status="processing")
    c = client(tmp_path, monkeypatch)
    r = c.post("/api/jobs", data={"mode": "video"}, files=[("files", ("v.mp4", b"x" * 5000, "video/mp4"))])
    assert r.status_code == 507 and "espacio" in r.json()["detail"]


def test_storage_cap_zero_means_unlimited(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_MAX_STORAGE_GB", "0")
    _job(tmp_path, "a" * 32, 9000)
    assert storage.make_room(tmp_path, 10**12) == 0


def test_opening_a_job_counts_as_use(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    d = _job(tmp_path, "b" * 32, age_days=60)
    assert c.get(f"/api/jobs/{'b' * 32}").status_code == 200
    assert storage.cleanup(tmp_path, 30)["removed"] == 0 and d.exists()


def test_regenerating_replaces_previous_export(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setattr(pipeline, "OUT_DIR", out)
    d = tmp_path / "job"
    (d / "output").mkdir(parents=True)
    (d / "output" / "pieza.stl").write_bytes(b"s")
    (d / "output" / "pieza.scad").write_bytes(b"c")
    pipeline._export(d, "deadbeef" + "0" * 24)
    time.sleep(1.1)                                            # el nombre lleva la hora al segundo
    second = pipeline._export(d, "deadbeef" + "0" * 24)
    assert sorted(p.name for p in out.iterdir()) == sorted(os.path.basename(v) for v in second.values())
    (out / "otra-cosa.txt").write_text("mía")
    pipeline._export(d, "deadbeef" + "0" * 24)
    assert (out / "otra-cosa.txt").exists()                    # solo toca sus propios .stl/.scad


def test_openscad_failure_is_readable_and_logged(tmp_path, monkeypatch, caplog):
    import subprocess

    def boom(*a, **k):
        raise subprocess.CalledProcessError(1, "openscad", stderr="WARNING: x\nERROR: Parser error in line 3\n")

    monkeypatch.setattr(pipeline.subprocess, "run", boom)
    with caplog.at_level("ERROR", logger="scan2print"), pytest.raises(RuntimeError) as e:
        pipeline._openscad(tmp_path / "a.scad", tmp_path / "a.stl")
    assert "Parser error" in str(e.value) and "registro" in str(e.value)
    assert "Parser error" in caplog.text


def test_unexpected_error_is_logged_with_traceback(tmp_path, monkeypatch, caplog):
    d = tmp_path / "j"
    (d / "input").mkdir(parents=True)
    (d / "job.json").write_text(json.dumps({"id": "j", "status": "uploaded"}))
    monkeypatch.setattr(pipeline.cv2, "imread", lambda *a: (_ for _ in ()).throw(KeyError("raro")))
    (d / "input" / "planta_a.png").write_bytes(b"x")
    with caplog.at_level("ERROR", logger="scan2print"):
        pipeline.process_views(d)
    assert "falló" in caplog.text and "KeyError" in caplog.text
