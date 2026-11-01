import os
import time

import cv2
import numpy as np
import trimesh
from fastapi.testclient import TestClient

from app import jobs, main
from app.views.render import render_model


def make_box(path, size=(40, 20, 30)):
    box = trimesh.creation.box(size)
    box.apply_translation([0, 0, size[2] / 2])
    box.export(path)
    return path


def decode(png):
    return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)


def test_render_is_a_transparent_isometric_png(tmp_path):
    img = decode(render_model(make_box(tmp_path / "p.stl")))
    assert img.shape == (192, 192, 4)
    assert img[0, 0, 3] == 0 and img[-1, -1, 3] == 0            # fondo transparente: vale en claro y oscuro
    assert img[96, 96, 3] == 255                                 # la pieza, en el centro
    b, g, r = (int(v) for v in img[96, 96, :3])
    assert r > g > b and r > 60                                  # tono naranja filamento (sombreado según la cara)


def test_light_comes_from_above(tmp_path):
    """La cara superior debe ser la más clara de las tres que se ven."""
    img = decode(render_model(make_box(tmp_path / "p.stl"), size=256))
    ys, xs = np.nonzero(img[:, :, 3] == 255)
    top = img[ys.min() + 25, (xs.min() + xs.max()) // 2, :3].mean()      # justo bajo la arista superior
    bottom = img[ys.max() - 25, (xs.min() + xs.max()) // 2, :3].mean()   # cerca de la base: cara lateral
    assert top > bottom * 1.2


def test_render_is_fast_enough_for_a_list(tmp_path):
    p = make_box(tmp_path / "p.stl")
    t = time.perf_counter()
    render_model(p)
    assert time.perf_counter() - t < 1.0


def test_thumb_png_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORAGE", tmp_path)
    d = tmp_path / ("a" * 32)
    (d / "output").mkdir(parents=True)
    jobs.write(d, {"id": d.name, "mode": "views", "status": "done", "created": "x", "inputs": [], "outputs": []})
    c = TestClient(main.app)
    url = f"/api/jobs/{d.name}/thumb.png"
    assert c.get(url).status_code == 404                          # sin modelo: la app usa la foto

    stl = make_box(d / "output" / "pieza.stl")
    r = c.get(url)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content.startswith(b"\x89PNG")
    assert r.headers["cache-control"] == "no-cache"
    assert c.get(url + "?v=7").headers["cache-control"] == "public, max-age=31536000, immutable"

    first = (d / "thumb-model.png").read_bytes()
    time.sleep(0.02)
    make_box(stl, size=(20, 40, 10))                         # se regenera la pieza...
    os.utime(stl, (time.time() + 5, time.time() + 5))
    c.get(url)
    assert (d / "thumb-model.png").read_bytes() != first          # ...y la miniatura cacheada se rehace
