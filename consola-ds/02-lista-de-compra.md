# Lista de compra — Consola DS DIY (×2)

> **ACTUALIZACIÓN (sin prototipo aparte):** se eliminan la fuente de 27 W y el cable micro‑HDMI (se prueba con las pantallas finales y un cargador USB‑C que ya tengáis), el stick opcional y el segundo kilo de filamento; las pantallas pasan a Elecrow o anuncios más baratos. La Pi, el disipador y la microSD no se tocan porque van dentro de las consolas finales. Total de la lista: unos 350–500 € las dos consolas (~175–250 € cada una). La versión al día está en el artifact de la lista de compra.
>
> Precios orientativos de noviembre de 2026, **por consola** salvo que se indique. Compruébalos antes de comprar.
> Los enlaces de AliExpress son búsquedas, porque sus anuncios cambian a menudo. Antes de comprar, mirad las valoraciones y que el anuncio diga **"Raspberry Pi 5"**.

## ⚠️ Dos avisos antes de comprar

1. **La Raspberry Pi ha subido de precio** por el coste de la memoria RAM. La Pi 5 de 2 GB ronda ahora los **70–85 €** (salió a ~56 €). Por eso el total real queda en **~185–220 € por consola**, no en ~150 €. Al final hay ideas para recortar.
2. **El multijugador LAN de melonDS es muy sensible a la latencia.** Sus autores dicen que funciona mejor por cable, que *no esperemos que vaya bien por Wi‑Fi* y que **no funciona por VPN/internet**. Con un punto de acceso directo entre las dos consolas (5 GHz) debería mejorar, pero **hay que probarlo**. Por eso la compra va en **dos fases**: primero se valida lo más importante con poco dinero.
   - **Plan B: "cable link"** como el de la Game Boy. La Pi 5 tiene Ethernet, así que un cable corto entre las dos consolas daría la conexión más estable.
   - Se puede jugar a distancia con otras consolas (GBA vía RetroArch netplay), pero no con DS.

---

## FASE 1 — Prototipo en mesa (comprar ya)
Sirve para comprobar que melonDS + multijugador va bien entre dos Pi **antes** de gastar en el resto. Si sale mal, las Pi se aprovechan igual.

