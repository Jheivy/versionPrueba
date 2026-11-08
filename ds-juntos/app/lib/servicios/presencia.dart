import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../modelos.dart';
import '../nucleo/red.dart';
import 'sesion.dart';

/// IP de Tailscale de este dispositivo (null si no está conectado).
Future<String?> ipTailscale() async {
  try {
    final interfaces = await NetworkInterface.list(type: InternetAddressType.IPv4);
    return elegirIpTailscale(interfaces.expand((i) => i.addresses).map((a) => a.address));
  } catch (_) {
    return null;
  }
}

/// Quién está conectado y a qué juega, en directo (Supabase Realtime Presence).
class PresenciaServicio extends ChangeNotifier {
  PresenciaServicio(this.sesion);
  final Sesion sesion;

  RealtimeChannel? _canal;
  Presencia? _mia;

  /// Presencia de la pareja (null = desconectada).
  Presencia? pareja;

  Future<void> iniciar() async {
    final yo = sesion.yo!;
    _mia = Presencia(
      userId: yo.id,
      nombre: yo.nombre,
      estado: Estado.conectada,
      desde: DateTime.now(),
      ip: await ipTailscale(),
    );
    final canal = sb.channel('pareja:${sesion.parejaId}', opts: RealtimeChannelConfig(key: yo.id));
    canal.onPresenceSync((_) => _actualizarPareja()).subscribe((estado, _) async {
      if (estado == RealtimeSubscribeStatus.subscribed) await canal.track(_mia!.aMapa());
    });
    _canal = canal;
  }

  void _actualizarPareja() {
    final otros = _canal!
        .presenceState()
        .where((s) => s.key != sesion.yo!.id)
        .expand((s) => s.presences)
        .map((p) => Presencia.desdeMapa(p.payload))
        .toList();
    pareja = otros.isEmpty ? null : otros.last;
    notifyListeners();
  }

  Future<void> jugando(String titulo) => _cambiar(Estado.jugando, titulo);
  Future<void> conectada() => _cambiar(Estado.conectada, null);

  Future<void> _cambiar(Estado estado, String? juego) async {
    _mia = Presencia(
      userId: _mia!.userId,
      nombre: sesion.yo!.nombre,
      estado: estado,
      desde: DateTime.now(),
      juego: juego,
      ip: await ipTailscale(),
    );
    await _canal?.track(_mia!.aMapa());
  }

  String? get miIp => _mia?.ip;

  Future<void> detener() async {
    await _canal?.untrack();
    if (_canal != null) await sb.removeChannel(_canal!);
    _canal = null;
  }
}
