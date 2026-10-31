import shutil
import subprocess

import pytest

from app.views.scad_writer import build_scad

# Pieza en L: 40x20 de planta, alzado en L de 40 de ancho y 30 de alto
PLANTA = [[(0, 0), (40, 0), (40, 20), (0, 20)]]
ALZADO = [[(0, 0), (40, 0), (40, 10), (10, 10), (10, 30), (0, 30)]]
PERFIL = [[(0, 0), (20, 0), (20, 30), (0, 30)]]


def test_parameters_from_views():
    s = build_scad(PLANTA, ALZADO, PERFIL, holgura=0.2)
    assert "ancho = 40.000;" in s and "fondo = 20.000;" in s and "alto = 30.000;" in s
    assert "holgura = 0.200;" in s
    assert s.count("linear_extrude") == 3


def test_holes_become_paths():
    planta = PLANTA + [[(5, 5), (8, 5), (8, 8), (5, 8)]]
    s = build_scad(planta, altura=5)
    assert "paths=[[0,1,2,3],[4,5,6,7]]" in s


def test_requires_height():
    with pytest.raises(ValueError):
        build_scad(PLANTA)


@pytest.mark.skipif(not shutil.which("openscad"), reason="openscad no instalado")
def test_renders_stl(tmp_path):
    scad = tmp_path / "p.scad"
    scad.write_text(build_scad(PLANTA, ALZADO, PERFIL))
    subprocess.run(["openscad", "-o", str(tmp_path / "p.stl"), str(scad)], check=True)
    assert (tmp_path / "p.stl").stat().st_size > 0
