# Guía de prueba en el Mac y el móvil (≈ 45 min en total, por bloques)

Todo lo desarrollado se ha probado con fotos y mallas **sintéticas**. Esta guía sirve para comprobarlo con la realidad y
decirme qué falla. Cada bloque es independiente: si uno no sale, sigue con el siguiente y anótalo.

**Qué necesitas:** el Mac mini, el Android (misma Wi-Fi), una impresora para la hoja A4, un **calibre** y 2–3 piezas
sencillas que ya hayas medido (una caja o tapa con 2 agujeros, una pieza con una ranura y otra más alta, de 4–5 cm).

Dónde está cada cosa para anotar resultados:
- Trabajos: `~/Scan2Print/jobs/<id>/` → `job.json` (medidas, `parallax`, `quality`, `quality_warnings`, `holes`, `mesh`), `input/` (tus fotos), `output/pieza.scad|stl`.
- Exportaciones para Orca: `~/Scan2Print/out/`.
- Log del servidor: `/tmp/scan2print.log` (con `launchd`) o la terminal. Más detalle: `SCAN2PRINT_LOG=DEBUG`.

---

## 0. Preparación (10 min)
1. **Mac**: sigue «Arranque en el Mac» del README (`brew install openscad mkcert`, venv, `requirements-dev.txt`, certificado).
   - Genera el certificado **también con la IP del Mac**, por si el móvil no resuelve `.local`:
     `mkcert -cert-file cert.pem -key-file key.pem "$(scutil --get LocalHostName).local" localhost 192.168.X.Y`
   - Arranca con `deploy/run.sh` y comprueba que en la terminal sale el QR de emparejamiento (o `deploy/pair.sh`).
2. **Hoja de marcadores**: la app la ofrece en *Ajustes → Hoja de marcadores (PDF, A4)* (o `server/.venv/bin/python tools/marker_sheet.py`) → imprime el PDF **al 100 %** (sin «ajustar a página») y
   **mide un marcador con el calibre: debe medir 30,0 mm** (si no, la escala de todo estará mal). Anótalo: ____ mm.
3. **Móvil**: instala la CA de `mkcert -CAROOT` (Ajustes → Seguridad → Certificados), abre `https://<mac>.local:8443` (o la IP),
   escanea el QR / escribe el código → «Instalar app».
   - ✔ Anota: ¿abre por `.local`? ¿hace falta la IP? ¿pide instalar la CA? ¿se instala como app?

## 1. Precisión con 3 vistas (10 min) — lo más importante
Pieza A: la caja/tapa con medidas conocidas (ancho × fondo × alto con calibre: ____ × ____ × ____ mm).
1. Hoja plana sobre mesa clara, buena luz difusa, sin sombras duras. Pieza **centrada** en la hoja.
2. *Capturar → 3 vistas*. Móvil a **30–40 cm**, centrado sobre la hoja, la hoja entera en pantalla. Fíjate en el semáforo:
   ¿se pone verde? ¿aparece «aleja la cámara o usa zoom» o «se ven N de 4 marcadores»? Anota los avisos.
3. Haz planta (pieza tumbada), alzado (de pie, cara larga hacia ti) y perfil (de pie, girada 90°). Activa «Revisar contornos».
4. En la revisión: ¿el contorno naranja sigue el borde de la pieza? ¿hay avisos de calidad? Continúa.
5. Compara con el calibre. **Resultado esperado:** error ≤ 0,5 mm (aceptable ≤ 1 mm).

| | Calibre | App | Diferencia |
|---|---|---|---|
| Ancho | | | |
| Fondo | | | |
| Alto | | | |

6. Repite **alejando el móvil a ~60 cm con zoom** y anota si mejora. Mira en `job.json` → `parallax` (distancia estimada vs.
   la que mediste con una cinta: ____ vs ____ cm) y el interruptor «Corregir perspectiva» (Ajustar medidas): ¿mejora o empeora?
7. Si el error es mayor de 1 mm: manda `input/` y `job.json` del trabajo.

