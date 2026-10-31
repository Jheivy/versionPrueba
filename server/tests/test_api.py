from fastapi.testclient import TestClient


def client(tmp_path, monkeypatch):
    from app import main
    monkeypatch.setattr(main, "STORAGE", tmp_path)
    return TestClient(main.app)


def test_upload_views_job(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    files = [("files", (f"{v}.jpg", b"img", "image/jpeg")) for v in ("a", "b", "c")]
    r = c.post("/api/jobs", data={"mode": "views", "views": "planta,alzado,perfil"}, files=files)
    assert r.status_code == 201
    job = r.json()
    assert job["inputs"] == ["planta_a.jpg", "alzado_b.jpg", "perfil_c.jpg"]
    assert c.get(f"/api/jobs/{job['id']}").json()["status"] == "uploaded"
    assert [j["id"] for j in c.get("/api/jobs").json()] == [job["id"]]
    assert c.get(f"/api/jobs/{job['id']}/files/planta_a.jpg").content == b"img"


def test_rejects_bad_input(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    f = [("files", ("x.jpg", b"img", "image/jpeg"))]
    assert c.post("/api/jobs", data={"mode": "nope"}, files=f).status_code == 400
    assert c.post("/api/jobs", data={"mode": "views", "views": "techo"}, files=f).status_code == 400
    assert c.get("/api/jobs/../../etc").status_code == 404
