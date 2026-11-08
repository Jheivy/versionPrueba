import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../app.dart';
import '../modelos.dart';
import '../nucleo/lanzador.dart';
import '../nucleo/sistemas.dart';
import 'inicio.dart';
import 'jugar.dart';

class PantallaJuego extends StatefulWidget {
  const PantallaJuego({super.key, required this.juego});
  final Juego juego;

  @override
  State<PantallaJuego> createState() => _PantallaJuegoState();
}

class _PantallaJuegoState extends State<PantallaJuego> {
  late Juego juego = widget.juego;

  Future<void> _buscarRom() async {
    final s = Servicios.de(context);
    final r = await FilePicker.pickFiles(dialogTitle: 'Busca «${juego.titulo}»');
    final ruta = r.isEmpty ? null : r.single.path;
    if (ruta == null || !mounted) return;
    final ok = await s.biblioteca.enlazarRom(juego, ruta);
    if (!mounted) return;
    avisar(context, ok ? 'ROM enlazado' : 'Ese archivo no es el mismo juego (la huella no coincide)');
    setState(() {});
  }

  Future<void> _jugarJuntos() async {
    final s = Servicios.de(context);
    if (s.presencia.pareja == null) {
      avisar(context, '${s.sesion.pareja?.nombre ?? 'Tu pareja'} no está conectada ahora. Le llegará igual si abre la app en 10 min.');
    }
    final ok = await intentar(context, () async {
      await s.social.invitar(juego.id, s.presencia.miIp);
    });
    if (!ok || !mounted) return;
    await jugar(context, juego, netplay: juego.modo == ModoJuntos.wiimmfi ? null : const Anfitrion());
  }

  Future<void> _historial() async {
    final s = Servicios.de(context);
    final rom = s.ajustes.rutaRom(juego.romSha1);
    final versiones = await s.partidas.historial(juego.id);
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      builder: (c) => ListView(
        shrinkWrap: true,
        children: [
          const ListTile(title: Text('Versiones guardadas'), subtitle: Text('Recuperar una versión no borra la actual: también queda en el historial.')),
          if (versiones.isEmpty) const ListTile(title: Text('Todavía no hay versiones')),
          for (final v in versiones)
            ListTile(
              leading: const Icon(Icons.history),
              title: Text('Versión $v'),
              trailing: rom == null ? null : const Text('Recuperar'),
              onTap: rom == null
                  ? null
                  : () async {
                      Navigator.pop(c);
                      final ruta = await s.lanzador.rutaPartidaLocal(rom);
                      if (!mounted) return;
                      await intentar(context, () => s.partidas.restaurar(juego, v, ruta));
                      if (mounted) avisar(context, 'Versión $v recuperada');
                    },
            ),
        ],
      ),
    );
  }

  Future<void> _renombrar() async {
    final s = Servicios.de(context);
    final ctrl = TextEditingController(text: juego.titulo);
    final nuevo = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Nombre del juego'),
        content: TextField(controller: ctrl, autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(c, ctrl.text), child: const Text('Guardar')),
        ],
      ),
    );
    if (nuevo == null || nuevo.trim().isEmpty || !mounted) return;
    if (await intentar(context, () => s.biblioteca.renombrar(juego, nuevo))) {
      setState(() => juego = Juego(id: juego.id, titulo: nuevo.trim(), sistemaId: juego.sistemaId, romSha1: juego.romSha1, modo: juego.modo));
    }
  }

  Future<void> _borrar() async {
    final s = Servicios.de(context);
    final si = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text('¿Quitar «${juego.titulo}»?'),
        content: const Text('Se quita de la lista de los dos y se borra su partida de la nube. Los archivos de vuestros dispositivos no se tocan.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Quitar')),
        ],
      ),
    );
    if (si != true || !mounted) return;
    if (await intentar(context, () => s.biblioteca.borrar(juego)) && mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final s = Servicios.de(context);
    final rom = s.ajustes.rutaRom(juego.romSha1);
    final tema = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(juego.titulo),
        actions: [
          PopupMenuButton<String>(
            onSelected: (v) => v == 'renombrar' ? _renombrar() : _borrar(),
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'renombrar', child: Text('Cambiar nombre')),
              PopupMenuItem(value: 'borrar', child: Text('Quitar de la lista')),
            ],
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 120,
                height: 160,
                child: ClipRRect(borderRadius: BorderRadius.circular(8), child: Caratula(juego: juego, rom: rom)),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(juego.titulo, style: tema.textTheme.titleLarge),
                    Text(juego.sistema?.nombre ?? juego.sistemaId),
                    const SizedBox(height: 12),
                    DropdownButton<ModoJuntos>(
                      value: juego.modo,
                      isExpanded: true,
                      items: [for (final m in ModoJuntos.values) DropdownMenuItem(value: m, child: Text(m.nombre))],
                      onChanged: (m) async {
                        if (m == null) return;
                        if (await intentar(context, () => s.biblioteca.cambiarModo(juego, m))) {
                          setState(() => juego = Juego(id: juego.id, titulo: juego.titulo, sistemaId: juego.sistemaId, romSha1: juego.romSha1, modo: m));
                        }
                      },
                    ),
                    Text(juego.modo.explicacion, style: tema.textTheme.bodySmall),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          StreamBuilder<EstadoPartida?>(
            stream: s.partidas.estado(juego.id),
            builder: (context, snap) {
              final e = snap.data;
              final bloqueada = e != null && e.bloqueadaPorOtro(s.sesion.yo!.id);
              return Card(
                child: ListTile(
                  leading: Icon(bloqueada ? Icons.lock_clock : Icons.cloud_done_outlined),
                  title: Text(e?.sha1 == null ? 'Sin partida en la nube todavía' : 'Partida en la nube · versión ${e!.version}'),
                  subtitle: Text(
                    bloqueada
                        ? '${s.sesion.nombreDe(e.bloqueadaPor!)} la está usando ahora'
                        : e?.subidaPor == null
                            ? 'Se sube sola al terminar de jugar'
                            : 'Guardada por ${s.sesion.nombreDe(e!.subidaPor!)} ${haceCuanto(e.actualizada)}',
                  ),
                  trailing: TextButton(onPressed: _historial, child: const Text('Historial')),
                ),
              );
            },
          ),
          Card(
            child: ListTile(
              leading: Icon(rom == null ? Icons.link_off : Icons.sd_storage_outlined),
              title: Text(rom == null ? 'No está en este dispositivo' : 'ROM en este dispositivo'),
              subtitle: Text(rom ?? 'Busca el archivo para poder jugar aquí'),
              trailing: TextButton(onPressed: _buscarRom, child: Text(rom == null ? 'Buscar ROM' : 'Cambiar')),
            ),
          ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: rom == null ? null : () => jugar(context, juego),
            icon: const Icon(Icons.play_arrow),
            label: const Text('Jugar'),
          ),
          if (admiteJugarJuntos(juego.modo)) ...[
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: rom == null ? null : _jugarJuntos,
              icon: const Icon(Icons.favorite_outline),
              label: const Text('Juega conmigo'),
            ),
          ],
        ],
      ),
    );
  }
}
