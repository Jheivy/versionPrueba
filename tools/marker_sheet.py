#!/usr/bin/env python3
"""Genera marker_sheet.pdf (A4). Imprímelo al 100 % (sin 'ajustar a página')."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
from PIL import Image  # noqa: E402

from app.views.markers import render_sheet  # noqa: E402

out = Path(sys.argv[1] if len(sys.argv) > 1 else "marker_sheet.pdf")
Image.fromarray(render_sheet(300)).save(out, resolution=300)
print(f"Escrito {out} — comprueba con una regla que cada marcador mide 30 mm.")
