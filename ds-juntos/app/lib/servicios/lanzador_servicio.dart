import 'dart:async';
import 'dart:io';

import 'package:android_intent_plus/android_intent.dart';
import 'package:android_intent_plus/flag.dart';
import 'package:flutter/widgets.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../modelos.dart';
import '../nucleo/lanzador.dart';
import 'ajustes_local.dart';

/// Abre RetroArch y espera a que se cierre (o a que se vuelva a la app en Android).
class LanzadorServicio {
  LanzadorServicio(this.ajustes);
  final AjustesLocal ajustes;

  /// Ruta del .srm de este juego en este dispositivo.
  Future<String> rutaPartidaLocal(String rom) async =>
      rutaPartida(await ajustes.carpetaPartidas(), rom, plataformaActual);

  Future<void> jugarYEsperar({
    required Juego juego,
    required String rom,
    required String apodo,
    Netplay? netplay,
  }) async {
    final nucleo = juego.sistema!.nucleo;
    if (plataformaActual == Plataforma.android) {
      final intent = intentAndroid(paquete: ajustes.retroarch, nucleo: nucleo, rom: rom);
      final volver = _esperarVuelta();
      await AndroidIntent(
        action: 'android.intent.action.MAIN',
        package: intent.paquete,
        componentName: intent.actividad,
        arguments: intent.extras,
        flags: [Flag.FLAG_ACTIVITY_NEW_TASK, Flag.FLAG_ACTIVITY_CLEAR_TOP],
      ).launch();
      await volver;
      return;
    }

    final carpetaPartidas = await ajustes.carpetaPartidas();
    await Directory(carpetaPartidas).create(recursive: true);
    final soporte = await getApplicationSupportDirectory();
    final cfg = File(p.join(soporte.path, 'ds_juntos.cfg'));
    await cfg.writeAsString(configExtra(carpetaPartidas: carpetaPartidas, apodo: apodo));

    final orden = ordenEscritorio(
      plataforma: plataformaActual,
      retroarch: ajustes.retroarch,
      carpetaNucleos: ajustes.carpetaNucleos,
      nucleo: nucleo,
      rom: rom,
      archivoConfigExtra: cfg.path,
      apodo: apodo,
      netplay: netplay,
    );
    if (!await File(orden.ejecutable).exists()) {
      throw StateError('No encuentro RetroArch en ${orden.ejecutable}. Revisad Ajustes.');
    }
    final proceso = await Process.start(orden.ejecutable, orden.argumentos);
    // Vaciar la salida para que el proceso no se bloquee.
    unawaited(proceso.stdout.drain<void>());
    unawaited(proceso.stderr.drain<void>());
    await proceso.exitCode;
  }

  /// Se completa cuando la app pasa a segundo plano y luego vuelve.
  Future<void> _esperarVuelta() {
    final listo = Completer<void>();
    var salio = false;
    late final AppLifecycleListener oyente;
    oyente = AppLifecycleListener(
      onHide: () => salio = true,
      onResume: () {
        if (salio && !listo.isCompleted) {
          oyente.dispose();
          listo.complete();
        }
      },
    );
    return listo.future;
  }
}
