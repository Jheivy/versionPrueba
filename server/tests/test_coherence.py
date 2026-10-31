import cv2
import pytest
import trimesh
from fastapi.testclient import TestClient
from synth import photo

from app import jobs, main, pipeline
from app.views import coherence
from app.views.markers import render_sheet

SHEET = render_sheet()


def rect(w, h):
    return [[(0, 0), (w, 0), (w, h), (0, h)]]


def test_consistent_views_give_no_warning():
    s = coherence.sizes({"planta": rect(40, 20), "alzado": rect(40.3, 30), "perfil": rect(19.8, 29.7)})
    assert coherence.check(s) == []  # diferencias dentro del error de la foto


def test_mismatch_is_reported_per_dimension():
    s = coherence.sizes({"planta": rect(40, 20), "alzado": rect(43, 30), "perfil": rect(20, 27)})
    ws = {w["dim"]: w for w in coherence.check(s)}
    assert set(ws) == {"ancho", "alto"}
    assert ws["ancho"]["views"] == ["planta", "alzado"] and ws["ancho"]["values"] == [40.0, 43.0]
    assert ws["alto"]["views"] == ["alzado", "perfil"] and ws["alto"]["diff"] == 3.0


def test_tolerance_grows_with_size():
    big = coherence.sizes({"planta": rect(200, 100), "alzado": rect(203, 50)})
    assert coherence.check(big) == []  # 3 mm en 200 mm (1,5 %): dentro del 2 %
    assert coherence.check(coherence.sizes({"planta": rect(200, 100), "alzado": rect(205, 50)}))


def test_missing_views_are_not_compared():
    assert coherence.check(coherence.sizes({"planta": rect(40, 20)})) == []
    assert coherence.check(coherence.sizes({"planta": rect(40, 20), "alzado": rect(50, 30)}))[0]["dim"] == "ancho"


def test_targets_prefer_caliper_then_average():
    s = coherence.sizes({"planta": rect(40, 20), "alzado": rect(43, 30), "perfil": rect(20, 30)})
    assert coherence.targets(s, {}) == {}                                   # sin pedir nada, no se toca
    assert coherence.targets(s, {}, unify=True) == {"ancho": 41.5}          # solo lo que no cuadra
    assert coherence.targets(s, {"ancho": 40.5}, unify=True) == {"ancho": 40.5}  # el calibre manda
    assert coherence.targets(s, {"alto": 31}) == {"alto": 31}


def _job(tmp_path, monkeypatch, alzado_w=43):
    monkeypatch.setattr(main, "STORAGE", tmp_path / "jobs")
    monkeypatch.setattr(pipeline, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(pipeline, "_notify", lambda p: None)
    d = tmp_path / "jobs" / ("e" * 32)
    (d / "input").mkdir(parents=True)
    shots = {"planta": [("rect", 0, (60, 100, 40, 20))],
             "alzado": [("rect", 0, (60, 100, alzado_w, 30))],
             "perfil": [("rect", 0, (60, 100, 20, 30))]}
    for n, s in shots.items():
        cv2.imwrite(str(d / "input" / f"{n}_x.jpg"), photo(SHEET, s))
    jobs.write(d, {"id": d.name, "mode": "views", "status": "uploaded", "created": "x", "inputs": [], "outputs": []})
    return d


def extents(d):
    return trimesh.load(d / "output" / "pieza.stl").extents


def test_review_and_result_report_the_mismatch(tmp_path, monkeypatch):
    d = _job(tmp_path, monkeypatch)
    pipeline.process_views(d, pause_for_review=True)
    job = jobs.read(d)
    assert job["status"] == "review"
    (w,) = job["warnings"]
    assert w["dim"] == "ancho" and w["views"] == ["planta", "alzado"] and w["diff"] == pytest.approx(3.0, abs=0.4)

    pipeline.process_views(d)  # el usuario continúa sin corregir
    job = jobs.read(d)
    assert job["status"] == "done" and [x["dim"] for x in job["warnings"]] == ["ancho"]
    assert extents(d)[0] == pytest.approx(40, abs=0.5)  # el sólido se recorta al menor
    dims = job["dims"]  # y las medidas mostradas son las del sólido real, no las de una vista cualquiera
    assert [dims["ancho"], dims["fondo"], dims["alto"]] == pytest.approx(list(extents(d)), abs=0.6)


def test_unify_averages_and_clears_warning(tmp_path, monkeypatch):
    d = _job(tmp_path, monkeypatch)
    pipeline.process_views(d, {"unificar": 1})
    job = jobs.read(d)
    assert job["warnings"] == [] and job["dims"]["ancho"] == pytest.approx(41.5, abs=0.4)
    assert extents(d)[0] == pytest.approx(41.5, abs=0.5)  # las dos vistas se estiran al promedio


def test_caliper_value_stretches_each_view_to_it(tmp_path, monkeypatch):
    d = _job(tmp_path, monkeypatch)
    pipeline.process_views(d, {"ancho": 40.0})
    job = jobs.read(d)
    assert job["warnings"] == [] and job["dims"]["ancho"] == 40.0
    assert extents(d)[0] == pytest.approx(40, abs=0.4)
    pipeline.process_views(d, {"ancho": 45.0})  # antes el alzado no se estiraba a su propia medida
    assert extents(d)[0] == pytest.approx(45, abs=0.5)


def test_api_exposes_warnings(tmp_path, monkeypatch):
    d = _job(tmp_path, monkeypatch)
    pipeline.process_views(d, pause_for_review=True)
    c = TestClient(main.app)
    assert c.get(f"/api/jobs/{d.name}").json()["warnings"][0]["dim"] == "ancho"
    assert c.post(f"/api/jobs/{d.name}/params", json={"unificar": 1}).status_code == 200
    j = c.get(f"/api/jobs/{d.name}").json()
    assert j["status"] == "done" and j["warnings"] == [] and j["params"] == {"unificar": 1.0}


def test_narrow_view_is_stretched_to_the_caliper_value(tmp_path, monkeypatch):
    """Regresión: antes el factor se calculaba sobre la planta y se aplicaba igual al alzado, así que un
    alzado más estrecho seguía recortando la pieza por debajo de la cota medida."""
    d = _job(tmp_path, monkeypatch, alzado_w=37)
    pipeline.process_views(d, {"ancho": 40.0})
    assert jobs.read(d)["warnings"] == []
    assert extents(d)[0] == pytest.approx(40, abs=0.5)  # con el código anterior salía ~37


def test_displayed_dims_match_the_real_solid_when_height_disagrees(tmp_path, monkeypatch):
    d = _job(tmp_path, monkeypatch, alzado_w=40)
    cv2.imwrite(str(d / "input" / "perfil_x.jpg"), photo(SHEET, [("rect", 0, (60, 100, 20, 27))]))  # perfil más bajo
    pipeline.process_views(d)
    job = jobs.read(d)
    assert [w["dim"] for w in job["warnings"]] == ["alto"]
    assert job["dims"]["alto"] == pytest.approx(27, abs=0.4) == pytest.approx(extents(d)[2], abs=0.5)
