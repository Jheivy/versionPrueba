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
