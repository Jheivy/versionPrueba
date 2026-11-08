import 'dart:io';

import 'package:supabase_flutter/supabase_flutter.dart';

import '../modelos.dart';
import '../nucleo/sync_decision.dart';
import 'ajustes_local.dart';
import 'biblioteca.dart';
import 'sesion.dart';

/// Qué copia de la partida queda cuando hay conflicto.
enum EleccionConflicto { nube, local }

/// Sincroniza la partida guardada (.srm) de cada juego con Supabase Storage.
class Partidas {
  Partidas(this.sesion, this.ajustes);
  final Sesion sesion;
  final AjustesLocal ajustes;

  static const bucket = 'partidas';

  String _ruta(String juegoId, String archivo) => '${sesion.parejaId}/$juegoId/$archivo';

  Stream<EstadoPartida?> estado(String juegoId) => sb
      .from('partidas')
      .stream(primaryKey: ['juego_id'])
      .eq('juego_id', juegoId)
      .map((filas) => filas.isEmpty ? null : EstadoPartida.desdeMapa(filas.first));

  Future<EstadoPartida?> _leer(String juegoId) async {
    final fila = await sb.from('partidas').select().eq('juego_id', juegoId).maybeSingle();
    return fila == null ? null : EstadoPartida.desdeMapa(fila);
  }

  /// Reserva la partida. false si la está usando la otra persona.
  Future<bool> bloquear(String juegoId) async =>
      await sb.rpc<bool>('bloquear_partida', params: {'p_juego': juegoId}) == true;

  Future<void> desbloquear(String juegoId) => sb.rpc('desbloquear_partida', params: {'p_juego': juegoId});

  /// Antes de jugar: baja la versión de la nube si es más nueva.
  /// Si las dos copias cambiaron, pregunta con [preguntar].
  Future<AccionSync> antesDeJugar(
    Juego juego,
    String rutaLocal,
    Future<EleccionConflicto> Function() preguntar,
  ) async {
    final remoto = await _leer(juego.id);
    final local = await huellaSiExiste(rutaLocal);
    final accion = decidirSync(
      local: local,
      remoto: remoto?.sha1,
      ultimoSincronizado: ajustes.ultimoSync(juego.id),
    );
    switch (accion) {
      case AccionSync.bajar:
        await _bajar(juego.id, rutaLocal, remoto!.sha1);
      case AccionSync.conflicto:
        if (await preguntar() == EleccionConflicto.nube) {
          await _copiaDeSeguridad(rutaLocal);
          await _bajar(juego.id, rutaLocal, remoto!.sha1);
        }
      // La subida de una copia local nueva se hace al terminar de jugar.
      case AccionSync.subir:
      case AccionSync.nada:
        break;
    }
    return accion;
  }

  /// Después de jugar: sube la partida si ha cambiado.
  Future<bool> despuesDeJugar(Juego juego, String rutaLocal) async {
    final local = await huellaSiExiste(rutaLocal);
    final remoto = await _leer(juego.id);
    if (local == null || local == remoto?.sha1) return false;

    final bytes = await File(rutaLocal).readAsBytes();
    final previa = remoto?.version ?? 0;
    final opciones = const FileOptions(upsert: true, contentType: 'application/octet-stream');
    await sb.storage.from(bucket).uploadBinary(_ruta(juego.id, 'historial/${previa + 1}.srm'), bytes, fileOptions: opciones);
    await sb.storage.from(bucket).uploadBinary(_ruta(juego.id, 'actual.srm'), bytes, fileOptions: opciones);
    await sb.rpc('registrar_subida', params: {'p_juego': juego.id, 'p_sha1': local, 'p_version_previa': previa});
    await ajustes.guardarUltimoSync(juego.id, local);
    return true;
  }

  /// Versiones anteriores guardadas en la nube (las más recientes primero).
  Future<List<int>> historial(String juegoId) async {
    final archivos = await sb.storage.from(bucket).list(path: _ruta(juegoId, 'historial'));
    final versiones = archivos
        .map((f) => int.tryParse(f.name.replaceAll('.srm', '')))
        .whereType<int>()
        .toList()
      ..sort((a, b) => b.compareTo(a));
    return versiones;
  }

  /// Recupera una versión anterior (la actual se guarda antes como copia).
  Future<void> restaurar(Juego juego, int version, String rutaLocal) async {
    await _copiaDeSeguridad(rutaLocal);
    final bytes = await sb.storage.from(bucket).download(_ruta(juego.id, 'historial/$version.srm'));
    await File(rutaLocal).writeAsBytes(bytes, flush: true);
    await despuesDeJugar(juego, rutaLocal);
  }

  Future<void> _bajar(String juegoId, String rutaLocal, String? sha1) async {
    final bytes = await sb.storage.from(bucket).download(_ruta(juegoId, 'actual.srm'));
    final archivo = File(rutaLocal);
    await archivo.parent.create(recursive: true);
    await archivo.writeAsBytes(bytes, flush: true);
    await ajustes.guardarUltimoSync(juegoId, sha1);
  }

  Future<void> _copiaDeSeguridad(String rutaLocal) async {
    final archivo = File(rutaLocal);
    if (!await archivo.exists()) return;
    final marca = DateTime.now().toIso8601String().replaceAll(':', '-').split('.').first;
    await archivo.copy('$rutaLocal.copia-$marca');
  }
}
