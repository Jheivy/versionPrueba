import pytest
from fastapi.testclient import TestClient

CID = "a1" * 16


def client(tmp_path, monkeypatch):
    from app import main
    monkeypatch.setattr(main, "STORAGE", tmp_path)
    return TestClient(main.app)


def post(c, cid=CID, name="v.mp4", data=b"x" * 2000):
    return c.post("/api/jobs", data={"mode": "video", "client_id": cid}, files=[("files", (name, data, "video/mp4"))])


def test_same_client_id_creates_one_job(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    first, second = post(c), post(c)
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"] == CID
    assert len(c.get("/api/jobs").json()) == 1
    assert (tmp_path / CID / "input" / "v.mp4").read_bytes() == b"x" * 2000     # no se vuelve a escribir


def test_retry_after_the_job_moved_on_returns_the_current_state(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    post(c)
    c.patch(f"/api/jobs/{CID}", json={"name": "Renombrada"})
    assert post(c).json()["name"] == "Renombrada"


@pytest.mark.parametrize("bad", ["x", "A1" * 16, "a1" * 15, "../" + "a1" * 14, "g1" * 16])
def test_invalid_client_id_is_rejected(tmp_path, monkeypatch, bad):
    c = client(tmp_path, monkeypatch)
    assert post(c, cid=bad).status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_upload_in_progress_with_the_same_id_is_409(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    (tmp_path / CID / "input").mkdir(parents=True)       # otra subida con ese id todavía sin job.json
    r = post(c)
    assert r.status_code == 409 and "en curso" in r.json()["detail"]


def test_without_client_id_nothing_changes(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    a = c.post("/api/jobs", data={"mode": "video"}, files=[("files", ("v.mp4", b"x" * 2000, "video/mp4"))])
    b = c.post("/api/jobs", data={"mode": "video"}, files=[("files", ("v.mp4", b"x" * 2000, "video/mp4"))])
    assert a.status_code == b.status_code == 201 and a.json()["id"] != b.json()["id"]


def test_a_failed_first_upload_leaves_the_id_free_for_the_retry(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2PRINT_MAX_VIDEO_MB", "0.001")
    c = client(tmp_path, monkeypatch)
    assert post(c, data=b"x" * 5000).status_code == 413
    assert not (tmp_path / CID).exists()                 # sin restos: el reintento puede usar el mismo id
    monkeypatch.setenv("SCAN2PRINT_MAX_VIDEO_MB", "10")
    assert post(c).status_code == 201
