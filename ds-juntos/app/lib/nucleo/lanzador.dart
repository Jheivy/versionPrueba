/// Construye la orden para abrir un juego en RetroArch en cada plataforma.
/// Solo arma datos; quien la ejecuta es `servicios/lanzador_servicio.dart`.
library;

enum Plataforma { windows, macos, android }

/// Rol en una partida de netplay.
sealed class Netplay {
  const Netplay();
}

class Anfitrion extends Netplay {
  const Anfitrion();
}

class Invitado extends Netplay {
  const Invitado(this.ip, {this.puerto = puertoNetplay});
  final String ip;
  final int puerto;
}

const int puertoNetplay = 55435;

class OrdenEscritorio {
  const OrdenEscritorio(this.ejecutable, this.argumentos);
  final String ejecutable;
  final List<String> argumentos;
}

class IntentAndroid {
  const IntentAndroid({required this.paquete, required this.actividad, required this.extras});
  final String paquete;
  final String actividad;
  final Map<String, String> extras;
}

const String actividadRetroArch = 'com.retroarch.browser.retroactivity.RetroActivityFuture';

String archivoNucleo(String nucleo, Plataforma plataforma) => switch (plataforma) {
      Plataforma.windows => '${nucleo}_libretro.dll',
      Plataforma.macos => '${nucleo}_libretro.dylib',
      Plataforma.android => '${nucleo}_libretro_android.so',
    };

/// Ejecutable de RetroArch por defecto en cada sistema de escritorio.
String retroarchPorDefecto(Plataforma plataforma) => switch (plataforma) {
      Plataforma.windows => r'C:\RetroArch-Win64\retroarch.exe',
      Plataforma.macos => '/Applications/RetroArch.app/Contents/MacOS/RetroArch',
      Plataforma.android => 'com.retroarch.aarch64',
    };

String _unir(String carpeta, String archivo, Plataforma p) {
  final sep = p == Plataforma.windows ? r'\' : '/';
  return carpeta.endsWith(sep) ? '$carpeta$archivo' : '$carpeta$sep$archivo';
}

/// Configuración extra que la app añade a RetroArch en escritorio para
/// que las partidas se guarden en la carpeta que sincroniza.
String configExtra({required String carpetaPartidas, required String apodo}) => [
      'savefile_directory = "$carpetaPartidas"',
      'savestate_directory = "$carpetaPartidas"',
      'sort_savefiles_enable = "false"',
      'sort_savefiles_by_content_enable = "false"',
      'sort_savestates_enable = "false"',
      'netplay_nickname = "$apodo"',
      '',
    ].join('\n');

OrdenEscritorio ordenEscritorio({
  required Plataforma plataforma,
  required String retroarch,
  required String carpetaNucleos,
  required String nucleo,
  required String rom,
  required String archivoConfigExtra,
  required String apodo,
  Netplay? netplay,
}) {
  assert(plataforma != Plataforma.android);
  final args = <String>[
    '-L',
    _unir(carpetaNucleos, archivoNucleo(nucleo, plataforma), plataforma),
    rom,
    '--appendconfig',
    archivoConfigExtra,
    '--nick',
    apodo,
    ...switch (netplay) {
      null => const <String>[],
      Anfitrion() => const ['--host'],
      Invitado(:final ip, :final puerto) => ['--connect', ip, '--port', '$puerto'],
    },
  ];
  return OrdenEscritorio(retroarch, args);
}

/// En Android RetroArch no acepta netplay por intent: se abre el juego y
/// la app indica los pasos para alojar o unirse desde el menú Netplay.
IntentAndroid intentAndroid({
  required String paquete,
  required String nucleo,
  required String rom,
  String? archivoConfig,
}) {
  return IntentAndroid(
    paquete: paquete,
    actividad: actividadRetroArch,
    extras: {
      'ROM': rom,
      'LIBRETRO': '/data/data/$paquete/cores/${archivoNucleo(nucleo, Plataforma.android)}',
      'CONFIGFILE': archivoConfig ?? '/storage/emulated/0/Android/data/$paquete/files/retroarch.cfg',
      'IME': 'com.android.inputmethod.latin/.LatinIME',
    },
  );
}

/// Ruta de la partida guardada que crea RetroArch para un ROM
/// (mismo nombre, extensión .srm, en la carpeta de partidas).
String rutaPartida(String carpetaPartidas, String rom, Plataforma plataforma) {
  final nombre = rom.split(RegExp(r'[\\/]')).last;
  final punto = nombre.lastIndexOf('.');
  final base = punto <= 0 ? nombre : nombre.substring(0, punto);
  return _unir(carpetaPartidas, '$base.srm', plataforma);
}
