/// Consolas que admite la app, con el núcleo de RetroArch que usa cada una
/// y cómo se puede jugar en pareja a distancia.
library;

/// Cómo se puede jugar juntos a un juego.
enum ModoJuntos {
  /// Mismo juego, cada uno con su mando, por netplay de RetroArch.
  netplay('Netplay', 'Jugáis a la vez: uno aloja y el otro se une.'),

  /// Juegos de DS con modo online (servidores Wiimmfi).
  wiimmfi('Online DS', 'El juego tenía modo online: os encontráis por Wiimmfi.'),

  /// Cable link de Game Boy por red (núcleo Gambatte). Experimental.
  cableLink('Cable link', 'Cable link de Game Boy por red. Experimental.'),

  /// Multijugador local de DS: solo en la misma red.
  redLocal('Red local', 'Solo en la misma red. A distancia, por turnos.'),

  /// Cada uno juega cuando quiere y compartís la partida guardada.
  turnos('Por turnos', 'Compartís la partida: uno sigue donde lo dejó el otro.');

  const ModoJuntos(this.nombre, this.explicacion);
  final String nombre;
  final String explicacion;

  static ModoJuntos desdeId(String id) =>
      ModoJuntos.values.firstWhere((m) => m.name == id, orElse: () => ModoJuntos.turnos);
}

class Sistema {
  const Sistema({
    required this.id,
    required this.nombre,
    required this.extensiones,
    required this.nucleo,
    required this.modo,
    required this.carpetaCaratulas,
  });

  final String id;
  final String nombre;
  final List<String> extensiones;

  /// Nombre base del núcleo de RetroArch (sin `_libretro` ni extensión).
  final String nucleo;

  /// Modo juntos por defecto; cada juego puede cambiarlo.
  final ModoJuntos modo;

  /// Carpeta de carátulas en thumbnails.libretro.com.
  final String carpetaCaratulas;
}

const List<Sistema> sistemas = [
  Sistema(
    id: 'nds',
    nombre: 'Nintendo DS',
    extensiones: ['nds'],
    nucleo: 'melondsds',
    modo: ModoJuntos.turnos,
    carpetaCaratulas: 'Nintendo - Nintendo DS',
  ),
  Sistema(
    id: 'gba',
    nombre: 'Game Boy Advance',
    extensiones: ['gba'],
    nucleo: 'mgba',
    modo: ModoJuntos.turnos,
    carpetaCaratulas: 'Nintendo - Game Boy Advance',
  ),
  Sistema(
    id: 'gb',
    nombre: 'Game Boy / Color',
    extensiones: ['gb', 'gbc'],
    nucleo: 'gambatte',
    modo: ModoJuntos.cableLink,
    carpetaCaratulas: 'Nintendo - Game Boy Color',
  ),
  Sistema(
    id: 'nes',
    nombre: 'NES',
    extensiones: ['nes'],
    nucleo: 'fceumm',
    modo: ModoJuntos.netplay,
    carpetaCaratulas: 'Nintendo - Nintendo Entertainment System',
  ),
  Sistema(
    id: 'snes',
    nombre: 'Super Nintendo',
    extensiones: ['sfc', 'smc'],
    nucleo: 'snes9x',
    modo: ModoJuntos.netplay,
    carpetaCaratulas: 'Nintendo - Super Nintendo Entertainment System',
  ),
  Sistema(
    id: 'n64',
    nombre: 'Nintendo 64',
    extensiones: ['n64', 'z64', 'v64'],
    nucleo: 'mupen64plus_next',
    modo: ModoJuntos.netplay,
    carpetaCaratulas: 'Nintendo - Nintendo 64',
  ),
  Sistema(
    id: 'md',
    nombre: 'Mega Drive',
    extensiones: ['md', 'gen', 'smd'],
    nucleo: 'genesis_plus_gx',
    modo: ModoJuntos.netplay,
    carpetaCaratulas: 'Sega - Mega Drive - Genesis',
  ),
];

/// Extensión del archivo en minúsculas y sin punto ('' si no tiene).
String extension(String ruta) {
  final nombre = ruta.split(RegExp(r'[\\/]')).last;
  final punto = nombre.lastIndexOf('.');
  return punto <= 0 ? '' : nombre.substring(punto + 1).toLowerCase();
}

/// Nombre del archivo sin carpeta ni extensión.
String nombreBase(String ruta) {
  final nombre = ruta.split(RegExp(r'[\\/]')).last;
  final punto = nombre.lastIndexOf('.');
  return punto <= 0 ? nombre : nombre.substring(0, punto);
}

Sistema? sistemaPorRuta(String ruta) {
  final ext = extension(ruta);
  for (final s in sistemas) {
    if (s.extensiones.contains(ext)) return s;
  }
  return null;
}

Sistema? sistemaPorId(String id) {
  for (final s in sistemas) {
    if (s.id == id) return s;
  }
  return null;
}

/// Título legible a partir del nombre del archivo:
/// "Pokemon - Platinum Version (USA) (Rev 1).nds" -> "Pokemon - Platinum Version".
String tituloDesdeArchivo(String ruta) {
  return nombreBase(ruta)
      .replaceAll(RegExp(r'\s*[\(\[][^\)\]]*[\)\]]'), '')
      .replaceAll('_', ' ')
      .trim();
}

/// URL de la carátula en el repositorio de libretro (puede no existir:
/// la app muestra una portada generada si falla).
String urlCaratula(Sistema sistema, String rutaRom) {
  final nombre = nombreBase(rutaRom).replaceAll(RegExp(r'[&*/:`<>?\\|"]'), '_');
  return 'https://thumbnails.libretro.com/'
      '${Uri.encodeComponent(sistema.carpetaCaratulas)}/Named_Boxarts/'
      '${Uri.encodeComponent(nombre)}.png';
}
