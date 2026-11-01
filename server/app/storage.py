"""Límites de subida y limpieza de trabajos antiguos."""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from fastapi import HTTPException, UploadFile

from . import jobs

MB = 1024 * 1024
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
CHUNK = MB


def _mb(name: str, default: float) -> int:
    try:
        v = float(os.environ.get(name, default))
    except ValueError:
        v = default
    return int(max(v, 0.001) * MB)


def max_photo() -> int:
    return _mb("SCAN2PRINT_MAX_PHOTO_MB", 40)


def max_video() -> int:
    return _mb("SCAN2PRINT_MAX_VIDEO_MB", 1500)


def max_files() -> int:
    return int(os.environ.get("SCAN2PRINT_MAX_FILES", 400))


def max_request() -> int:
    """Tope de una petición completa (rechazo temprano por Content-Length)."""
    return max_video() + 8 * MB


def retention_days() -> float:
    """Días que se conserva un trabajo sin tocar (0 = para siempre)."""
    try:
        return max(float(os.environ.get("SCAN2PRINT_RETENTION_DAYS", 30)), 0)
    except ValueError:
        return 30


def limit_for(filename: str | None) -> int:
    return max_video() if Path(filename or "").suffix.lower() in VIDEO_EXT else max_photo()


async def save_upload(f: UploadFile, dest: Path) -> int:
    """Guarda el fichero en bloques; 413 (y sin restos) si supera el límite de su tipo."""
    limit, total = limit_for(f.filename), 0
    try:
        with dest.open("wb") as out:
            while chunk := await f.read(CHUNK):
                total += len(chunk)
                if total > limit:
                    raise HTTPException(413, f"«{f.filename or 'fichero'}» supera el límite de {limit // MB} MB")
                out.write(chunk)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return total


def _size(d: Path) -> int:
    return sum(p.stat().st_size for p in d.rglob("*") if p.is_file())


def usage(storage: Path) -> dict:
    n = total = 0
    if storage.exists():
        for d in storage.iterdir():
            if (d / "job.json").exists():
                n += 1
                total += _size(d)
    return {"jobs": n, "bytes": total}


def cleanup(storage: Path, days: float, now: float | None = None) -> dict:
    """Borra los trabajos sin tocar desde hace más de `days` días (nunca los que se están procesando)."""
    removed = freed = 0
    if days <= 0 or not storage.exists():
        return {"removed": 0, "freed": 0}
    limit = (now or time.time()) - days * 86400
    for d in storage.iterdir():
        jf = d / "job.json"
        try:
            if not jf.exists() or jf.stat().st_mtime > limit or jobs.is_busy(d):
                continue
            if jobs.read(d).get("status") in ("uploaded", "processing"):
                continue
            size = _size(d)
            shutil.rmtree(d)
            removed, freed = removed + 1, freed + size
        except OSError:
            continue
    return {"removed": removed, "freed": freed}


def check_content_length(value: str | None) -> None:
    try:
        n = int(value or 0)
    except ValueError:
        return
    if n > max_request():
        raise HTTPException(413, f"La subida supera el límite de {max_request() // MB} MB")


def check_count(n: int) -> None:
    if n > max_files():
        raise HTTPException(413, f"Demasiados ficheros (máximo {max_files()})")
