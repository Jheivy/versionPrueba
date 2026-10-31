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
- [ ] Hito 6: fotogrametría (vídeo → malla)

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

## Tests
```bash
cd server && .venv/bin/pytest
```
