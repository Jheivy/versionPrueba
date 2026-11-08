import 'package:flutter/material.dart';

import 'servicios/ajustes_local.dart';
import 'servicios/biblioteca.dart';
import 'servicios/lanzador_servicio.dart';
import 'servicios/partidas.dart';
import 'servicios/presencia.dart';
import 'servicios/sesion.dart';
import 'servicios/social.dart';

/// Todos los servicios de la app, accesibles con `Servicios.de(context)`.
class Servicios extends InheritedWidget {
  Servicios({super.key, required this.sesion, required this.ajustes, required super.child})
      : biblioteca = Biblioteca(sesion, ajustes),
        partidas = Partidas(sesion, ajustes),
        presencia = PresenciaServicio(sesion),
        social = Social(sesion),
        lanzador = LanzadorServicio(ajustes);

  final Sesion sesion;
  final AjustesLocal ajustes;
  final Biblioteca biblioteca;
  final Partidas partidas;
  final PresenciaServicio presencia;
  final Social social;
  final LanzadorServicio lanzador;

  static Servicios de(BuildContext context) => context.dependOnInheritedWidgetOfExactType<Servicios>()!;

  @override
  bool updateShouldNotify(Servicios oldWidget) => false;
}

/// Colores tipo DS: gris plata con acento azul.
ThemeData tema(Brightness brillo) {
  final esquema = ColorScheme.fromSeed(seedColor: const Color(0xFF4F7CFF), brightness: brillo);
  return ThemeData(
    colorScheme: esquema,
    useMaterial3: true,
    scaffoldBackgroundColor: brillo == Brightness.light ? const Color(0xFFE9ECF2) : const Color(0xFF15181E),
    cardTheme: const CardThemeData(clipBehavior: Clip.antiAlias, elevation: 1),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
  );
}

Color colorDesdeHex(String hex) {
  final limpio = hex.replaceFirst('#', '');
  return Color(int.tryParse('FF$limpio', radix: 16) ?? 0xFF4F7CFF);
}

void avisar(BuildContext context, String texto) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(texto)));

/// Hace una acción mostrando el error si falla. Devuelve true si fue bien.
Future<bool> intentar(BuildContext context, Future<void> Function() accion) async {
  try {
    await accion();
    return true;
  } catch (e) {
    if (context.mounted) avisar(context, mensajeError(e));
    return false;
  }
}

String mensajeError(Object e) {
  final txt = e.toString();
  final m = RegExp(r'message: ([^,\)]+)').firstMatch(txt);
  return m?.group(1) ?? txt.replaceFirst(RegExp(r'^\w+(Exception|Error): ?'), '');
}

String haceCuanto(DateTime? fecha) {
  if (fecha == null) return '—';
  final d = DateTime.now().difference(fecha.toLocal());
  if (d.inMinutes < 1) return 'ahora mismo';
  if (d.inMinutes < 60) return 'hace ${d.inMinutes} min';
  if (d.inHours < 24) return 'hace ${d.inHours} h';
  return 'hace ${d.inDays} d';
}
