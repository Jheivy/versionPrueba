import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../nucleo/lanzador.dart';

Plataforma get plataformaActual {
  if (Platform.isWindows) return Plataforma.windows;
  if (Platform.isMacOS) return Plataforma.macos;
  return Plataforma.android;
}

/// Ajustes que solo valen para este dispositivo (rutas, ROMs, etc.).
class AjustesLocal {
  AjustesLocal._(this._prefs);
  final SharedPreferences _prefs;

  static Future<AjustesLocal> cargar() async => AjustesLocal._(await SharedPreferences.getInstance());

  /// Escritorio: ruta del ejecutable. Android: paquete de RetroArch.
  String get retroarch => _prefs.getString('retroarch') ?? retroarchPorDefecto(plataformaActual);
  set retroarch(String v) => _prefs.setString('retroarch', v);

  /// Carpeta de núcleos de RetroArch (solo escritorio).
  String get carpetaNucleos => _prefs.getString('nucleos') ?? _nucleosPorDefecto();
  set carpetaNucleos(String v) => _prefs.setString('nucleos', v);

  /// Carpeta donde RetroArch guarda las partidas (.srm).
  Future<String> carpetaPartidas() async {
    final guardada = _prefs.getString('partidas');
    if (guardada != null) return guardada;
    if (plataformaActual == Plataforma.android) return '/storage/emulated/0/RetroArch/saves';
    final soporte = await getApplicationSupportDirectory();
    return p.join(soporte.path, 'partidas');
  }

  set carpetaPartidasManual(String v) => _prefs.setString('partidas', v);

  String get discordUrl => _prefs.getString('discord') ?? '';
  set discordUrl(String v) => _prefs.setString('discord', v);

  /// ROM local de cada juego (por su huella).
  String? rutaRom(String sha1) => _mapa('roms')[sha1];
  Future<void> guardarRutaRom(String sha1, String ruta) => _guardarEnMapa('roms', sha1, ruta);

  /// Última huella sincronizada de la partida de cada juego.
  String? ultimoSync(String juegoId) => _mapa('sync')[juegoId];
  Future<void> guardarUltimoSync(String juegoId, String? sha1) => _guardarEnMapa('sync', juegoId, sha1);

  Map<String, String> _mapa(String clave) {
    final txt = _prefs.getString(clave);
    if (txt == null) return {};
    return Map<String, String>.from(jsonDecode(txt) as Map);
  }

  Future<void> _guardarEnMapa(String clave, String k, String? v) {
    final m = _mapa(clave);
    if (v == null) {
      m.remove(k);
    } else {
      m[k] = v;
    }
    return _prefs.setString(clave, jsonEncode(m));
  }

  String _nucleosPorDefecto() {
    if (plataformaActual == Plataforma.macos) {
      final home = Platform.environment['HOME'] ?? '';
      return '$home/Library/Application Support/RetroArch/cores';
    }
    return r'C:\RetroArch-Win64\cores';
  }
}