| Pieza | Cant. | € aprox./ud | Dónde |
|---|---|---|---|
| Raspberry Pi 5 **2 GB** | 2 | 70–85 | [Página oficial → botón "Buy" (muestra tiendas españolas: Kubii, TiendaTec, RaspiPC)](https://www.raspberrypi.com/products/raspberry-pi-5/) · [RS España](https://es.rs-online.com/web/p/raspberry-pi/0219252) · [Kiwi Electronics](https://www.kiwi-electronics.com/en/raspberry-pi-boards-363/raspberry-pi-5-2gb-20129) · [Botland](https://botland.store/moduly-i-zestawy-raspberry-pi-5/25346-raspberry-pi-5-2gb-5056561803302.html) |
| Active Cooler oficial (disipador + ventilador) | 2 | 5–6 | [Raspberry Pi Active Cooler](https://www.raspberrypi.com/products/active-cooler/) |
| microSD 32–64 GB A1/A2 (Samsung EVO / SanDisk) | 2 | 6–9 | Cualquier tienda grande (Amazon, PcComponentes) |
| Fuente USB‑C 5 V 5 A oficial 27 W (solo para la mesa) | 1–2 | 12–14 | [Raspberry Pi 27W USB‑C](https://www.raspberrypi.com/products/27w-power-supply/) |
| Cable micro‑HDMI → HDMI (para usar una tele/monitor que ya tengáis) | 1–2 | 4–6 | Cualquier tienda |

**Coste fase 1:** ~95–120 € por consola (~190–240 € las dos). Ratón, teclado y monitor: los que tengáis en casa.

**Prueba a hacer:** instalar Raspberry Pi OS + melonDS 1.x en las dos, crear un punto de acceso Wi‑Fi en una y conectar la otra, y jugar a un juego con multijugador local (p. ej. Mario Kart DS) en *System → Multiplayer → Host/Join LAN game*. Después repetir con un cable Ethernet. Os guiaré paso a paso.

---

## FASE 2 — El resto de la consola (cuando la fase 1 funcione)

### Pantallas
| Pieza | Cant./consola | € aprox./ud | Dónde |
|---|---|---|---|
| **Waveshare 4.3" DSI 800×480 táctil capacitiva** (sin drivers, válida para Pi 5) | 2 | 30–40 | [The Pi Hut](https://thepihut.com/collections/waveshare/products/4-3-dsi-capacitive-touchscreen-display-for-raspberry-pi-800x480) · [RobotShop ES](https://www.robotshop.com/es/products/waveshare-43-capacitive-touch-display-for-raspberry-pi-800480-mipi-dsi-interface) · [Waveshare](https://www.waveshare.com/4.3inch-dsi-lcd.htm) |
| Alternativa más barata: Spotpear 4.3" DSI (sin drivers, Pi 5) | 2 | 20–30 | [Spotpear](https://spotpear.com/shop/Raspberry-Pi-4.3-inch-LCD-DSI-MIPI-800x480-Display-Capacitive-Touchscreen.html) |
| Cable DSI Pi 5 (22→15 pines) **200 mm** para la pantalla de arriba, que pasa por la bisagra; comprad también uno de 300 mm por si acaso | 1–2 | 1–3 | [Waveshare Display Cable (B)](https://www.waveshare.com/product/display-cable-b.htm) |
| Lápiz capacitivo de punta fina | 1 | 2–5 | [AliExpress: "stylus capacitivo punta fina"](https://es.aliexpress.com/w/wholesale-capacitive-stylus-fine-tip.html) |

> Por qué 4.3" 800×480: la imagen de DS (256×192) se escala ×2,5 a 640×480 y se ve nítida. Es apaisada como la DS y no necesita drivers. Comprobad que el anuncio incluye el cable de Pi 5 (22 pines); si no, lo cubre la fila del cable.

### Energía
| Pieza | Cant./consola | € aprox./ud | Dónde |
|---|---|---|---|
| Módulo **"18650 UPS" USB‑C 5 V 3 A** (carga + elevador + protección) | 1 | 4–10 | [AliExpress: "18650 UPS module type-c 5V 3A"](https://es.aliexpress.com/w/wholesale-18650-ups-module-type-c-5v-3a.html) |
| Celdas 18650 de marca (Samsung 35E, LG MJ1, Molicel P28A) — **no las compréis en AliExpress, suelen ser falsas** | 2 | 4–6 | [NKON (tienda europea fiable)](https://www.nkon.nl/es/rechargeable/li-ion/18650-size.html) |
| Portapilas 2×18650 en paralelo (o tiras de níquel si soldáis el pack) | 1 | 1–2 | [AliExpress: "18650 holder 2 slot"](https://es.aliexpress.com/w/wholesale-18650-battery-holder-2-slot.html) |
| Interruptor deslizante + LED bicolor | 1 | 1 | Kit de componentes (abajo) |

> La Pi 5 arranca con 3 A, pero limita el USB a 600 mA. Para nuestro uso (mando RP2040 + tarjeta de sonido) basta. Si el módulo da problemas bajo carga, la alternativa fiable (más cara) es el [Waveshare UPS para Pi 5](https://probots.co.in/waveshare-raspberry-pi-5-ups-module-5v-6a-power-expansion-board-uninterruptible-power-supply.html).

### Controles
| Pieza | Cant./consola | € aprox./ud | Dónde |
|---|---|---|---|
| **RP2040‑Zero** (controla botones, LEDs y batería) | 1 | 3–5 | [Waveshare RP2040‑Zero](https://www.waveshare.com/rp2040-zero.htm) · [AliExpress: "RP2040-Zero"](https://es.aliexpress.com/w/wholesale-rp2040-zero.html) |
| Pulsadores táctiles 6×6 mm (kit surtido de alturas) | 1 kit para las dos | 3–5 | [AliExpress: "tactile switch 6x6 kit"](https://es.aliexpress.com/w/wholesale-tactile-switch-6x6-kit.html) |
| Placa perforada (protoboard soldable) | 2 | 1 | [AliExpress: "perfboard"](https://es.aliexpress.com/w/wholesale-perfboard-pcb.html) |
| Sensor Hall A3144 + imanes de neodimio 5×2 mm (detecta la tapa cerrada) | 1 + 1 | 0,5 | [AliExpress: "A3144 hall sensor"](https://es.aliexpress.com/w/wholesale-a3144-hall-sensor.html) · [imanes 5x2](https://es.aliexpress.com/w/wholesale-neodymium-magnet-5x2mm.html) |
| *(Opcional, para PSP)* stick analógico Hall | 1 | 3–8 | [AliExpress: "hall effect joystick module"](https://es.aliexpress.com/w/wholesale-hall-effect-joystick.html) |

### Audio
| Pieza | Cant./consola | € aprox./ud | Dónde |
|---|---|---|---|
| Tarjeta de sonido USB mini (micro + cascos) | 1 | 2–5 | [AliExpress: "usb sound card mini"](https://es.aliexpress.com/w/wholesale-usb-sound-card-mini.html) |
| Amplificador I2S **MAX98357A** | 1 | 2–3 | [AliExpress: "MAX98357A"](https://es.aliexpress.com/w/wholesale-max98357a.html) |
| Altavoz pequeño 8 Ω 1–2 W (~20–28 mm) | 2 | 1 | [AliExpress: "speaker 8 ohm 1w 28mm"](https://es.aliexpress.com/w/wholesale-speaker-8-ohm-1w-28mm.html) |

### Montaje y carcasa (compartido)
| Pieza | Cant. | € aprox. | Dónde |
|---|---|---|---|
| Insertos térmicos M2 / M2.5 (latón) + tornillos M2 surtidos | 1 kit | 6–8 | [AliExpress: "heat set insert M2 kit"](https://es.aliexpress.com/w/wholesale-heat-set-insert-m2.html) |
| Varilla de acero 3 mm o tornillos M3×30 (eje de bisagra) | 1 | 2 | Ferretería |
| Cable de silicona fino 28–30 AWG (varios colores) | 1 | 4–6 | [AliExpress: "silicone wire 30awg"](https://es.aliexpress.com/w/wholesale-silicone-wire-30awg.html) |
| Kit de resistencias + LEDs 3 mm | 1 | 3–4 | [AliExpress: "LED resistor kit"](https://es.aliexpress.com/w/wholesale-led-resistor-kit.html) |
| Filamento PLA (prototipos) + PETG (carcasa final) | 1 kg cada uno | 15–20/kg | Tienda Bambu Lab o cualquier marca |

### Herramientas (solo si no las tenéis)
Soldador con punta fina (p. ej. Pinecil), estaño fino 0,6–0,8 mm, multímetro, pinzas y flux.

---

## Resumen de coste por consola
| Bloque | € |
|---|---|
| Fase 1 (Pi 5, disipador, microSD) | 81–100 |
| Pantallas + cables + lápiz | 63–88 |
| Energía | 13–24 |
| Controles | 6–10 |
| Audio | 6–10 |
| Montaje + filamento (parte proporcional) | 10–15 |
| **Total** | **~180–245 €** (sin herramientas ni fuente de mesa) |

## Cómo acercarse a 150 €
- Pantallas Spotpear o genéricas de AliExpress en vez de Waveshare (−15/20 €).
- Comprar la Pi cuando haya oferta o de segunda mano en buen estado (−10/20 €).
- Pedido único de AliExpress para las dos consolas (envío compartido).
- Dejar el stick y el segundo altavoz para más adelante.

## Fuentes
- [Precio Pi 5 2 GB en España (Geeknetic)](https://www.geeknetic.es/Noticia/32468/La-Raspberry-Pi-5-mas-barata-ya-esta-disponible-desde-56-euros-por-la-version-de-2-GB-de-RAM.html) · [Subida de precio (Korben)](https://korben.info/es/raspberry-pi-modelo-2-gb-cuesta-precio-8-gb-2023.html)
- [melonDS 1.0: multijugador LAN y sus limitaciones](https://melonds.kuribo64.net/comments.php?id=216) · [Docs libretro melonDS DS](https://docs.libretro.com/library/melonds_ds/)
- [Waveshare 4.3" DSI (Electrokit, cables Pi 5 incluidos)](https://www.electrokit.com/en/4.3lcd-800x480px-dsi-with-touch)
