# Diseño: Scan2Print — de foto/vídeo a .scad/.stl (Android → Mac mini hub)

## Contexto
Replicar piezas rotas para imprimir en 3D. Repo vacío (`jheivy/versionprueba`, rama `claude/mobile-3d-reconstruction-app-98dg7q`).
Decisiones: Mac mini Apple Silicon como hub, PWA en el móvil servida por el Mac, backend Python/FastAPI, **MVP = alzado/planta/perfil → .scad paramétrico**. Vídeo→malla en fase 2.

## Arquitectura
```
Android (PWA, Chrome)  --HTTPS LAN (mDNS scan2print.local)-->  Mac mini
  cámara / subida                                             FastAPI + cola de trabajos
  ver resultado (three.js)                                    ├─ vistas/  OpenCV → contornos → .scad (OpenSCAD CLI → .stl)
                                                              ├─ photogrammetry/ (fase 2) CLI Swift Object Capture → .usdz → .stl
                                                              └─ storage/jobs/<id>/ + carpeta vigilada para el slicer
```
- Transferencia: subida HTTP multipart directa en Wi-Fi (rápido, sin nube). Fuera de casa: Tailscale opcional.
- HTTPS con certificado local (mkcert) — necesario para `getUserMedia` y para instalar la PWA.
- Salida: los .stl/.3mf se copian a `~/Scan2Print/out/` para abrir en Bambu/Prusa/Orca Slicer (o lanzar el slicer por CLI).

## Medición de tamaños (clave)
1. **Marcador de referencia**: hoja impresa con ArUco/ChArUco de tamaño conocido (p.ej. 50 mm) bajo el objeto o junto al dibujo → corrección de perspectiva + escala mm/px. Es el método principal.
2. **Cotas manuales**: en la PWA el usuario puede fijar 1–n medidas tomadas con calibre ("este lado = 23.4 mm") y el sistema reescala; tiene prioridad sobre el marcador.
3. Fase 2: escala en fotogrametría con el mismo tapete ChArUco (Object Capture no da escala absoluta fiable).
4. Tolerancia de impresión configurable (holgura ±0.2 mm) como parámetro en el .scad.

## Modo MVP: alzado/planta/perfil → 3D
Entrada: 3 fotos (o 1 hoja con las 3 vistas en cuadrícula conocida), cada una con marcador o con cotas.
Pipeline (`server/app/views/`):
1. `rectify.py` – detecta ArUco, homografía, recorta y escala a mm.
2. `contours.py` – umbral adaptativo + `findContours`, simplificación (Douglas-Peucker), detección de círculos (Hough) para agujeros; contornos interiores = huecos.
3. `reconstruct.py` – **intersección de extrusiones**: extruir planta en Z, alzado en Y, perfil en X e `intersection()` (visual hull ortográfico). Funciona muy bien para piezas prismáticas/mecánicas.
4. `scad_writer.py` – genera .scad legible con variables al inicio (`ancho`, `alto`, `holgura`, `diam_agujero_1`…) y `polygon()` por vista → editable a mano.
5. `export.py` – `openscad -o pieza.stl pieza.scad` (subprocess) + validación con `trimesh` (watertight, dimensiones).
Alternativa interna: CadQuery para exportar también STEP — opcional.

## PWA (`web/`)
- Vite + TypeScript simple (sin framework pesado), `manifest.json` + service worker.
- Pantallas: Nuevo trabajo → elegir modo → asistente de captura (guía "foto de planta", "alzado", "perfil", overlay para encuadrar) → introducir cotas → enviar → progreso (SSE/polling) → visor 3D (three.js, STLLoader) con dimensiones → "Enviar a carpeta del slicer".
- Editor de cotas sobre la imagen rectificada: el usuario toca dos puntos y escribe la medida.

## Backend (`server/`)
- FastAPI + uvicorn, `jobs` en SQLite (estado, modo, ficheros), workers con `asyncio`/`ProcessPoolExecutor`.
- Endpoints: `POST /jobs` (subida), `GET /jobs/{id}`, `GET /jobs/{id}/preview` (contornos detectados para corregir), `POST /jobs/{id}/params` (cotas/ajustes → regenera), `GET /jobs/{id}/files/{name}`.
- Dependencias: opencv-contrib-python (ArUco), numpy, trimesh, shapely; OpenSCAD instalado vía Homebrew.
- Servicio autoarrancable con `launchd` + anuncio mDNS (`zeroconf`).

## Fase 2: vídeo → malla
- `mac/ObjectCaptureCLI/` (Swift, `PhotogrammetrySession`, detail `.full`) recibe carpeta de fotogramas.
- Backend: extraer fotogramas del vídeo con ffmpeg (≈2–3 fps, descartar borrosos por varianza del Laplaciano), lanzar CLI, convertir .usdz/.obj → .stl con trimesh, escalar con el tapete ChArUco o con una cota manual, limpiar/rellenar (cerrar agujeros, decimar).
- Consejo de captura en la PWA: objeto sobre tapete, giro 360° a 2 alturas, luz difusa, objetos brillantes → spray mate.

## Fase 3 (ideas)
- Mesa giratoria + modo "fotos automáticas".
- Ajuste de primitivas (cilindros/planos) sobre la malla para obtener .scad paramétrico desde vídeo.
- Reparar pieza rota: reflejar la mitad sana / unir fragmentos.

## Estructura del repo
```
server/app/{main.py,jobs.py,views/,photogrammetry/,export.py}
server/tests/  (imágenes sintéticas con ArUco + piezas conocidas)
web/  (PWA)
mac/ObjectCaptureCLI/  (fase 2)
tools/marker_sheet.py  (genera PDF A4 con ArUco/ChArUco para imprimir)
docs/  (guía de captura, instalación en el Mac)
```

## Hitos
1. Esqueleto: FastAPI + PWA que sube fotos al Mac por HTTPS y las lista.
2. Hoja de marcadores + rectificación y escala (test: error < 0.5 mm en 50 mm).
3. Contornos → .scad → .stl para 1 vista (extrusión) y luego 3 vistas (intersección).
4. Visor 3D, editor de cotas, regeneración.
5. launchd + mDNS + carpeta del slicer.
6. Fase 2 fotogrametría.

## Verificación
- `pytest server/tests`: imágenes sintéticas renderizadas de un .scad conocido (cubo con agujero, pieza en L) → reconstrucción y comparación de dimensiones (bbox, volumen con trimesh, tolerancia ±0.5 mm).
- `openscad` genera STL sin errores y `trimesh.is_watertight`.
- E2E: desde el Android en la misma Wi-Fi abrir `https://scan2print.local`, instalar PWA, fotografiar una pieza real medida con calibre, imprimir y comparar.
