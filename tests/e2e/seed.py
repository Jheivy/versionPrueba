"""Crea trabajos de ejemplo en un servidor en marcha: uno listo, uno en revisión y uno con error.
Uso: PYTHONPATH=server:server/tests python tests/e2e/seed.py http://127.0.0.1:PORT  → imprime los ids en JSON."""
import json
import sys
import time

import cv2
import httpx
import numpy as np
from synth import photo3d

from app.views.markers import render_sheet

SHEET = render_sheet()
A, F, H = 40.0, 20.0, 30.0
BOXES = {"planta": (85, 138.5, A, F, H), "alzado": (85, 134, A, H, F), "perfil": (95, 134, F, H, A)}


def jpg(img):
    return cv2.imencode(".jpg", img)[1].tobytes()


def upload(c, name, images, review=False):
    files = [("files", (f"{v}.jpg", jpg(img), "image/jpeg")) for v, img in images.items()]
    data = {"mode": "views", "views": ",".join(images), "name": name, "review": "1" if review else ""}
    r = c.post("/api/jobs", data=data, files=files)
    r.raise_for_status()
    return r.json()["id"]


def wait(c, job_id, status):
    for _ in range(120):
        j = c.get(f"/api/jobs/{job_id}").json()
        if j["status"] == status:
            return j
        time.sleep(0.5)
    raise SystemExit(f"{job_id} no llegó a {status}: {j}")


def main(base):
    with httpx.Client(base_url=base, timeout=60) as c:
        photos = {v: photo3d(SHEET, b, 300.0) for v, b in BOXES.items()}
        done = upload(c, "Caja de prueba", photos)
        review = upload(c, "Caja en revisión", photos, review=True)
        review2 = upload(c, "Caja para continuar", photos, review=True)
        blank = {"planta": np.full((600, 800, 3), 128, np.uint8)}
        error = upload(c, "Foto sin hoja", blank)
        wait(c, done, "done"), wait(c, review, "review"), wait(c, review2, "review"), wait(c, error, "error")
    print(json.dumps({"done": done, "review": review, "continue": review2, "error": error}))


if __name__ == "__main__":
    main(sys.argv[1])
