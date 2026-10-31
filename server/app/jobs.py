"""Estado de los trabajos: escritura atómica, un lock por trabajo y control de concurrencia."""
from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path

_guard = threading.Lock()
_locks: dict[str, threading.RLock] = {}
_busy: set[str] = set()                 # trabajos en cola o procesándose en este proceso
_worker = threading.Lock()              # un solo procesado pesado a la vez (OpenSCAD / Object Capture)

STALE_MSG = "El servidor se reinició mientras se procesaba este trabajo. Pulsa «Reintentar»."


def _lock(d: Path) -> threading.RLock:
    with _guard:
        return _locks.setdefault(str(d), threading.RLock())


def read(d: Path) -> dict:
    return json.loads((d / "job.json").read_text())


def write(d: Path, job: dict) -> None:
    """Escribe job.json de forma atómica (fichero temporal + rename)."""
    tmp = d / f"job.json.{os.getpid()}.{threading.get_ident()}.tmp"
    tmp.write_text(json.dumps(job, indent=2))
    os.replace(tmp, d / "job.json")


def update(d: Path, **kw) -> dict:
    with _lock(d):
        job = read(d)
        job.update(kw)
        write(d, job)
        return job


def reserve(d: Path) -> bool:
    """Marca el trabajo como ocupado. False si ya hay un procesado en curso o en cola."""
    with _guard:
        if str(d) in _busy:
            return False
        _busy.add(str(d))
        return True


def release(d: Path) -> None:
    with _guard:
        _busy.discard(str(d))


def is_busy(d: Path) -> bool:
    with _guard:
        return str(d) in _busy


@contextmanager
def running(d: Path):
    """Envuelve un procesado: espera turno en el worker único y libera la reserva al acabar."""
    try:
        with _worker:
            yield
    finally:
        release(d)


def recover_stale(storage: Path) -> int:
    """Al arrancar: los trabajos que quedaron a medias pasan a error para poder reintentarlos."""
    n = 0
    if not storage.exists():
        return 0
    for d in storage.iterdir():
        try:
            job = read(d)
        except (OSError, ValueError):
            continue
        if job.get("status") in ("uploaded", "processing"):
            update(d, status="error", step=None, error=STALE_MSG, error_view=None)
            n += 1
        for tmp in d.glob("job.json.*.tmp"):
            tmp.unlink(missing_ok=True)
    return n
