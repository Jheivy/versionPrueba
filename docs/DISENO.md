# Diseño: Scan2Print — de foto/vídeo a .scad/.stl (Android → Mac mini hub)

Documento de arquitectura **del estado actual**. Uso y opciones: [README](../README.md). Lo que no está hecho, al final.

## Contexto
Replicar piezas rotas para imprimir en 3D. El Mac mini (Apple Silicon) es el hub y el Android lo usa como PWA por la
Wi-Fi de casa. Dos modos de entrada:
- **3 vistas** (planta/alzado/perfil sobre una hoja A4 de marcadores) → `.scad` paramétrico → `.stl`. Piezas mecánicas.
- **Vídeo 3D** (giro alrededor de la pieza) → malla con Object Capture (Swift CLI, solo macOS) → `.stl`. Formas orgánicas.

## Arquitectura
```
Android (PWA, Chrome)  ──HTTPS LAN──▶  Mac mini: FastAPI (un solo proceso)
  cámara guiada / galería               ├─ auth.py        emparejamiento por QR, cookie HttpOnly, tokens para agentes
  visor 3D (three.js)                   ├─ storage.py     límites de subida, tope de disco, retención y limpieza
  Ajustes, Trabajos, Capturar           ├─ pipeline.py    3 vistas: rectify → contornos → .scad → OpenSCAD → .stl
                                        ├─ pipeline_video.py  fotogramas → Object Capture CLI → malla → .stl
                                        └─ ~/Scan2Print/{jobs,out}   trabajos (job.json) y exportaciones (Orca / agentes)
```
- Estado de cada trabajo: `jobs/<id>/job.json` (escritura atómica, un lock por trabajo, un único *worker* pesado a la vez).
- Salida: `.stl` y `.scad` copiados a `~/Scan2Print/out/` (el STL de una regeneración sustituye al anterior) y, si se define,
  aviso por webhook (`SCAN2PRINT_WEBHOOK`) para tu página de impresión.
- Red: HTTPS con mkcert (necesario para la cámara y para instalar la PWA), mDNS `scan2print.local`, `launchd` en `deploy/`.

## Medición (lo que más importa)
1. **Hoja de marcadores** ArUco `DICT_4X4_50` en las 4 esquinas de un A4 (marcador de 30 mm): homografía → 1 mm = 10 px (`rectify.py`).
2. **Contorno** por umbral de Otsu en la hoja rectificada, simplificación Douglas-Peucker y huecos como contornos interiores
   (`contours.py`). Los huecos circulares se reconocen y pasan a ser parámetros del `.scad` (`holes.py`).
3. **Paralaje** (`parallax.py`): la cara superior de la pieza está más cerca de la cámara y se ve más grande. Se estima la
   distancia y el punto bajo la cámara desde la homografía (focal del EXIF o 26 mm típicos) y se deshace el factor `D/(D−h)`
   con la profundidad que dan las otras vistas. Con la cámara a 25–45 cm: ±1,2 mm en 40×20×30 mm (sin corregir, +7 a +11 %).
4. **Enderezado** (`regularize.py`): rectas y ángulos de 90° exactos hasta ~4° de desvío.
5. **Coherencia** (`coherence.py`): cada dimensión sale en dos vistas (ancho: planta y alzado; fondo: planta y perfil; alto:
   alzado y perfil); si difieren más de 0,8 mm o el 2 % se avisa antes de generar.
6. **Cotas con calibre**: tienen prioridad sobre todo lo anterior y reescalan cada vista desde su propio tamaño.
7. Resultado: `scad_writer.py` escribe un `.scad` legible (variables arriba, `polygon()` por vista) y el sólido es la
   **intersección de las tres extrusiones** (visual hull ortográfico). Ver límites abajo.
8. Vídeo: escala por una cota (`largo`) o, sin ella, estimada y marcada como tal.

