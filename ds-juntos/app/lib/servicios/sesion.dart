import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../modelos.dart';

SupabaseClient get sb => Supabase.instance.client;

/// Sesión, perfil propio y el de la pareja.
class Sesion extends ChangeNotifier {
  Perfil? yo;
  Perfil? pareja;
  bool cargando = true;

  String? get parejaId => yo?.parejaId;

  Future<void> iniciar() async {
    sb.auth.onAuthStateChange.listen((_) => recargar());
    await recargar();
  }

  Future<void> recargar() async {
    cargando = true;
    notifyListeners();
    final usuario = sb.auth.currentUser;
    if (usuario == null) {
      yo = null;
      pareja = null;
    } else {
      final filas = await sb.from('perfiles').select();
      final perfiles = filas.map(Perfil.desdeMapa).toList();
      yo = perfiles.where((p) => p.id == usuario.id).firstOrNull;
      pareja = perfiles.where((p) => p.id != usuario.id).firstOrNull;
    }
    cargando = false;
    notifyListeners();
  }

  Future<void> entrar(String email, String clave) =>
      sb.auth.signInWithPassword(email: email.trim(), password: clave);

  Future<void> registrarse(String email, String clave, String nombre) =>
      sb.auth.signUp(email: email.trim(), password: clave, data: {'nombre': nombre.trim()});

  Future<void> salir() => sb.auth.signOut();

  /// Devuelve el código para compartir con la pareja.
  Future<String> crearPareja() async {
    final codigo = await sb.rpc<String>('crear_pareja');
    await recargar();
    return codigo;
  }

  Future<void> unirse(String codigo) async {
    await sb.rpc('unirse_pareja', params: {'p_codigo': codigo.trim().toUpperCase()});
    await recargar();
  }

  Future<String?> codigoPareja() async {
    if (parejaId == null) return null;
    final fila = await sb.from('parejas').select('codigo').eq('id', parejaId!).maybeSingle();
    return fila?['codigo'] as String?;
  }

  Future<void> cambiarPerfil({String? nombre, String? color}) async {
    await sb.from('perfiles').update({
      'nombre': ?nombre,
      'color': ?color,
    }).eq('id', yo!.id);
    await recargar();
  }

  String nombreDe(String userId) =>
      userId == yo?.id ? 'Tú' : (pareja?.id == userId ? pareja!.nombre : 'Alguien');
}
