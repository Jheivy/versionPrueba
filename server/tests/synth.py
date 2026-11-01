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


def photo3d(sheet, box, dist=300.0, tilt=(2.0, -1.5), size=(1600, 2000)):
    """Foto en perspectiva REAL de una caja (x, y, ancho, largo, alto en mm sobre la hoja) con una cámara de
    móvil (focal equivalente a 26 mm) a `dist` mm sobre el papel: la cara superior sale más grande."""
    from app.views.parallax import DEFAULT_F35, DIAG_35
    w, h = size
    f = DEFAULT_F35 / DIAG_35 * float(np.hypot(w, h))
    K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])
    ax, ay = np.radians(tilt)
    Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    R = Rx @ Ry
    C = np.array([105.0, 148.5, -dist])               # centro de la cámara (z hacia la mesa; la altura es -z)
    t = -R @ C

    def proj(p):
        q = K @ (R @ np.array(p, float) + t)
        return q[:2] / q[2]

    Hm = K @ np.stack([R[:, 0], R[:, 1], t], axis=1)
    img = cv2.warpPerspective(sheet, Hm @ np.diag([1 / S, 1 / S, 1.0]), size, borderValue=200)
    x, y, bw, bl, bh = box
    pts = [proj((x + dx, y + dy, -z)) for dx in (0, bw) for dy in (0, bl) for z in (0, bh)]
    cv2.fillConvexPoly(img, cv2.convexHull(np.float32(pts)).astype(np.int32), 0)
    return img


def scene(sheet, box=(60, 100, 40, 20), color=(0, 0, 0), gradient=0.0, shadow=0.0, noise=0.0, quad=None):
    """Hoja con una pieza rectangular de `color` (BGR) en condiciones reales: `gradient` (0-1) oscurece la hoja de
    izquierda a derecha, `shadow` (0-1) añade la sombra suave que proyecta la pieza (desplazada hacia abajo-derecha)
    y `noise` es la desviación del ruido del sensor. Devuelve la foto en perspectiva (BGR)."""
    h, w = sheet.shape
    img = cv2.cvtColor(sheet, cv2.COLOR_GRAY2BGR).astype(np.float32)
    x, y, bw, bl = (round(v * S) for v in box)
    if shadow:
        sh = np.zeros((h, w), np.float32)
        sh[y + round(3 * S):y + bl + round(3 * S), x + round(3 * S):x + bw + round(3 * S)] = 1
        sh = cv2.GaussianBlur(sh, (0, 0), 4 * S)
        img *= (1 - shadow * sh)[..., None]
    img[y:y + bl, x:x + bw] = color
    if gradient:
        img *= (1 - gradient * np.linspace(0, 1, w, dtype=np.float32))[None, :, None]
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]),
                                    np.float32(quad or [[120, 90], [1500, 160], [1420, 1900], [60, 1750]]))
    out = cv2.warpPerspective(np.clip(img, 0, 255).astype(np.uint8), M, (1600, 2000), borderValue=(200, 200, 200))
    if noise:
        out = np.clip(out + np.random.default_rng(1).normal(0, noise, out.shape), 0, 255).astype(np.uint8)
    return out
