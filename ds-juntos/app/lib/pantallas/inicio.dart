import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../app.dart';
import '../modelos.dart';
import '../nucleo/lanzador.dart';
import '../nucleo/sistemas.dart';
import 'ajustes.dart';
import 'chat.dart';
import 'juego.dart';
import 'jugar.dart';

class PantallaInicio extends StatefulWidget {
  const PantallaInicio({super.key});

  @override
  State<PantallaInicio> createState() => _PantallaInicioState();
}

class _PantallaInicioState extends State<PantallaInicio> {
  StreamSubscription<List<Invitacion>>? _subInv;
  StreamSubscription<List<Mensaje>>? _subMsg;
  final _vistas = <String>{};
  int? _ultimoMensaje;
  List<Juego> _juegos = const [];
  late Servicios s;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_subInv != null) return;
    s = Servicios.de(context);
    s.presencia.iniciar();
    _subInv = s.social.invitaciones().listen(_alInvitar);
    _subMsg = s.social.mensajes().listen(_alMensaje);
  }

  @override
  void dispose() {
    _subInv?.cancel();
    _subMsg?.cancel();
    s.presencia.detener();
    super.dispose();
  }

  void _alMensaje(List<Mensaje> mensajes) {
    if (mensajes.isEmpty) return;
    final nuevo = mensajes.first;
    final primera = _ultimoMensaje == null;
    _ultimoMensaje = nuevo.id;
    if (primera || nuevo.de == s.sesion.yo!.id || !mounted) return;
    if (nuevo.esToque) {
      HapticFeedback.heavyImpact();
      avisar(context, '💗 ${s.sesion.pareja?.nombre ?? 'Tu pareja'} te ha dado un toque');
    } else {
      avisar(context, '${s.sesion.pareja?.nombre ?? 'Tu pareja'}: ${nuevo.texto}');
    }
  }

  Future<void> _alInvitar(List<Invitacion> lista) async {
    for (final inv in lista) {
      final reciente = DateTime.now().difference(inv.creada.toLocal()).inMinutes < 10;
      if (inv.estado != 'pendiente' || inv.de == s.sesion.yo!.id || !reciente || !_vistas.add(inv.id)) continue;
      final juego = _juegos.where((j) => j.id == inv.juegoId).firstOrNull;
      if (juego == null || !mounted) continue;
      HapticFeedback.heavyImpact();
      final acepta = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
          title: Text('${s.sesion.pareja?.nombre ?? 'Tu pareja'} quiere jugar contigo'),
          content: Text('${juego.titulo}\n${juego.modo.explicacion}'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Ahora no')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('¡Vamos!')),
          ],
        ),
      );
      await s.social.responder(inv, acepta: acepta == true);
      if (acepta == true && mounted) {
        await jugar(
          context,
          juego,
          // Sin IP de Tailscale, el invitado busca la partida en la lista de RetroArch.
          netplay: juego.modo == ModoJuntos.wiimmfi ? null : Invitado(inv.ipAnfitrion ?? ''),
        );
      }
    }
  }

  Future<void> _anadir() async {
    final r = await FilePicker.pickFiles(dialogTitle: 'Elige el ROM');
    final ruta = r.isEmpty ? null : r.single.path;
    if (ruta == null || !mounted) return;
    await intentar(context, () async {
      final res = await s.biblioteca.anadirRom(ruta);
      if (mounted) {
        avisar(context, res.yaExistia ? '«${res.juego.titulo}» ya estaba: enlazado en este dispositivo' : 'Añadido «${res.juego.titulo}»');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('DS Juntos'),
        actions: [
          IconButton(
            tooltip: 'Chat',
            icon: const Icon(Icons.chat_bubble_outline),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const PantallaChat())),
          ),
          IconButton(
            tooltip: 'Ajustes',
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const PantallaAjustes())),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _anadir,
        icon: const Icon(Icons.add),
        label: const Text('Añadir juego'),
      ),
      body: Column(
        children: [
          const BarraPareja(),
          Expanded(
            child: StreamBuilder<List<Juego>>(
              stream: s.biblioteca.juegos(),
              builder: (context, snap) {
                if (snap.hasError) return Center(child: Text(mensajeError(snap.error!)));
                if (!snap.hasData) return const Center(child: CircularProgressIndicator());
                _juegos = snap.data!;
                if (_juegos.isEmpty) {
                  return const Center(child: Text('Aún no hay juegos.\nAñadid uno con el botón de abajo.', textAlign: TextAlign.center));
                }
                return ListenableBuilder(
                  listenable: s.presencia,
                  builder: (context, _) => GridView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 180,
                      childAspectRatio: 0.72,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                    ),
                    itemCount: _juegos.length,
                    itemBuilder: (_, i) => TarjetaJuego(
                      juego: _juegos[i],
                      parejaJugando: s.presencia.pareja?.estado == Estado.jugando &&
                          s.presencia.pareja?.juego == _juegos[i].titulo,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// Quién es tu pareja, si está conectada y a qué juega; toque y Discord.
class BarraPareja extends StatelessWidget {
  const BarraPareja({super.key});

  @override
  Widget build(BuildContext context) {
    final s = Servicios.de(context);
    return ListenableBuilder(
      listenable: s.presencia,
      builder: (context, _) {
        final p = s.presencia.pareja;
        final nombre = s.sesion.pareja?.nombre ?? 'Tu pareja';
        final color = colorDesdeHex(s.sesion.pareja?.color ?? '#4F7CFF');
        final estado = s.sesion.pareja == null
            ? 'Aún no se ha unido. Pásale el código (en Ajustes).'
            : p == null
                ? 'Desconectada'
                : p.estado == Estado.jugando
                    ? 'Jugando a ${p.juego} · ${haceCuanto(p.desde)}'
                    : 'Conectada';
        return Card(
          margin: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                Stack(
                  children: [
                    CircleAvatar(backgroundColor: color, child: Text(nombre.characters.first.toUpperCase())),
                    Positioned(
                      right: 0,
                      bottom: 0,
                      child: Container(
                        width: 12,
                        height: 12,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: p == null ? Colors.grey : (p.estado == Estado.jugando ? Colors.orange : Colors.green),
                          border: Border.all(color: Theme.of(context).cardColor, width: 2),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(nombre, style: Theme.of(context).textTheme.titleMedium),
                      Text(estado, style: Theme.of(context).textTheme.bodySmall, overflow: TextOverflow.ellipsis),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Dar un toque',
                  icon: const Icon(Icons.favorite_border),
                  onPressed: () => intentar(context, () async {
                    await s.social.toque();
                    if (context.mounted) avisar(context, 'Toque enviado 💗');
                  }),
                ),
                if (s.ajustes.discordUrl.isNotEmpty)
                  IconButton(
                    tooltip: 'Llamada en Discord',
                    icon: const Icon(Icons.headset_mic_outlined),
                    onPressed: () => launchUrl(Uri.parse(s.ajustes.discordUrl), mode: LaunchMode.externalApplication),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class TarjetaJuego extends StatelessWidget {
  const TarjetaJuego({super.key, required this.juego, required this.parejaJugando});
  final Juego juego;
  final bool parejaJugando;

  @override
  Widget build(BuildContext context) {
    final s = Servicios.de(context);
    final sistema = juego.sistema;
    final rom = s.ajustes.rutaRom(juego.romSha1);
    final tema = Theme.of(context);
    return Card(
      child: InkWell(
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PantallaJuego(juego: juego))),
        onLongPress: rom == null ? null : () => jugar(context, juego),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Caratula(juego: juego, rom: rom),
                  if (parejaJugando)
                    Positioned(
                      left: 6,
                      top: 6,
                      child: Chip(
                        visualDensity: VisualDensity.compact,
                        label: Text('${s.sesion.pareja?.nombre ?? ''} juega'),
                        avatar: const Icon(Icons.sports_esports, size: 16),
                      ),
                    ),
                  if (rom == null)
                    const Positioned(right: 6, top: 6, child: Icon(Icons.link_off, size: 18)),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 6, 8, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(juego.titulo, maxLines: 2, overflow: TextOverflow.ellipsis, style: tema.textTheme.titleSmall),
                  Text('${sistema?.nombre ?? juego.sistemaId} · ${juego.modo.nombre}', style: tema.textTheme.bodySmall),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Carátula de libretro o, si no existe, una portada generada.
class Caratula extends StatelessWidget {
  const Caratula({super.key, required this.juego, this.rom});
  final Juego juego;
  final String? rom;

  @override
  Widget build(BuildContext context) {
    final sistema = juego.sistema;
    final generada = Container(
      color: Color(0xFF000000 | (juego.romSha1.hashCode & 0x7F7F7F) | 0x303030),
      alignment: Alignment.center,
      padding: const EdgeInsets.all(8),
      child: Text(
        juego.titulo,
        textAlign: TextAlign.center,
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
      ),
    );
    if (sistema == null) return generada;
    return Image.network(
      urlCaratula(sistema, rom ?? juego.titulo),
      fit: BoxFit.cover,
      errorBuilder: (_, _, _) => generada,
    );
  }
}
