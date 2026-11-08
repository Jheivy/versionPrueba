import 'dart:io';

import 'package:crypto/crypto.dart';

import '../modelos.dart';
import '../nucleo/sistemas.dart';
import 'ajustes_local.dart';
import 'sesion.dart';

/// SHA-1 de un archivo leyéndolo por partes (los ROMs pueden pesar cientos de MB).
Future<String> huellaArchivo(String ruta) async {
  final digest = await sha1.bind(File(ruta).openRead()).first;
  return digest.toString();
}

/// Huella de un archivo si existe, o null.
Future<String?> huellaSiExiste(String ruta) async =>
    await File(ruta).exists() ? huellaArchivo(ruta) : null;

class ResultadoAnadir {
  const ResultadoAnadir(this.juego, {required this.yaExistia});
  final Juego juego;
  final bool yaExistia;
}

class Biblioteca {
  Biblioteca(this.sesion, this.ajustes);
  final Sesion sesion;
  final AjustesLocal ajustes;

  /// Juegos de la pareja en tiempo real.
  Stream<List<Juego>> juegos() => sb
      .from('juegos')
      .stream(primaryKey: ['id'])
      .eq('pareja_id', sesion.parejaId!)
      .order('titulo', ascending: true)
      .map((filas) => filas.map(Juego.desdeMapa).toList());

  /// Añade un ROM a la biblioteca compartida (o lo enlaza en este
  /// dispositivo si la pareja ya lo había añadido).
  Future<ResultadoAnadir> anadirRom(String ruta) async {
    final sistema = sistemaPorRuta(ruta);
    if (sistema == null) throw const FormatException('Formato no reconocido');
    final huella = await huellaArchivo(ruta);
    await ajustes.guardarRutaRom(huella, ruta);

    final existente = await sb
        .from('juegos')
        .select()
        .eq('pareja_id', sesion.parejaId!)
        .eq('rom_sha1', huella)
        .maybeSingle();
    if (existente != null) return ResultadoAnadir(Juego.desdeMapa(existente), yaExistia: true);

    final fila = await sb
        .from('juegos')
        .insert({
          'pareja_id': sesion.parejaId,
          'titulo': tituloDesdeArchivo(ruta),
          'sistema': sistema.id,
          'rom_sha1': huella,
          'modo_juntos': sistema.modo.name,
        })
        .select()
        .single();
    return ResultadoAnadir(Juego.desdeMapa(fila), yaExistia: false);
  }

  /// Enlaza el ROM de este dispositivo con un juego que ya está en la lista.
  /// Devuelve false si el archivo no es el mismo juego.
  Future<bool> enlazarRom(Juego juego, String ruta) async {
    final huella = await huellaArchivo(ruta);
    if (huella != juego.romSha1) return false;
    await ajustes.guardarRutaRom(huella, ruta);
    return true;
  }

  Future<void> cambiarModo(Juego juego, ModoJuntos modo) =>
      sb.from('juegos').update({'modo_juntos': modo.name}).eq('id', juego.id);

  Future<void> renombrar(Juego juego, String titulo) =>
      sb.from('juegos').update({'titulo': titulo.trim()}).eq('id', juego.id);

  Future<void> borrar(Juego juego) => sb.from('juegos').delete().eq('id', juego.id);
}
