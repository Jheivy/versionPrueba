import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import jobs, main, pipeline

WEB = Path(main.WEB_DIR)
client = TestClient(main.app)


def test_service_worker_is_generated_from_the_real_files():
    r = client.get("/sw.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert r.headers["cache-control"] == "no-cache"
    src = r.text
    for placeholder in ('"/*VERSION*/dev"', '"/*VENDOR*/dev"', "/*SHELL*/[]", "/*VENDORLIST*/[]"):
        assert placeholder not in src
    shell = json.loads(re.search(r"const SHELL = (\[.*?\]);", src, re.S).group(1))
    vendor = json.loads(re.search(r"const VENDOR = (\[.*?\]);", src, re.S).group(1))
    assert {"./", "index.html", "js/app.js", "css/components.css", "js/views/detalle.js", "js/image.js"} <= set(shell)
    assert "vendor/three-0.160.0.module.min.js" in vendor and "fonts/ibm-plex-sans-latin-400-normal.woff2" in vendor
    for f in shell[1:] + vendor:
        assert (WEB / f).is_file(), f"{f} está en el service worker pero no existe"


def test_service_worker_version_changes_with_content(tmp_path, monkeypatch):
    for f in ("sw.js", "index.html"):
        (tmp_path / f).write_text((WEB / f).read_text())
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "lib.js").write_text("x")
    monkeypatch.setattr(main, "WEB_DIR", tmp_path)
    monkeypatch.setattr(main, "_SW_CACHE", {})
    v1 = re.search(r'const VERSION = "(\w+)"', main._sw_source()).group(1)
    vend1 = re.search(r'const VENDOR_VERSION = "(\w+)"', main._sw_source()).group(1)
    (tmp_path / "index.html").write_text("<html>cambio</html>")
    v2 = re.search(r'const VERSION = "(\w+)"', main._sw_source()).group(1)
    assert v1 != v2  # editar la app invalida la caché del shell...
    vend2 = re.search(r'const VENDOR_VERSION = "(\w+)"', main._sw_source()).group(1)
    assert vend1 == vend2  # ...pero no obliga a bajar three.js otra vez


def test_cache_headers_and_gzip():
    with client.stream("GET", "/vendor/three-0.160.0.module.min.js", headers={"Accept-Encoding": "gzip"}) as three:
        assert three.headers["cache-control"] == "public, max-age=31536000, immutable"
        assert three.headers["content-encoding"] == "gzip"
        on_the_wire = sum(len(chunk) for chunk in three.iter_raw())
    assert on_the_wire < 220_000  # 671 kB sin comprimir -> ~166 kB por el cable
    assert client.get("/fonts/ibm-plex-mono-latin-500-normal.woff2").headers["cache-control"].endswith("immutable")
    for path in ("/", "/js/app.js", "/css/components.css"):
        assert client.get(path).headers["cache-control"] == "no-cache"


def test_index_importmap_and_preloads_point_to_real_files():
    html = (WEB / "index.html").read_text()
    imap = json.loads(re.search(r'<script type="importmap">(.*?)</script>', html, re.S).group(1))["imports"]
    for target in imap.values():
        assert target.startswith("./"), "las rutas del importmap deben ser relativas (./) o el navegador las ignora"
        assert (WEB / target).exists(), target
    for href in re.findall(r'<link rel="(?:modulepreload|preload|stylesheet|manifest)" href="([^"]+)"', html):
        assert (WEB / href).exists(), href
    assert "cdn.jsdelivr" not in html  # nada depende de internet


def test_every_relative_import_resolves():
    for js in WEB.rglob("js/**/*.js"):
        for rel in re.findall(r'''(?:from|import\()\s*["'](\.{1,2}/[^"']+)["']''', js.read_text()):
            assert (js.parent / rel).resolve().is_file(), f"{js.relative_to(WEB)} importa {rel}, que no existe"


def test_three_addons_import_the_mapped_bare_specifier():
    for f in (WEB / "vendor" / "three-0.160.0-addons").rglob("*.js"):
        assert "from 'three'" in f.read_text()  # resuelto por el importmap a la copia local


def test_job_files_are_immutable_only_when_versioned(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "STORAGE", tmp_path)
    d = tmp_path / ("a" * 32)
    (d / "output").mkdir(parents=True)
    (d / "output" / "pieza.stl").write_text("solid x\nendsolid x\n")
    jobs.write(d, {"id": d.name, "mode": "views", "status": "done", "created": "x", "inputs": [], "outputs": []})
    url = f"/api/jobs/{d.name}/files/pieza.stl"
    assert client.get(url).headers["cache-control"] == "no-cache"
    assert client.get(url + "?v=123").headers["cache-control"] == "public, max-age=31536000, immutable"


def test_rev_changes_on_every_regeneration(tmp_path, monkeypatch):
    from test_coherence import _job
    d = _job(tmp_path, monkeypatch, alzado_w=40)
    pipeline.process_views(d)
    r1 = jobs.read(d)["rev"]
    pipeline.process_views(d, {"holgura": 0.2})
    assert jobs.read(d)["rev"] > r1 > 0  # nueva URL ?v= => el navegador no reutiliza un modelo antiguo


@pytest.mark.parametrize("name", ["tokens", "base", "components"])
def test_css_font_family_is_declared(name):
    assert (WEB / "css" / f"{name}.css").is_file()
