# Hoja de ruta

## Hecho: versión 0.1 (MVP)
- Cuentas con email y emparejar con código.
- Biblioteca compartida: los juegos se identifican por la huella del ROM y los ROMs no se suben nunca.
- Abrir RetroArch en Windows, Mac (orden de consola) y Android (intent).
- Sincronización de partidas con candado, detección de conflictos e historial de versiones.
- Presencia en directo: conectada o jugando a qué y desde cuándo.
- «Juega conmigo»: invitación, alojar o unirse, con IP de Tailscale o lista de RetroArch.
- Toques, chat y botón de Discord.

## Siguiente: probar en vuestros equipos
1. Compilar en Windows, Mac y Android y anotar lo que falle.
2. Probar la sincronización: jugar en el PC, seguir en el móvil y forzar un conflicto.
3. Probar «Juega conmigo» con un juego de SNES por Tailscale.
4. Probar un juego de DS con Wiimmfi (Mario Kart DS).

## Ideas para después
- **Notificaciones con la app cerrada** (Firebase Cloud Messaging), para que el «Juega conmigo» llegue también con el móvil bloqueado.
- **Entrar con Google** (Supabase OAuth con enlaces profundos en escritorio y Android).
- **Discord Rich Presence** en escritorio: «Jugando a X con Y».
- **Logros** con RetroAchievements: los núcleos ya los admiten; la app solo tendría que mostrarlos.
- **Diario de pareja**: tiempo jugado juntos, rachas y fotos (capturas de RetroArch).
- **Estado de ánimo o «te echo de menos»** en la barra de presencia.
- **Menú más DS**: dos paneles (biblioteca arriba y pareja abajo) y sonidos.
