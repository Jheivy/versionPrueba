import cv2
import numpy as np

S = 300 / 25.4


def photo(sheet, shapes, quad=((120, 90), (1500, 160), (1420, 1900), (60, 1750))):
    """shapes: ('rect'|'circle'|'poly', color, args en mm). Devuelve la hoja fotografiada en perspectiva."""
    sheet = sheet.copy()
    for kind, color, a in shapes:
        if kind == "rect":
            x, y, w, h = (round(v * S) for v in a)
            sheet[y:y + h, x:x + w] = color
        elif kind == "circle":
            cv2.circle(sheet, (round(a[0] * S), round(a[1] * S)), round(a[2] * S), color, -1)
        else:
            cv2.fillPoly(sheet, [np.round(np.array(a) * S).astype(np.int32)], color)
    h, w = sheet.shape
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(quad))
    return cv2.warpPerspective(sheet, M, (1600, 2000), borderValue=200)
