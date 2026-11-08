# Consola DIY estilo DS para 2 — Lluvia de ideas

## Contexto
Queréis construir **2 consolas** tipo Nintendo DS (carcasa impresa en Bambu A1 mini, 180×180×180 mm) para jugar juntos a juegos de DS, con emparejamiento muy fácil, barato pero de calidad. Este documento ordena vuestras ideas, añade las mías y marca qué es v1, qué es extra y qué descartaría.

---

## 1. La decisión que lo condiciona todo: el "cerebro"
**Recomendado: Raspberry Pi 5 (2 GB, la más barata; suficiente)** + emulador **melonDS 1.x (standalone)**.
- melonDS mueve la DS a velocidad completa en Pi 5 (en Pi 4 va justo).
- **melonDS 1.x trae multijugador LAN** → la clave de vuestro proyecto: las dos consolas se ven como si fuera Wi‑Fi local de DS.
- Pi 5 tiene **2 conectores de pantalla MIPI‑DSI** → dos pantallas reales como la DS.
- Wi‑Fi + Bluetooth integrados (mandos BT sin hardware extra).
- Alternativas más baratas (Radxa Zero 3W, Orange Pi): menos potencia y doble pantalla mucho más difícil. No las recomiendo para empezar.

## 2. Conexión entre las dos consolas (lo más importante)
| Modo | Cómo | Para qué |
|---|---|---|
| **Cerca (sin router)** | Consola A crea un punto de acceso Wi‑Fi propio; B se conecta sola (credenciales pre‑guardadas) | Viajes, sofá, sin internet |
| **Misma casa** | Ambas al Wi‑Fi de casa | Menos latencia que el hotspot |
| **Lejos** | VPN tipo Tailscale/ZeroTier → melonDS cree que estáis en la misma LAN | Jugar a distancia |

**Emparejamiento "un botón":** menú "Jugar juntos" → una consola pulsa *Crear sala*, la otra *Unirse* → se lanza el mismo juego en ambas. Como las dos consolas son "gemelas", se configuran emparejadas de fábrica (la vuestra con la suya).
- "Por frecuencia" (radio tipo 2,4 GHz propio/ESP‑NOW): **no lo recomiendo**; melonDS habla por red IP, así que Wi‑Fi directo/hotspot cumple el mismo objetivo sin hardware extra.

