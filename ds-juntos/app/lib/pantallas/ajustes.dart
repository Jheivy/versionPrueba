import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';

import '../app.dart';
import '../nucleo/lanzador.dart';
import '../servicios/ajustes_local.dart';
import '../servicios/presencia.dart';

class PantallaAjustes extends StatefulWidget {
  const PantallaAjustes({super.key});

  @override
  State<PantallaAjustes> createState() => _PantallaAjustesState();
}

class _PantallaAjustesState extends State<PantallaAjustes> {
  static const colores = ['#4F7CFF', '#E0457B', '#2BB673', '#F2994A', '#9B51E0', '#00A3BF'];
  String? _codigo;
  String? _ip;
  String _partidas = '';

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final s = Servicios.de(context);
    s.sesion.codigoPareja().then((c) => mounted ? setState(() => _codigo = c) : null);
    ipTailscale().then((ip) => mounted ? setState(() => _ip = ip) : null);
    s.ajustes.carpetaPartidas().then((c) => mounted ? setState(() => _partidas = c) : null);
  }

  Future<void> _editar(String titulo, String actual, void Function(String) guardar) async {
    final ctrl = TextEditingController(text: actual);
    final v = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(titulo),
        content: TextField(controller: ctrl, autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(c, ctrl.text.trim()), child: const Text('Guardar')),
        ],
      ),
    );
    if (v != null) setState(() => guardar(v));
  }

  @override
  Widget build(BuildContext context) {
    final s = Servicios.de(context);
    final a = s.ajustes;
    final android = plataformaActual == Plataforma.android;
    return Scaffold(
      appBar: AppBar(title: const Text('Ajustes')),
      body: ListView(
        children: [
          const _Titulo('Vosotros'),
          ListTile(
            leading: const Icon(Icons.person_outline),
            title: const Text('Tu nombre'),
            subtitle: Text(s.sesion.yo?.nombre ?? ''),
            onTap: () => _editar('Tu nombre', s.sesion.yo?.nombre ?? '', (v) {
              if (v.isNotEmpty) intentar(context, () => s.sesion.cambiarPerfil(nombre: v));
            }),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Wrap(
              spacing: 8,
              children: [
                for (final c in colores)
                  ChoiceChip(
                    label: const SizedBox(width: 8),
                    avatar: CircleAvatar(backgroundColor: colorDesdeHex(c)),
                    selected: s.sesion.yo?.color == c,
                    onSelected: (_) => intentar(context, () => s.sesion.cambiarPerfil(color: c)).then((_) => setState(() {})),
                  ),
              ],
            ),
          ),
          ListTile(
            leading: const Icon(Icons.favorite_outline),
            title: const Text('Código de pareja'),
            subtitle: Text(_codigo ?? '…'),
            trailing: const Icon(Icons.copy),
            onTap: _codigo == null ? null : () => Clipboard.setData(ClipboardData(text: _codigo!)),
          ),
          ListTile(
            leading: const Icon(Icons.headset_mic_outlined),
            title: const Text('Enlace de la llamada de Discord'),
            subtitle: Text(a.discordUrl.isEmpty ? 'Pega el enlace de vuestro canal de voz' : a.discordUrl),
            onTap: () => _editar('Enlace de Discord', a.discordUrl, (v) => a.discordUrl = v),
          ),
          const _Titulo('Jugar a distancia'),
          ListTile(
            leading: Icon(_ip == null ? Icons.wifi_off : Icons.vpn_lock),
            title: Text(_ip == null ? 'Tailscale no está conectado' : 'Tailscale: $_ip'),
            subtitle: const Text('Con Tailscale en los dos dispositivos, «Juega conmigo» conecta directo. Sin él, se usa la lista de partidas de RetroArch.'),
          ),
          const _Titulo('RetroArch en este dispositivo'),
          ListTile(
            leading: const Icon(Icons.videogame_asset_outlined),
            title: Text(android ? 'Paquete de RetroArch' : 'Programa RetroArch'),
            subtitle: Text(a.retroarch),
            onTap: () => _editar(android ? 'Paquete (com.retroarch o com.retroarch.aarch64)' : 'Ruta de RetroArch', a.retroarch, (v) => a.retroarch = v),
          ),
          if (!android)
            ListTile(
              leading: const Icon(Icons.extension_outlined),
              title: const Text('Carpeta de núcleos'),
              subtitle: Text(a.carpetaNucleos),
              onTap: () => _editar('Carpeta de núcleos', a.carpetaNucleos, (v) => a.carpetaNucleos = v),
            ),
          ListTile(
            leading: const Icon(Icons.save_outlined),
            title: const Text('Carpeta de partidas'),
            subtitle: Text(_partidas),
            onTap: () => _editar('Carpeta de partidas', _partidas, (v) {
              a.carpetaPartidasManual = v;
              _partidas = v;
            }),
          ),
          if (android)
            ListTile(
              leading: const Icon(Icons.folder_open),
              title: const Text('Permitir acceso a los archivos'),
              subtitle: const Text('Necesario para leer las partidas de RetroArch'),
              onTap: () async {
                final st = await Permission.manageExternalStorage.request();
                if (context.mounted) avisar(context, st.isGranted ? 'Permiso concedido' : 'Sin permiso: actívalo en los ajustes de Android');
              },
            ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout),
            title: const Text('Cerrar sesión'),
            onTap: () {
              Navigator.pop(context);
              s.sesion.salir();
            },
          ),
        ],
      ),
    );
  }
}

class _Titulo extends StatelessWidget {
  const _Titulo(this.texto);
  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 4),
        child: Text(texto, style: TextStyle(color: Theme.of(context).colorScheme.primary, fontWeight: FontWeight.w600)),
      );
}
