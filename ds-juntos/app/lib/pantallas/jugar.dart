import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../app.dart';
import '../modelos.dart';
import '../nucleo/lanzador.dart';
import '../nucleo/sistemas.dart';
import '../servicios/ajustes_local.dart';
import '../servicios/partidas.dart';

/// Abre un juego: sincroniza la partida, avisa a la pareja, lanza RetroArch
/// y al terminar sube la partida.
///
/// En netplay solo el anfitrión sincroniza: el invitado juega sobre la
/// partida del anfitrión y no sube nada.
Future<void> jugar(BuildContext context, Juego juego, {Netplay? netplay}) async {
  final s = Servicios.de(context);
  final rom = s.ajustes.rutaRom(juego.romSha1);
  if (rom == null || !await File(rom).exists()) {
    if (context.mounted) avisar(context, 'Falta el ROM en este dispositivo: ábrelo y pulsa «Buscar ROM».');
    return;
  }
  if (!context.mounted) return;

  // RetroArch no acepta netplay al abrirlo en Android, ni el cable link de
  // Game Boy, ni unirse sin IP: en esos casos se explican los pasos.
  final conPasos = netplay != null &&
      (plataformaActual == Plataforma.android ||
          juego.modo == ModoJuntos.cableLink ||
          (netplay is Invitado && netplay.ip.isEmpty));
  if (conPasos) {
    final seguir = await mostrarPasosNetplay(context, juego, netplay);
    if (!seguir || !context.mounted) return;
  }

  final sincroniza = netplay is! Invitado;
  final rutaSrm = await s.lanzador.rutaPartidaLocal(rom);

  if (sincroniza) {
    if (!await s.partidas.bloquear(juego.id)) {
      if (context.mounted) {
        avisar(context, '${s.sesion.pareja?.nombre ?? 'Tu pareja'} está jugando esta partida ahora mismo.');
      }
      return;
    }
    if (!context.mounted) return;
    final ok = await intentar(context, () async {
      await s.partidas.antesDeJugar(juego, rutaSrm, () => _preguntarConflicto(context));
    });
    if (!ok) {
      await s.partidas.desbloquear(juego.id);
      return;
    }
  }

  await s.presencia.jugando(juego.titulo);
  try {
    if (context.mounted) {
      await intentar(context, () => s.lanzador.jugarYEsperar(
            juego: juego,
            rom: rom,
            apodo: s.sesion.yo!.nombre,
            netplay: conPasos ? null : netplay,
          ));
    }
  } finally {
    await s.presencia.conectada();
    if (sincroniza) {
      var subida = false;
      try {
        subida = await s.partidas.despuesDeJugar(juego, rutaSrm);
      } finally {
        await s.partidas.desbloquear(juego.id);
      }
      if (context.mounted) avisar(context, subida ? 'Partida guardada en la nube ✓' : 'La partida no ha cambiado');
    }
  }
}

Future<EleccionConflicto> _preguntarConflicto(BuildContext context) async {
  final r = await showDialog<EleccionConflicto>(
    context: context,
    barrierDismissible: false,
    builder: (c) => AlertDialog(
      title: const Text('Las dos partidas han cambiado'),
      content: const Text(
        'Este dispositivo y la nube tienen progresos distintos. Elige con cuál seguir. '
        'La otra no se pierde: queda una copia en la carpeta de partidas o en el historial.',
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, EleccionConflicto.local), child: const Text('La de este dispositivo')),
        FilledButton(onPressed: () => Navigator.pop(c, EleccionConflicto.nube), child: const Text('La de la nube')),
      ],
    ),
  );
  return r ?? EleccionConflicto.local;
}

/// Pasos para jugar juntos según el modo del juego. Devuelve true si se sigue.
Future<bool> mostrarPasosNetplay(BuildContext context, Juego juego, Netplay netplay) async {
  final anfitrion = netplay is Anfitrion;
  final ip = netplay is Invitado && netplay.ip.isNotEmpty ? netplay.ip : null;
  if (ip != null) await Clipboard.setData(ClipboardData(text: ip));
  if (!context.mounted) return false;

  final pasos = switch (juego.modo) {
    ModoJuntos.cableLink => anfitrion
        ? 'En RetroArch: Menú rápido → Opciones del núcleo → Network Link: «Server». Espera a tu pareja.'
        : 'En RetroArch: Menú rápido → Opciones del núcleo → Network Link: «Client» e IP del servidor: $ip (ya copiada).',
    _ => anfitrion
        ? 'En RetroArch: Menú principal → Netplay → «Alojar partida». Tu pareja se unirá.'
        : ip == null
            ? 'En RetroArch: Menú principal → Netplay → «Actualizar lista de anfitriones» y elige la partida de tu pareja.'
            : 'En RetroArch: Menú principal → Netplay → «Conectarse a un anfitrión» y pega la IP: $ip (ya copiada).',
  };
  final aviso = juego.modo == ModoJuntos.redLocal
      ? '\n\nOjo: el multijugador local de la DS necesita muy poco retraso. A distancia puede no funcionar.'
      : '';

  final r = await showDialog<bool>(
    context: context,
    builder: (c) => AlertDialog(
      title: Text(anfitrion ? 'Vas a alojar la partida' : 'Vas a unirte'),
      content: Text('$pasos$aviso'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancelar')),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Abrir RetroArch')),
      ],
    ),
  );
  return r ?? false;
}

/// Si el modo permite jugar a la vez (los demás se juegan por turnos).
bool admiteJugarJuntos(ModoJuntos modo) => modo != ModoJuntos.turnos;
