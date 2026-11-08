# DS Juntos

Vuestra «consola» compartida para Windows, Mac y Android:

- **Biblioteca** de juegos (DS, GBA, Game Boy, NES, SNES, N64, Mega Drive) con carátulas.
- **Partidas sincronizadas**: al terminar de jugar se suben a la nube y el otro dispositivo sigue donde lo dejasteis. Hay historial de versiones y un candado para no pisaros.
- **Presencia**: veis si el otro está conectado y a qué juega, en directo.
- **«Juega conmigo»**: invitación al instante; uno aloja y el otro se une.
- **Toques y chat**, y un botón para abrir vuestra llamada de Discord.

La app no emula: abre **RetroArch** con el núcleo adecuado. Usar RetroArch en los tres sistemas hace que las partidas (`.srm`) valgan igual en todos.

> Los juegos tienen que ser copias de cartuchos vuestros.

## Qué se puede jugar juntos a distancia

| Modo | Juegos | Cómo |
|---|---|---|
| **Netplay** | NES, SNES, N64, Mega Drive | Netplay de RetroArch: los dos jugáis la misma partida, cada uno con su mando |
| **Online DS** | DS con modo Wi-Fi (Mario Kart DS, Pokémon…) | Servidores Wiimmfi: cada uno abre su juego y entra al modo online |
| **Cable link** | Game Boy / Color | Network Link del núcleo Gambatte. Experimental |
| **Red local** | Multijugador local de DS | Solo con muy poco retraso. A distancia puede no ir |
| **Por turnos** | Todos | Compartís la partida y cada uno sigue donde lo dejó el otro |

Cada juego tiene su modo y lo podéis cambiar en su ficha.

## Puesta en marcha

### 1. Supabase (una vez, gratis)
1. Cread un proyecto en [supabase.com](https://supabase.com).
2. En **SQL Editor**, pegad y ejecutad [`supabase/migrations/001_inicial.sql`](supabase/migrations/001_inicial.sql). Crea las tablas, la seguridad, el almacén de partidas y el tiempo real.
3. Opcional, para entrar sin confirmar el email: **Authentication → Sign In / Providers → Email**, desactivad *Confirm email*.
4. En **Project Settings → API**, copiad la *Project URL* y la clave pública (*anon / publishable*).
5. En `app/`, copiad `supabase.example.json` a `supabase.json` y pegad esos dos valores. `supabase.json` no se sube al repositorio.

### 2. RetroArch en cada dispositivo
- **Windows**: instaladlo en `C:\RetroArch-Win64` o poned la ruta en Ajustes.
- **Mac**: `/Applications/RetroArch.app`.
- **Android**: la versión de la [web de RetroArch](https://www.retroarch.com/?page=platforms) (paquete `com.retroarch.aarch64`) o la de Play Store (`com.retroarch`). Cambiad el paquete en Ajustes si hace falta.

En cada RetroArch, descargad los núcleos desde *Online Updater → Core Downloader*:
- melonDS DS
- mGBA
- Gambatte
- FCEUmm
- Snes9x
- Mupen64Plus-Next
- Genesis Plus GX

Usad **la misma versión de RetroArch y de los núcleos** en los dos: el netplay lo exige.

**Solo en Android:**
- En *Settings → Saving*, desactivad *Sort Saves into Folders* y poned *SaveRAM Autosave Interval* en 10 segundos.
- Antes de volver a DS Juntos, usad *Cerrar contenido*, para que la partida esté guardada al subirla.
- La primera vez, en Ajustes de DS Juntos pulsad **Permitir acceso a los archivos**.

### 3. Tailscale (recomendado para jugar juntos)
Instalad [Tailscale](https://tailscale.com) en los cuatro dispositivos con la misma cuenta.
- La app detecta la IP de Tailscale y «Juega conmigo» conecta directo.
- Sin Tailscale, el invitado busca la partida en *Netplay → Actualizar lista de anfitriones* de RetroArch, que usa sus servidores relay.

### 4. Compilar y ejecutar
Hace falta [Flutter](https://docs.flutter.dev/get-started/install) 3.38 o superior.

```bash
cd app
flutter pub get
flutter run --dart-define-from-file=supabase.json            # en el dispositivo conectado
flutter build windows --dart-define-from-file=supabase.json  # en Windows
flutter build macos   --dart-define-from-file=supabase.json  # en Mac
flutter build apk     --dart-define-from-file=supabase.json  # APK para instalar en el móvil
```

## Primer uso
1. Cada uno crea su cuenta: nombre, email y contraseña.
2. Uno pulsa **Crear pareja** y le pasa el código de 6 letras al otro, que pulsa **Unirme**.
3. **Añadir juego** → elegid el ROM. En el otro dispositivo, añadid el mismo archivo: la app lo reconoce por su huella y lo enlaza al mismo juego.
4. Pulsad un juego → **Jugar**. Al cerrar RetroArch, la partida sube sola.

## Estructura
```
ds-juntos/
├─ supabase/migrations/001_inicial.sql   tablas, seguridad (RLS), funciones y almacén
└─ app/lib/
   ├─ nucleo/      lógica pura y con tests: sistemas, sincronización, órdenes de RetroArch, red
   ├─ servicios/   Supabase (sesión, biblioteca, partidas, presencia, social), lanzador, ajustes
   └─ pantallas/   inicio, ficha del juego, jugar, chat, ajustes, login, emparejar
```

Tests: `cd app && flutter test`.

## Estado
Está comprobado:
- la lógica (15 tests);
- `flutter analyze` sin avisos;
- la base de datos en un Postgres local: emparejar, el límite de dos personas, el candado, la subida de versiones y que nadie de fuera ve vuestros datos.

**Sin probar todavía**, porque necesita vuestros equipos o vuestro proyecto de Supabase:
- compilar en Windows, Mac y Android;
- la conexión real con Supabase;
- abrir RetroArch;
- el netplay entre dispositivos.

La hoja de ruta está en [PLAN.md](PLAN.md).
