# Scan2Print

Fotografía una pieza (o su alzado/planta/perfil) con el móvil Android, envíala al Mac mini y obtén un `.scad` paramétrico + `.stl` listo para imprimir.

Diseño completo y hoja de ruta: [docs/DISENO.md](docs/DISENO.md).

## Estado
- [x] Hito 1: servidor FastAPI + PWA que sube fotos al Mac
- [x] Generador `.scad` por intersección de vistas (`server/app/views/scad_writer.py`)
- [x] Hito 2: hoja de marcadores ArUco (`tools/marker_sheet.py`) + rectificación a mm (`rectify.py`)
- [x] Hito 3: contornos → `.scad` → `.stl` automático al subir (`pipeline.py`)
- [ ] Hitos 4–6: visor 3D, cotas, launchd/mDNS, fotogrametría

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

## Tests
```bash
cd server && .venv/bin/pytest
```
