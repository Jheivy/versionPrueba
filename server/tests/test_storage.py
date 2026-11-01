import os
import time

from fastapi.testclient import TestClient

from app import jobs, storage


def client(tmp_path, monkeypatch):
    from app import main
    monkeypatch.setattr(main, "STORAGE", tmp_path)
    return TestClient(main.app)


def _job(tmp_path, name, status="done", age_days=0.0):
    d = tmp_path / name
    (d / "input").mkdir(parents=True)
    (d / "input" / "f.bin").write_bytes(b"x" * 1000)
    jobs.write(d, {"id": name, "status": status, "created": "2020-01-01T00:00:00+00:00", "inputs": [], "outputs": []})
    t = time.time() - age_days * 86400
    os.utime(d / "job.json", (t, t))
    return d


def test_photo_over_limit_rejected_without_leftovers(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_MAX_PHOTO_MB", "0.001")      # ~1 KB
    c = client(tmp_path, monkeypatch)
    big = [("files", ("a.jpg", b"x" * 5000, "image/jpeg"))]
    r = c.post("/api/jobs", data={"mode": "views", "views": "planta"}, files=big)
    assert r.status_code == 413 and "límite" in r.json()["detail"]
    assert list(tmp_path.iterdir()) == []


def test_video_has_its_own_larger_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_MAX_PHOTO_MB", "0.001")
    monkeypatch.setenv("SCAN2PRINT_MAX_VIDEO_MB", "1")
    assert storage.limit_for("v.mov") > storage.limit_for("f.jpg")
    c = client(tmp_path, monkeypatch)
    r = c.post("/api/jobs", data={"mode": "video"}, files=[("files", ("v.mp4", b"x" * 5000, "video/mp4"))])
    assert r.status_code == 201


def test_content_length_rejected_early(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_MAX_VIDEO_MB", "1")
    c = client(tmp_path, monkeypatch)
    headers = {"content-length": str(50 * 1024 * 1024), "content-type": "multipart/form-data; boundary=x"}
    r = c.post("/api/jobs", content=b"x", headers=headers)
    assert r.status_code == 413


def test_too_many_files(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_MAX_FILES", "2")
    c = client(tmp_path, monkeypatch)
    files = [("files", (f"{i}.jpg", b"i", "image/jpeg")) for i in range(3)]
    assert c.post("/api/jobs", data={"mode": "video"}, files=files).status_code == 413


def test_replace_view_over_limit_releases_job(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    files = [("files", (f"{v}.jpg", b"img", "image/jpeg")) for v in ("a", "b", "c")]
    jid = c.post("/api/jobs", data={"mode": "views", "views": "planta,alzado,perfil"}, files=files).json()["id"]
    monkeypatch.setenv("SCAN2PRINT_MAX_PHOTO_MB", "0.001")
    r = c.post(f"/api/jobs/{jid}/inputs", data={"view": "planta"}, files={"file": ("n.jpg", b"x" * 5000, "image/jpeg")})
    assert r.status_code == 413
    assert not jobs.is_busy(tmp_path / jid)


def test_cleanup_removes_only_old_idle_jobs(tmp_path):
    old = _job(tmp_path, "a" * 32, age_days=40)
    new = _job(tmp_path, "b" * 32, age_days=2)
    stuck = _job(tmp_path, "c" * 32, status="processing", age_days=60)
    busy = _job(tmp_path, "d" * 32, age_days=60)
    assert jobs.reserve(busy)
    try:
        r = storage.cleanup(tmp_path, 30)
    finally:
        jobs.release(busy)
    assert r["removed"] == 1 and r["freed"] >= 1000
    assert not old.exists() and new.exists() and stuck.exists() and busy.exists()
    assert storage.cleanup(tmp_path, 0) == {"removed": 0, "freed": 0}


def test_storage_endpoints(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_RETENTION_DAYS", "10")
    c = client(tmp_path, monkeypatch)
    _job(tmp_path, "a" * 32, age_days=20)
    _job(tmp_path, "b" * 32, age_days=1)
    info = c.get("/api/storage").json()
    assert info["jobs"] == 2 and info["bytes"] >= 2000 and info["retention_days"] == 10
    assert c.post("/api/storage/cleanup", json={"days": 0.5}).status_code == 400
    assert c.post("/api/storage/cleanup", json={"days": "x"}).status_code == 400
    assert c.post("/api/storage/cleanup", json={}).json()["removed"] == 1       # usa la retención configurada
    assert c.get("/api/storage").json()["jobs"] == 1
