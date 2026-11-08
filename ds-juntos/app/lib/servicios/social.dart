import '../modelos.dart';
import 'sesion.dart';

/// Invitaciones a jugar, chat y toques.
class Social {
  Social(this.sesion);
  final Sesion sesion;

  Stream<List<Mensaje>> mensajes() => sb
      .from('mensajes')
      .stream(primaryKey: ['id'])
      .eq('pareja_id', sesion.parejaId!)
      .order('creado', ascending: false)
      .limit(100)
      .map((filas) => filas.map(Mensaje.desdeMapa).toList());

  Future<void> escribir(String texto) =>
      sb.from('mensajes').insert({'pareja_id': sesion.parejaId, 'texto': texto.trim()});

  Future<void> toque() => sb.from('mensajes').insert({'pareja_id': sesion.parejaId, 'tipo': 'toque'});

  Stream<List<Invitacion>> invitaciones() => sb
      .from('invitaciones')
      .stream(primaryKey: ['id'])
      .eq('pareja_id', sesion.parejaId!)
      .order('creada', ascending: false)
      .limit(20)
      .map((filas) => filas.map(Invitacion.desdeMapa).toList());

  Future<Invitacion> invitar(String juegoId, String? miIp) async {
    final fila = await sb
        .from('invitaciones')
        .insert({'pareja_id': sesion.parejaId, 'juego_id': juegoId, 'ip_anfitrion': miIp})
        .select()
        .single();
    return Invitacion.desdeMapa(fila);
  }

  Future<void> responder(Invitacion inv, {required bool acepta}) => sb
      .from('invitaciones')
      .update({'estado': acepta ? 'aceptada' : 'rechazada'}).eq('id', inv.id);

  Future<void> cancelar(Invitacion inv) =>
      sb.from('invitaciones').update({'estado': 'cancelada'}).eq('id', inv.id);
}
