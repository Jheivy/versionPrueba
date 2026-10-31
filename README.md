# Scan2Print

Fotografía una pieza (o su alzado/planta/perfil) con el móvil Android, envíala al Mac mini y obtén un `.scad` paramétrico + `.stl` listo para imprimir.

Diseño completo y hoja de ruta: [docs/DISENO.md](docs/DISENO.md).

## Interfaz (PWA)
Tres pestañas — **Capturar · Trabajos · Ajustes** —, cámara guiada con semáforo en vivo (hoja detectada, nitidez, luz), revisión de contornos antes de generar, progreso por pasos, visor 3D con rejilla de 1 cm y cubo de referencia, y ajuste de medidas con calibre/holgura. Código en `web/` (`css/`, `js/`, `js/views/`), sin dependencias de build.

## Estado
- [x] Hito 1: servidor FastAPI + PWA que sube fotos al Mac
- [x] Generador `.scad` por intersección de vistas (`server/app/views/scad_writer.py`)
- [x] Hito 2: hoja de marcadores ArUco (`tools/marker_sheet.py`) + rectificación a mm (`rectify.py`)
- [x] Hito 3: contornos → `.scad` → `.stl` automático al subir (`pipeline.py`)
- [x] Hito 4: visor 3D (three.js) y cotas de calibre + holgura con regeneración
- [x] Hito 5: arranque con launchd, mDNS (`scan2print.local`), carpeta de salida y webhook
- [x] Hito 6: vídeo → malla con Object Capture (**pendiente de probar en el Mac**, ver abajo)

## Agujeros paramétricos
Los agujeros circulares se detectan en cada vista y se escriben en el `.scad` como parámetros editables:
```
diam_agujero_planta_1 = 3.200;  // posible M3 (paso medio)
pos_agujero_planta_1 = [12.300, 8.100];
```
- En la app aparecen como chips («Ø3,2 mm · planta 1 · posible M3») y se corrige cada Ø con el calibre en *Ajustar medidas*.
- La etiqueta métrica es solo una **sugerencia**: la medida fotográfica tiene ±0,1 mm de error y no se ajusta sola.
- Los huecos que no son círculos (cuadrados, hexágonos, ranuras) y los de Ø < ~2,5 mm se mantienen como polígono.
- El contorno pasa por los píxeles del borde del material, así que el Ø se corrige 1 píxel (0,1 mm); el error en pruebas sintéticas es ≤ 0,1 mm.

## Enderezado de contornos
Antes de generar el modelo, los contornos se «enderezan» (`server/app/views/regularize.py`): los tramos que siguen
siendo una recta (±0,3 mm) se funden en una arista, las casi horizontales/verticales (hasta ~4°) pasan a serlo
exactamente y las esquinas son la intersección de rectas vecinas. Resultado: rectángulos, L, U… con el nº exacto de
vértices y ángulos de 90°, y un `.scad` mucho más legible. Un dibujo torcido 2° mide 40,0 × 19,9 en vez de 40,6 × 21,3.
- **No se toca** un contorno si menos de la mitad de su perímetro son rectas (círculos, elipses, piezas redondas),
  ni uno inclinado ≥ ~6° (se asume que lo es a propósito), ni si el cambio de área supera el 4 %.
- Se puede desactivar por trabajo con el interruptor *Enderezar contornos* en *Ajustar medidas*.
- La pantalla de revisión muestra ya el contorno enderezado: es el mismo que usará el modelo.
- Límite: con ruido > ±0,15 mm en el contorno, el enderezado es parcial (no deforma, deja parte del ruido). Los
  escalones < 0,5 mm se consideran ruido y desaparecen.

## Coherencia entre vistas
Cada dimensión aparece en dos vistas y debe medir lo mismo: **ancho** (planta y alzado), **fondo** (planta y perfil) y
**alto** (alzado y perfil). Si difieren más de 0,8 mm (o el 2 % en piezas grandes) la app lo avisa **antes de generar**
(pantalla de revisión) y también en el resultado, con las dos medidas. El sólido es la intersección de las tres
extrusiones, así que se recorta a la vista más pequeña y las medidas mostradas son las del sólido real.
- **Unificar (promedio):** estira las dos vistas al promedio (`unificar: 1` en `/params`).
- **Cota con calibre:** cada vista se estira hasta la cota desde **su propio** tamaño (antes se aplicaba el factor de la
  planta a todas, y un alzado más estrecho seguía recortando la pieza: una cota de 40 mm daba 36,98 mm).
- O repetir la foto que falle desde la revisión.
- `job.json` incluye `warnings` (`dim`, `views`, `values`, `diff`); vacío cuando todo cuadra.

## Diseño y rendimiento
**Diseño** (`web/css/`, `web/js/`): sistema de tokens claro/oscuro con acento azul→violeta, tipografía Inter (local),
barra inferior flotante con pastilla animada, tarjetas con profundidad, esqueletos de carga, transiciones entre
pantallas (View Transitions API, con el sentido según la navegación), hápticos (ajustable en *Ajustes*) y gestos:
deslizar una tarjeta para borrarla, arrastrar una hoja inferior para cerrarla y tirar de la lista para actualizar.
Respeta `prefers-reduced-motion`.

**Velocidad, sin paso de compilación:**
- three.js (minificado) y la fuente se sirven desde el propio Mac (`web/vendor/`, `web/fonts/`): la app ya no
  necesita internet. Licencias en `web/vendor/LICENSE-three.txt` y `web/fonts/LICENSE-inter-OFL.txt`.
- Cada pantalla se carga bajo demanda y, en reposo, las demás se precargan con `modulepreload` (sin ejecutarlas).
- El servidor comprime (gzip) y cachea: `vendor/` y `fonts/` son inmutables, el resto se revalida con ETag y los
  modelos `…/pieza.stl?v=<rev>` son inmutables (la revisión cambia al regenerar).
- El service worker lo **genera el servidor** a partir de los archivos reales (`GET /sw.js`): la versión es un hash del
  contenido, así no hay listas ni versiones que mantener a mano. La app abre sin red.
- Las fotos se reducen a ≤ 3000 px en el móvil antes de subirlas (4–8 MB → ~1–2 MB).
- Medido con un móvil emulado (30 Mbps, 40 ms, CPU 4× más lenta): abrir un modelo pasa de 755 a 652 ms (frío) y de
  624 a 493 ms (repetido), y deja de descargar 261 kB de internet.

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
La escala de Object Capture es aproximada: indica en la app la **dimensión más larga medida con calibre**. El `.obj` se guarda en `work/` del trabajo y corregir la escala solo reprocesa la malla (segundos); cambiar el `detalle` sí repite la reconstrucción.

**Cosas a verificar en el Mac (no se han podido ejecutar aquí):**
1. Que `swift build` compila (API `PhotogrammetrySession`).
2. Que con una URL de carpeta `.modelFile` genera `*.obj`. Si solo genera `.usdz`, cambiar `Entry.swift` o convertir con `usdz`→`obj`.
3. Orientación (Y-up) y que el STL aparece apoyado en Z=0 en Orca.

## Tests
```bash
cd server && .venv/bin/pytest && .venv/bin/ruff check ..
```