## 3. Vuestras ideas, clasificadas
**✅ v1 (imprescindible)**
- Pantalla táctil abajo + pantalla arriba (2× DSI ~3,5–4", relación cercana a 4:3)
- Lápiz (pantalla táctil **resistiva** = más fiel a la DS; capacitiva = necesita stylus de punta conductiva)
- D‑pad, A/B/X/Y, L/R, Start/Select, encendido, volumen +/–
- Altavoces (1 amplificador I2S MAX98357A en v1, estéreo en v2) + jack de cascos
- Micrófono (juegos DS lo usan: soplar, hablar) → tarjeta de audio USB interna (resuelve mic + cascos de golpe)
- LED de encendido y LED de batería (verde/naranja/rojo + carga)
- Botones de **avance rápido**, **screen swap** y **guardado rápido** (hotkeys de melonDS)
- Puerto USB‑C (carga + datos)
- Batería extraíble
- Menú propio estilo DS + menú multijugador

**🟡 v2 (extras que merecen la pena)**
- 1 stick analógico Hall (magnético) — para DS no hace falta, útil para PSP y otros; la carcasa lleva el hueco desde v1
- Vibración (motor ERM pequeño; melonDS soporta Rumble Pak)
- Salida de vídeo (micro‑HDMI de la Pi llevado a un puerto en la carcasa)
- Chat de voz (Mumble/WebRTC sobre la misma red) — posible pero es software propio
- Logros (RetroAchievements) solo donde no choque con el multijugador: p. ej. GBA vía RetroArch
- Conectar mando: Bluetooth integrado + USB → casi gratis

**⚪ Opcional / descartar en v1**
- Cámara: solo la usan juegos de DSi y el soporte en emulador es limitado
- Sensor de movimiento (IMU ~3 €): casi ningún juego de DS lo usa; barato si queréis meterlo para otros sistemas
- NFC: ningún juego de DS lo usa. **Idea chula**: usarlo para *acercar las consolas = emparejar/crear sala*. Bonito pero no necesario
- "SSD": en Pi 5 una NVMe engorda la consola. Mejor **microSD accesible desde fuera** (los juegos DS ocupan poco)

## 4. Ideas extra mías
- **Bisagra tipo concha (clamshell)** con el cable plano de la pantalla superior pasando por la bisagra; cerrar tapa = suspender pantalla.
- **Botón Home** dedicado para volver al menú.
- **Microcontrolador RP2040 (Pico/RP2040‑Zero)** para botones, sticks, LEDs y vibración → aparece como mando USB; simplifica el cableado y no gasta pines de la Pi.
- **Medidor de batería**: v1 leído por el RP2040 (divisor de tensión, gratis); v2 chip MAX17048 si queréis % exacto.
- **Guardado en la nube local**: sincronizar partidas entre las dos consolas.
- **Perfil por consola** (nombre, color, avatar) que aparece al conectar con la otra.
- **Carcasas de colores distintos** para cada uno (impresión con AMS lite o cambio de filamento).
- Ventilador pequeño + rejillas: la Pi 5 se calienta.

## 5. Arquitectura (resumen)
```
Batería 18650 (x2, 1S2P, en compartimento con tapa)
  → módulo carga USB‑C + protección + elevador 5 V / 3 A → Pi 5
Pi 5 ── DSI0: pantalla superior
     ── DSI1: pantalla inferior táctil
     ── USB: RP2040 (botones, stick, LEDs, vibración)  |  tarjeta audio USB (mic + cascos)
     ── I2S: MAX98357A → altavoces
     ── GPIO: sensor Hall de tapa (suspender al cerrar)
     ── I2C (v2): MAX17048 / IMU / NFC opcionales
     ── micro‑HDMI → puerto de vídeo (v2)
Software: Raspberry Pi OS Lite → menú propio (Python/Godot) → melonDS
```

## 6. Coste por consola — versión ECONÓMICA (aprox., verificar precios)
| Parte | Elección barata | € |
|---|---|---|
| Cerebro | **Pi 5 de 2 GB** (melonDS no necesita más RAM) + disipador/ventilador genérico | 55–65 |
| Pantallas | 2× DSI genéricas de AliExpress (~4", una táctil) | 40–55 |
| Energía | 2× 18650 + módulo carga/elevador USB‑C 5 V 3 A genérico (Pi 5 va bien a 3 A sin periféricos USB pesados) | 10–15 |
| Controles | RP2040‑Zero clónico + pulsadores 6×6 con capuchones impresos, sin stick | 6–10 |
| Audio | Tarjeta USB (mic + cascos) + 1 amp MAX98357A + 2 altavoces pequeños | 6–9 |
| Varios | microSD 32 GB, cables, tornillos, insertos | 10–15 |
| Filamento | PLA/PETG | 3–5 |
| **Total** | | **~130–175 €** (vs ~205–270 € antes) |

**Cómo se ahorra (sin perder calidad de juego):**
- Pi 5 2 GB en vez de 4 GB (−15 €).
- Comprar pantallas, baterías y módulos en AliExpress y en un solo pedido para las dos consolas (envío compartido).
- Nivel de batería leído por el RP2040 (divisor de tensión) en vez de chip fuel gauge (−5 €).
- Sin stick analógico en v1: la DS no lo usa (−10 €). Se deja el hueco en la carcasa para añadirlo luego.
- Un solo amplificador (mono → estéreo luego si queréis).
- Botones: pulsadores baratos + capuchones impresos; d‑pad impreso.
- **Opción "ultra‑barata"**: Pi 4 de 2 GB de segunda mano (~30–35 €). Ahorra ~25 € pero algunos juegos 3D de DS irán lentos y solo tiene 1 DSI (habría que usar HDMI para la otra pantalla). Solo si el presupuesto manda.

## 7. Fases de construcción guiada
1. **Prototipo en mesa**: Pi 5 + 2 pantallas + melonDS + multijugador LAN funcionando entre dos Pi (validar lo importante primero).
2. **Controles**: RP2040 + botones en protoboard.
3. **Energía**: baterías, carga, autonomía, LEDs.
4. **Audio**: altavoces, mic, cascos.
5. **Carcasa v1** en PLA (pruebas de encaje) → **v2 en PETG**; bisagra.
6. **Software**: menú estilo DS, "Jugar juntos", hotkeys, perfiles.
7. **Extras v2**: vibración, vídeo, chat de voz, logros, NFC.

## 8. Decisiones tomadas y qué implican
| Decisión | Implicación |
|---|---|
| **Plegable (clamshell)** | Mitad inferior: Pi 5, batería, botones, pantalla táctil. Mitad superior: solo pantalla + altavoces. Bisagra impresa con eje metálico (varilla 3 mm o tornillo M3) y cable FPC de pantalla pasando por la bisagra (con holgura en bucle). Sensor Hall + imán (~0,5 €) para suspender al cerrar. Grosor realista ~25–28 mm cerrada (más gorda que una DS Lite por la Pi 5). Cabe en la A1 mini (~150×90 mm por mitad). |
| **DS + GBA (+ otras, negociable)** | GBA va sobrada en Pi 5 (mGBA). PSP posible en muchos juegos (PPSSPP) pero pide stick → se deja **hueco para 1 stick** en la carcasa; en v1 se puede poner uno barato (~2–8 €). Pi 5 2 GB sigue valiendo. |
| **Prioridad multijugador** | melonDS standalone como emulador DS principal. Logros solo donde no estorbe (p. ej. GBA vía RetroArch), en v2. |
| **Presupuesto ~150 €/consola** | Se mantiene la lista económica de la sección 6. |
| **Soldar "más o menos"** | v1 con módulos pre‑hechos + placa perforada para botones (todo de agujero pasante, fácil). v2 opcional: PCB de botones sencilla encargada a JLCPCB/PCBWay (~5–10 € por 5 placas = ambas consolas + repuestos), que hace el montaje más limpio y fácil. |

