import cv2
import numpy as np
import pytest
import trimesh
from fastapi.testclient import TestClient

from app import main, pipeline, pipeline_video
from app.photogrammetry.mesh import postprocess
from app.photogrammetry.scale import sheet_alignment
from app.views.markers import A4_H, A4_W, render_sheet

UNIT_MM = 12.5            # «unidad» arbitraria de la malla reconstruida: 1 unidad = 12,5 mm
BOX = (40.0, 20.0, 30.0)  # la pieza sobre la hoja (mm)


def rotation(seed=3):
    q = np.random.default_rng(seed).normal(size=4)
    return trimesh.transformations.quaternion_matrix(q / np.linalg.norm(q))[:3, :3]


def make_scene(path, side=1, noise_mm=0.3, blank=False, shear=0.0, seed=3):
    """OBJ real (v / vt / f + .mtl + .png) con la hoja A4 como suelo texturizado y una caja encima, girado y movido
    a una posición cualquiera y en unidades arbitrarias. `side` = hacia qué lado de la hoja sale la pieza."""
    rng = np.random.default_rng(seed)
    n = 6                                                       # la hoja son n x n celdas (como una malla real)
    xs, ys = np.linspace(0, A4_W, n + 1), np.linspace(0, A4_H, n + 1)
    pts, uvs, faces = [], [], []
    for y in ys:
        for x in xs:
            pts.append((x + shear * y, y, rng.normal(0, noise_mm)))
            uvs.append((x / A4_W, 1 - y / A4_H))                # OBJ: v = 0 es el borde de ABAJO de la imagen
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            faces += [(a, a + 1, a + n + 2), (a, a + n + 2, a + n + 1)]
    box = trimesh.creation.box(BOX)
    box.apply_translation([A4_W / 2, A4_H / 2, side * BOX[2] / 2 * -1])   # sobre la hoja (z del plano = bajo la mesa)
    base = len(pts)
    pts += [tuple(v) for v in box.vertices]
    uvs += [(0.5, 0.5)] * len(box.vertices)                     # sin textura propia (degenerados en el atlas)
    faces += [tuple(base + np.array(f)) for f in box.faces]
    r = rotation(seed)
    world = (np.array(pts) * side) @ r.T / UNIT_MM + np.array([3.0, -2.0, 7.5])
    cv2.imwrite(str(path.with_suffix(".png")), np.full_like(render_sheet(), 255) if blank else render_sheet())
    path.with_suffix(".mtl").write_text(f"newmtl hoja\nmap_Kd {path.with_suffix('.png').name}\n")
    with path.open("w") as f:
        f.write(f"mtllib {path.with_suffix('.mtl').name}\nusemtl hoja\n")
        f.writelines(f"v {x:.6f} {y:.6f} {z:.6f}\n" for x, y, z in world)
        f.writelines(f"vt {u:.6f} {v:.6f}\n" for u, v in uvs)
        f.writelines(f"f {a + 1}/{a + 1} {b + 1}/{b + 1} {c + 1}/{c + 1}\n" for a, b, c in faces)
    return r


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_scale_from_the_sheet_in_the_texture(tmp_path, seed):
    make_scene(tmp_path / "m.obj", seed=seed)
    found = sheet_alignment(tmp_path / "m.obj")
    assert found["mm_per_unit"] == pytest.approx(UNIT_MM, rel=0.01)
    assert found["markers"] == 4 and found["rms_mm"] < 1.0


def test_normal_points_to_the_side_where_the_part_is(tmp_path):
    make_scene(tmp_path / "m.obj")
    found = sheet_alignment(tmp_path / "m.obj")
    mesh = trimesh.load(tmp_path / "m.obj", force="mesh", process=False)
    assert float(((np.asarray(mesh.vertices) - found["origin"]) @ found["normal"]).mean()) > 0


def test_no_markers_in_the_texture_means_no_scale(tmp_path):
    make_scene(tmp_path / "m.obj", blank=True)
    assert sheet_alignment(tmp_path / "m.obj") is None


def test_untextured_mesh_means_no_scale(tmp_path):
    trimesh.creation.box([1, 1, 1]).export(tmp_path / "m.obj")
    assert sheet_alignment(tmp_path / "m.obj") is None


def test_a_warped_sheet_is_rejected(tmp_path):
    make_scene(tmp_path / "m.obj", shear=0.5)                   # la hoja salió torcida: el ajuste no es de fiar
    assert sheet_alignment(tmp_path / "m.obj") is None