## 2. Agujeros y ranura (5 min)
Pieza B con 2 agujeros (mide su Ø con calibre: ____, ____) y, si tienes, una ranura (ancho ____ × largo ____).
- ¿Salen los chips «Ø…» / «Ranura …»? ¿Coinciden con el calibre (±0,2 mm)? ¿Aparece «posible M3/M4…» donde toca?
- En *Ajustar medidas* corrige un Ø con el calibre → *Regenerar* → comprueba el STL en el visor.
- Abre el `.scad` en OpenSCAD: ¿se entiende y se puede editar (`diam_agujero_…`, `ancho_ranura_…`)?

## 3. Condiciones difíciles (5 min) — lo que debe avisar
Haz una foto de planta de cada una y anota qué hace la app:
1. **Sombra dura** (lámpara lateral) → ¿el contorno se ensancha? ¿cuánto?
2. **Pieza blanca** sobre el A4 → debe salir el aviso «se distingue poco del papel».
3. **Hoja arrugada** o con el móvil casi pegado → aviso de hoja deformada / pocos marcadores.
4. **Luz con degradado** (media hoja a oscuras) → el contorno debe seguir bien.

## 4. Cola de envío sin Wi-Fi (3 min)
1. Haz las fotos de una pieza, **activa el modo avión** y pulsa «Enviar al Mac».
2. ¿Sale «guardado en el móvil»? ¿Aparece en *Trabajos → Pendientes de enviar* con el contador en la pestaña?
3. **Cierra la app del todo y ábrela**: ¿sigue ahí?
4. Quita el modo avión: ¿se envía sola (en menos de ~5 s al volver a la app)? ¿Un solo trabajo, sin duplicado?
5. Repite con un **vídeo grande** (≥ 100 MB): ¿se guarda? ¿falla por espacio?

## 5. Impresión y Orca (5 min)
1. Abre `~/Scan2Print/out/…stl` en Orca: ¿la pieza aparece **apoyada** en la cama y con la escala bien (mide con la regla de Orca)?
2. Imprime la pieza A (o una versión rápida) y mídela con el calibre: ¿cuánto se aparta del original? (anota para saber qué
   holgura usar: *Ajustar medidas → Holgura*).

## 6. Vídeo 3D con la hoja (10 min, solo en el Mac)
1. `cd mac/ObjectCaptureCLI && swift build -c release` → anota si **compila** (si falla, copia el error).
2. `export SCAN2PRINT_OBJECT_CAPTURE="$PWD/.build/release/scan2print-object-capture"` y reinicia el servidor con ese entorno
   (en el `.plist` si usas `launchd`).
3. Pon la pieza **sobre la hoja de marcadores** (pegada con cinta para que no se mueva), graba 40–60 s girando alrededor en dos alturas.
4. Mira el log: `hoja de marcadores en el vídeo: sí` y después `hoja de marcadores en el modelo: 4 marcadores, error … mm`.
   - Si dice «no se ve» en el modelo: el papel no salió en el modelo o los marcadores no se leyeron en la textura. Manda
     `~/Scan2Print/jobs/<id>/work/obj/` (el `.obj`, el `.mtl` y la textura `.png/.jpg`) — con eso lo arreglo.
5. En el resultado: ¿pone «Escala real medida con la hoja de marcadores»? Mide la pieza con el calibre y compara:
   ____ vs ____ mm. ¿El STL aparece sin el papel, apoyado y con el lado largo en X?
6. Repite **sin hoja**: debe seguir funcionando con «Escala estimada» y la opción de indicar una medida.

## 7. Arranque automático (2 min)
`launchctl load` del `.plist` (README) → reinicia el Mac → ¿el servidor está arriba y el móvil conecta sin tocar nada?
¿Se vuelve a anunciar `scan2print.local`?

---

## Qué mandarme
- Lo que falló (número de bloque + qué viste), con captura de la pantalla o del log.
- Para un trabajo concreto con error de medida: la carpeta `input/` y su `job.json`.
- Para el vídeo: la carpeta `work/obj/` y el log.
- La tabla de precisión de los bloques 1 y 2.

**Criterios de «va bien»:** error ≤ 0,5 mm con 3 vistas; los avisos saltan en el bloque 3; una captura enviada sin red llega
sola y una sola vez; la hoja da la escala del vídeo con error < 3 mm (si no, avisa y cae a la estimada); el STL llega a Orca
apoyado y a escala.