## Interfaz (PWA en `web/`, sin paso de compilación)
- **Navegación:** barra inferior flotante (Capturar · Trabajos · Ajustes), router por hash con View Transitions, pantalla de
  emparejamiento si el móvil no está autorizado. ES modules, three.js y fuentes locales (la app no necesita internet),
  service worker generado por el servidor (versionado por hash de contenido), gzip + caché inmutable.
- **Captura:** cámara guiada con `/api/detect` cada ~700 ms (hoja visible, nitidez, luz, distancia) y disparo activo solo en
  verde; alternativa de galería/cámara nativa.
- **Revisión de contornos:** el trabajo se pausa en `review` y muestra contorno (naranja) y huecos (turquesa); se puede
  repetir una foto o continuar. Un aviso plegable señala las vistas que no cuadran.
- **Resultado:** miniatura isométrica renderizada en el servidor (`/api/jobs/{id}/thumb.png`), visor 3D con cotas, rejilla de
  1 cm, cubo de referencia y **corte por plano en X, Y o Z** para ver el interior; medidas, agujeros (con diámetro estándar
  probable), ajuste de medidas y descarga STL/.scad.
- **Ajustes:** estado del servidor, almacenamiento (uso, retención, límites, borrado manual), seguridad (dispositivos, QR).
- **Identidad visual «taller de precisión»:** grafito y papel técnico con rejilla de plano, botón principal de tinta sólida,
  un único acento naranja (el color del filamento; también marca cotas, foco y progreso), colores de eje rojo/verde/azul
  para X/Y/Z, IBM Plex Sans y Mono (cifras), claro y oscuro, objetivos táctiles ≥ 44 px, `prefers-reduced-motion`.
  Los tokens están en `web/css/tokens.css`; los componentes (`.btn`, `.chip`, `.note`, `.spec`, `.mfield`, `.seg`) en `components.css`.
- **Gestos y respuesta:** deslizar para borrar, hoja inferior arrastrable, tirar para actualizar, hápticos configurables.

## Seguridad y límites
Todo `/api` exige dispositivo emparejado (cookie o Bearer); CSRF por `Origin`; solo hashes en disco. Subidas: foto 40 MB,
vídeo 1,5 GB, 400 ficheros, cuerpos cortados por bytes recibidos; 20 GB de tope de disco con expulsión de lo más antiguo;
retención de 30 días desde el último uso. Detalle y variables de entorno en el README.

## Pruebas
- `server/tests` (pytest, ~120): imágenes sintéticas con ArUco, fotos en perspectiva 3D real (`synth.photo3d`), API,
  autenticación, límites, limpieza, OpenSCAD real (la CI lo instala).
- `tests/e2e` (Playwright): arranca el servidor con trabajos de ejemplo y recorre la app en móvil (claro y oscuro):
  navegación, visor 3D y corte, revisión, ajustes, y una auditoría de desbordes, objetivos táctiles y botones sin nombre.
- Pendiente de **verificación real**: fotos de móvil, el CLI de Object Capture, orientación en Orca y `launchd` en el Mac.

## Límites conocidos y siguientes pasos
- La intersección de extrusiones no reproduce huecos internos ni cóncavos que no se vean en alguna vista; es ideal para
  piezas prismáticas. El vídeo cubre las formas orgánicas pero sin parámetros editables.
- Si la pieza no está centrada bajo la cámara el paralaje deja ~1 mm de residuo; una focal muy distinta de la supuesta
  falsea la distancia.
- Contorno por Otsu: sombras fuertes, piezas oscuras o brillantes y papel no blanco lo degradan.
- Solo agujeros circulares (no ranuras ni avellanados); la hoja A4 limita la pieza a ~190 × 277 mm.
- Ideas: escala automática en vídeo con la hoja en escena, mesa giratoria, ajuste de primitivas sobre la malla, exportar 3MF,
  reparar pieza rota reflejando la mitad sana.
