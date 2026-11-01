"""Extrae fotogramas nítidos de un vídeo (uno por intervalo, el menos borroso)."""
from __future__ import annotations

from pathlib import Path

import cv2


def _sharpness(frame) -> float:
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, (480, round(480 * g.shape[0] / g.shape[1])))
    return cv2.Laplacian(g, cv2.CV_64F).var()


def extract_frames(video: Path, out_dir: Path, step_s: float = 0.4, max_frames: int = 120) -> int:
    """Guarda en `out_dir` el fotograma más nítido de cada ventana de `step_s` segundos
    (ventana ampliada si saldrían más de `max_frames`). Devuelve cuántos guardó."""
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError(f"no se pudo abrir el vídeo {video.name}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    if total > 0:
        step_s = max(step_s, total / fps / max_frames)
    best: dict[int, tuple[float, object]] = {}
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        b = int(i / fps / step_s)
        s = _sharpness(frame)
        if b not in best or s > best[b][0]:
            best[b] = (s, frame)
        i += 1
    cap.release()
    out_dir.mkdir(parents=True, exist_ok=True)
    for n, b in enumerate(sorted(best)):
        cv2.imwrite(str(out_dir / f"frame_{n:04d}.jpg"), best[b][1], [cv2.IMWRITE_JPEG_QUALITY, 95])
    if len(best) < 10:
        raise ValueError(f"solo {len(best)} fotogramas útiles; graba un vídeo más largo (≥ 20 s) girando alrededor")
    return len(best)


def sheet_visible(frames_dir: Path, sample: int = 15, min_share: float = 0.4) -> bool:
    """¿Sale la hoja de marcadores en el vídeo? (≥ 2 marcadores en el `min_share` de los fotogramas muestreados)."""
    from ..views.markers import DICT, marker_corners_mm
    files = sorted(frames_dir.glob("*.jp*g")) + sorted(frames_dir.glob("*.png"))
    if not files:
        return False
    picked = files[:: max(1, len(files) // sample)][:sample]
    det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(DICT), cv2.aruco.DetectorParameters())
    known, hits = marker_corners_mm(), 0
    for f in picked:
        img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        scale = 1280 / max(img.shape)
        if scale < 1:
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        _, ids, _ = det.detectMarkers(img)
        hits += len({int(i) for i in (ids.flatten() if ids is not None else [])} & known.keys()) >= 2
    return hits / len(picked) >= min_share
