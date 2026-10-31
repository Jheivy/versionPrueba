import json
import threading

from fastapi.testclient import TestClient

from app import jobs, main, pipeline


def make_job(tmp_path, status="done", mode="views"):
    d = tmp_path / ("a" * 32)
    (d / "input").mkdir(parents=True)
    jobs.write(d, {"id": d.name, "mode": mode, "status": status, "created": "2026-01-01T00:00:00+00:00",
                   "inputs": [], "outputs": []})
    return d


def test_atomic_update_leaves_no_temp(tmp_path):
    d = make_job(tmp_path)
    threads = [threading.Thread(target=jobs.update, args=(d,), kwargs={f"k{i}": i}) for i in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    job = jobs.read(d)
    assert all(job[f"k{i}"] == i for i in range(20))  # ninguna actualización perdida
    assert not list(d.glob("*.tmp"))


def test_busy_job_rejects_new_work(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORAGE", tmp_path)
    d = make_job(tmp_path, status="review")
    c = TestClient(main.app)
    assert jobs.reserve(d)  # simula un procesado en curso
    try:
        for r in (c.post(f"/api/jobs/{d.name}/params", json={}),
                  c.post(f"/api/jobs/{d.name}/confirm"),
                  c.post(f"/api/jobs/{d.name}/inputs", data={"view": "planta"},
                         files={"file": ("p.jpg", b"x", "image/jpeg")}),
                  c.delete(f"/api/jobs/{d.name}")):
            assert r.status_code == 409 and "procesando" in r.json()["detail"]
        assert jobs.read(d)["status"] == "review"  # nada se tocó
    finally:
        jobs.release(d)


def test_reservation_released_after_processing(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORAGE", tmp_path)
    monkeypatch.setattr(pipeline, "_notify", lambda p: None)
    d = make_job(tmp_path, status="error")
    c = TestClient(main.app)
    assert c.post(f"/api/jobs/{d.name}/params", json={}).status_code == 200
    assert jobs.read(d)["status"] == "error"  # sin fotos: falla, pero libera
    assert not jobs.is_busy(d)
    assert c.post(f"/api/jobs/{d.name}/params", json={}).status_code == 200


def test_restart_marks_stale_jobs(tmp_path, monkeypatch):
    stale = make_job(tmp_path, status="processing")
    done = tmp_path / ("b" * 32)
    (done / "input").mkdir(parents=True)
    jobs.write(done, {"id": done.name, "mode": "views", "status": "done", "created": "x", "inputs": [], "outputs": []})
    (stale / "job.json.1.2.tmp").write_text("{}")
    monkeypatch.setattr(main, "STORAGE", tmp_path)
    with TestClient(main.app):  # ejecuta el arranque (lifespan)
        pass
    j = json.loads((stale / "job.json").read_text())
    assert j["status"] == "error" and j["error"] == jobs.STALE_MSG and j["step"] is None
    assert jobs.read(done)["status"] == "done"
    assert not list(stale.glob("*.tmp"))