def test_postprocess_cuts_the_paper_and_sets_the_real_size(tmp_path):
    make_scene(tmp_path / "m.obj")
    found = sheet_alignment(tmp_path / "m.obj")
    info = postprocess(tmp_path / "m.obj", tmp_path / "o.stl", sheet=found)
    m = trimesh.load(tmp_path / "o.stl")
    assert m.extents == pytest.approx(BOX, abs=1.5)            # sin los 210 x 297 mm del papel, alineada con X/Y
    assert m.bounds[0][2] == pytest.approx(0, abs=1e-6)
    assert info["scale_source"] == "marcadores" and not info["scale_estimated"]


def test_stands_on_the_sheet_whatever_the_orientation(tmp_path):
    make_scene(tmp_path / "m.obj")
    found = sheet_alignment(tmp_path / "m.obj")
    postprocess(tmp_path / "m.obj", tmp_path / "o.stl", sheet=found)
    ex = trimesh.load(tmp_path / "o.stl").extents
    assert ex[2] == pytest.approx(BOX[2], abs=1.5)               # el alto es el de la caja: Z = perpendicular a la hoja


def test_calibre_overrides_the_sheet(tmp_path):
    make_scene(tmp_path / "m.obj")
    found = sheet_alignment(tmp_path / "m.obj")
    info = postprocess(tmp_path / "m.obj", tmp_path / "o.stl", largo_mm=80, sheet=found)
    assert trimesh.load(tmp_path / "o.stl").extents.max() == pytest.approx(80, abs=0.2)
    assert info["scale_source"] == "calibre"


def test_video_job_uses_the_sheet_without_any_measure(tmp_path, monkeypatch):
    from test_video import make_video
    monkeypatch.setattr(main, "STORAGE", tmp_path / "jobs")
    monkeypatch.setattr(pipeline, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(pipeline, "_notify", lambda p: None)

    def fake_capture(frames, out, detail="medium", keep_background=False):
        out.mkdir()
        make_scene(out / "model.obj")
        return out / "model.obj"
    monkeypatch.setattr(pipeline_video, "run_object_capture", fake_capture)
    make_video(tmp_path / "v.mp4")
    c = TestClient(main.app)
    jid = c.post("/api/jobs", data={"mode": "video"},
                 files=[("files", ("v.mp4", (tmp_path / "v.mp4").read_bytes(), "video/mp4"))]).json()["id"]
    job = c.get(f"/api/jobs/{jid}").json()
    assert job["status"] == "done", job
    assert job["mesh"]["scale_source"] == "marcadores" and not job["mesh"]["scale_estimated"]
    assert job["mesh"]["sheet"]["markers"] == 4
    assert [job["dims"][k] for k in ("ancho", "fondo", "alto")] == pytest.approx(BOX, abs=1.5)


def test_sheet_visible_in_the_frames(tmp_path):
    from synth import photo

    from app.photogrammetry.frames import sheet_visible
    with_sheet, without = tmp_path / "a", tmp_path / "b"
    with_sheet.mkdir(), without.mkdir()
    for i in range(12):
        cv2.imwrite(str(with_sheet / f"frame_{i:04d}.jpg"), photo(render_sheet(), [("rect", 0, (60, 100, 40, 20))]))
        noise = np.random.default_rng(i).integers(0, 255, (600, 800, 3), np.uint8)
        cv2.imwrite(str(without / f"frame_{i:04d}.jpg"), noise)
    assert sheet_visible(with_sheet) and not sheet_visible(without)
    assert not sheet_visible(tmp_path / "vacia")


def test_background_is_kept_only_when_the_video_shows_the_sheet(tmp_path, monkeypatch):
    from synth import photo
    from test_video import make_video
    monkeypatch.setattr(main, "STORAGE", tmp_path / "jobs")
    monkeypatch.setattr(pipeline, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(pipeline, "_notify", lambda p: None)
    flags = []

    def fake_capture(frames, out, detail="medium", keep_background=False):
        flags.append(keep_background)
        out.mkdir()
        make_scene(out / "model.obj")
        return out / "model.obj"
    monkeypatch.setattr(pipeline_video, "run_object_capture", fake_capture)

    w = cv2.VideoWriter(str(tmp_path / "hoja.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 30, (800, 1000))
    gray = photo(render_sheet(), [("rect", 0, (60, 100, 40, 20))])
    shot = cv2.resize(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), (800, 1000))
    for i in range(150):
        w.write(np.roll(shot, i % 7, axis=1) if i % 3 else cv2.GaussianBlur(shot, (0, 0), 3))
    w.release()
    make_video(tmp_path / "nada.mp4")
    c = TestClient(main.app)
    for name in ("hoja.mp4", "nada.mp4"):
        files = [("files", (name, (tmp_path / name).read_bytes(), "video/mp4"))]
        jid = c.post("/api/jobs", data={"mode": "video"}, files=files).json()["id"]
        assert c.get(f"/api/jobs/{jid}").json()["status"] == "done"
    assert flags == [True, False]
