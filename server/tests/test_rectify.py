import cv2
import numpy as np
import pytest

from app.views.markers import A4_H, A4_W, render_sheet
from app.views.rectify import MarkersNotFound, rectify

PX = 10.0


def photo(sheet, square_mm=(80, 100, 50)):
    """Dibuja un cuadrado negro de 50 mm sobre la hoja y la fotografía en perspectiva."""
    s = 300 / 25.4
    x, y, side = (round(v * s) for v in square_mm)
    sheet = sheet.copy()
    sheet[y:y + side, x:x + side] = 0
    h, w = sheet.shape
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[120, 90], [1500, 160], [1420, 1900], [60, 1750]])
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(sheet, M, (1600, 2000), borderValue=200)


def test_rectify_recovers_scale():
    out = rectify(photo(render_sheet()), PX)
    assert out.shape == (round(A4_H * PX), round(A4_W * PX))
    mask = out < 60
    mask[:int(60 * PX)] = False  # ignora marcadores
    mask[-int(60 * PX):] = False
    ys, xs = np.nonzero(mask)
    w, h = (xs.max() - xs.min() + 1) / PX, (ys.max() - ys.min() + 1) / PX
    assert w == pytest.approx(50, abs=0.5) and h == pytest.approx(50, abs=0.5)


def test_fails_without_markers():
    with pytest.raises(MarkersNotFound):
        rectify(np.full((500, 500), 255, np.uint8))
