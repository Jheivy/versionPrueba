import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from synth import photo

from app import main, pipeline
from app.views.markers import render_sheet

SHEET = render_sheet()


def enc(img):
    return cv2.imencode(".jpg", img)[1].tobytes()


def L_files():
    shots = {
        "planta": [("rect", 0, (60, 100, 40, 20)), ("circle", 255, (70, 110, 4))],
        "alzado": [("poly", 0, [(60, 130), (100, 130), (100, 120), (70, 120), (70, 100), (60, 100)])],
        "perfil": [("rect", 0, (60, 100, 20, 30))],
    }
    return shots, [("files", (f"{n}.jpg", enc(photo(SHEET, s)), "image/jpeg")) for n, s in shots.items()]


@pytest.fixture
def c(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORAGE", tmp_path / "jobs")
    monkeypatch.setattr(pipeline, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(pipeline, "_notify", lambda p: None)
    return TestClient(main.app)


def test_detect_sheet_and_blank(c):
    r = c.post("/api/detect", files={"file": ("f.jpg", enc(photo(SHEET, [])), "image/jpeg")}).json()
    assert r["markers"] == 4 and r["ok"] is True and r["checks"] == {"hoja": True, "nitidez": True, "luz": True} and r["hint"] == "Listo para disparar"
    blank = c.post("/api/detect", files={"file": ("f.jpg", enc(np.full((600, 800, 3), 128, np.uint8)), "image/jpeg")}).json()
    assert blank["markers"] == 0 and not blank["ok"] and "hoja" in blank["hint"]
    assert c.post("/api/detect", files={"file": ("f.jpg", b"xx", "image/jpeg")}).status_code == 400


def test_health_and_sheet_pdf(c):
    h = c.get("/api/health").json()
    assert h["version"] and isinstance(h["openscad"], bool)
    r = c.get("/api/marker-sheet.pdf")
    assert r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF")


def test_review_flow(c):
    _, files = L_files()
    job = c.post("/api/jobs", data={"mode": "views", "views": "planta,alzado,perfil", "review": "1"}, files=files).json()
    jid = job["id"]
    j = c.get(f"/api/jobs/{jid}").json()
    assert j["status"] == "review" and j["step"] == "review" and j["outputs"] == []
    p = c.get(f"/api/jobs/{jid}/preview/planta.png")
    assert p.status_code == 200 and p.content.startswith(b"\x89PNG")
    import json
    info = json.loads(p.headers["X-Preview-Info"])
    assert info["huecos"] == 1 and info["ancho"] == pytest.approx(40, abs=0.7)
    assert c.post(f"/api/jobs/{jid}/confirm").status_code == 200
    j = c.get(f"/api/jobs/{jid}").json()
    assert j["status"] == "done" and j["step"] is None and "pieza.stl" in j["outputs"]
    assert c.post(f"/api/jobs/{jid}/confirm").status_code == 409  # ya no espera revisión


def test_friendly_error_and_replace_view(c):
    shots, files = L_files()
    files[0] = ("files", ("planta.jpg", enc(np.full((600, 800, 3), 200, np.uint8)), "image/jpeg"))  # sin hoja
    jid = c.post("/api/jobs", data={"mode": "views", "views": "planta,alzado,perfil"}, files=files).json()["id"]
    j = c.get(f"/api/jobs/{jid}").json()
    assert j["status"] == "error" and j["error_view"] == "planta" and "hoja de marcadores" in j["error"]
    good = ("file", ("planta.jpg", enc(photo(SHEET, shots["planta"])), "image/jpeg"))
    assert c.post(f"/api/jobs/{jid}/inputs", data={"view": "planta"}, files=[good]).status_code == 200
    j = c.get(f"/api/jobs/{jid}").json()
    assert j["status"] == "review" and j["error"] is None and len(j["inputs"]) == 3  # vuelve a revisión
    c.post(f"/api/jobs/{jid}/confirm")
    assert c.get(f"/api/jobs/{jid}").json()["status"] == "done"


def test_rename_thumb_delete(c):
    _, files = L_files()
    jid = c.post("/api/jobs", data={"mode": "views", "views": "planta,alzado,perfil", "name": "Tapa"}, files=files).json()["id"]
    assert c.get(f"/api/jobs/{jid}").json()["name"] == "Tapa"  # no lo pisa el nombre del último fichero
    assert c.patch(f"/api/jobs/{jid}", json={"name": "Tapa batería"}).json()["name"] == "Tapa batería"
    assert c.get(f"/api/jobs/{jid}/thumb.jpg").content[:2] == b"\xff\xd8"
    assert c.delete(f"/api/jobs/{jid}").status_code == 204
    assert c.get(f"/api/jobs/{jid}").status_code == 404
