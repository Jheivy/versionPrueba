# Scan2Print

Fotografía una pieza (o su alzado/planta/perfil) con el móvil Android, envíala al Mac mini y obtén un `.scad` paramétrico + `.stl` listo para imprimir.

Diseño completo y hoja de ruta: [docs/DISENO.md](docs/DISENO.md).

## Estado
- [x] Hito 1: servidor FastAPI + PWA que sube fotos al Mac
- [x] Generador `.scad` por intersección de vistas (`server/app/views/scad_writer.py`)
- [x] Hito 2: hoja de marcadores ArUco (`tools/marker_sheet.py`) + rectificación a mm (`rectify.py`)
- [x] Hito 3: contornos → `.scad` → `.stl` automático al subir (`pipeline.py`)
- [x] Hito 4: visor 3D (three.js) y cotas de calibre + holgura con regeneración
- [x] Hito 5: arranque con launchd, mDNS (`scan2print.local`), carpeta de salida y webhook
- [x] Hito 6: vídeo → malla con Object Capture (**pendiente de probar en el Mac**, ver abajo)

## Arranque en el Mac
```bash
brew install openscad mkcert && mkcert -install
cd server && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
mkcert -cert-file cert.pem -key-file key.pem "$(scutil --get LocalHostName).local" localhost
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-certfile cert.pem --ssl-keyfile key.pem
```
En el Android (misma Wi-Fi): abre `https://<nombre-del-mac>.local:8443` → menú → *Instalar app*.
Para que Android confíe en el certificado, instala la CA de `mkcert -CAROOT` (`rootCA.pem`) en Ajustes → Seguridad → Certificados.

Los trabajos se guardan en `~/Scan2Print/jobs/` (configurable con `SCAN2PRINT_STORAGE`).

## Arranque automático y salida (Orca / tu página de impresión)
```bash
sed "s#REPO_PATH#$PWD#" deploy/com.scan2print.plist > ~/Library/LaunchAgents/com.scan2print.plist
launchctl load ~/Library/LaunchAgents/com.scan2print.plist
```
- Cada trabajo terminado copia `AAAAMMDD-HHMMSS_<id>.stl/.scad` a `~/Scan2Print/out/` (`SCAN2PRINT_OUT`): abre ahí con Orca o vigila la carpeta desde tus agentes.
- `SCAN2PRINT_WEBHOOK=<url>`: POST JSON `{"event":"job.done","id","dims":{ancho,fondo,alto},"files":{stl,scad}}` al terminar.
- API estable para tu página: `GET /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/files/pieza.stl`, `POST /api/jobs/{id}/params`.

## Vídeo → malla (Object Capture) — primer test en el Mac
```bash
cd mac/ObjectCaptureCLI && swift build -c release
export SCAN2PRINT_OBJECT_CAPTURE="$PWD/.build/release/scan2print-object-capture"   # añádelo también al .plist
# prueba suelta con una carpeta de fotos:
$SCAN2PRINT_OBJECT_CAPTURE ./fotos ./salida medium && ls salida
```
Flujo: vídeo → fotogramas nítidos (`photogrammetry/frames.py`) → CLI → `.obj` → `mesh.py` (mayor fragmento, Y-up→Z-up, m→mm, rellena huecos, apoya en Z=0) → `pieza.stl`.
La escala de Object Capture es aproximada: indica en la app la **dimensión más larga medida con calibre** y se regenera sin repetir la reconstrucción pesada… (hoy la repite; mejora pendiente).

**Cosas a verificar en el Mac (no se han podido ejecutar aquí):**
1. Que `swift build` compila (API `PhotogrammetrySession`).
2. Que con una URL de carpeta `.modelFile` genera `*.obj`. Si solo genera `.usdz`, cambiar `Entry.swift` o convertir con `usdz`→`obj`.
3. Orientación (Y-up) y que el STL aparece apoyado en Z=0 en Orca.

## Tests
```bash
cd server && .venv/bin/pytest
```
