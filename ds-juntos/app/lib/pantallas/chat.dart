import 'package:flutter/material.dart';

import '../app.dart';
import '../modelos.dart';

class PantallaChat extends StatefulWidget {
  const PantallaChat({super.key});

  @override
  State<PantallaChat> createState() => _PantallaChatState();
}

class _PantallaChatState extends State<PantallaChat> {
  final _texto = TextEditingController();

  Future<void> _enviar() async {
    final t = _texto.text.trim();
    if (t.isEmpty) return;
    _texto.clear();
    await intentar(context, () => Servicios.de(context).social.escribir(t));
  }

  @override
  Widget build(BuildContext context) {
    final s = Servicios.de(context);
    final yo = s.sesion.yo!.id;
    final esquema = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(s.sesion.pareja?.nombre ?? 'Chat')),
      body: Column(
        children: [
          Expanded(
            child: StreamBuilder<List<Mensaje>>(
              stream: s.social.mensajes(),
              builder: (context, snap) {
                final mensajes = snap.data ?? const [];
                return ListView.builder(
                  reverse: true,
                  padding: const EdgeInsets.all(12),
                  itemCount: mensajes.length,
                  itemBuilder: (_, i) {
                    final m = mensajes[i];
                    final mio = m.de == yo;
                    final hora = '${m.creado.hour.toString().padLeft(2, '0')}:${m.creado.minute.toString().padLeft(2, '0')}';
                    return Align(
                      alignment: mio ? Alignment.centerRight : Alignment.centerLeft,
                      child: Container(
                        margin: const EdgeInsets.symmetric(vertical: 3),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        constraints: const BoxConstraints(maxWidth: 320),
                        decoration: BoxDecoration(
                          color: mio ? esquema.primaryContainer : esquema.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Text(m.esToque ? '💗 toque · $hora' : '${m.texto}  ·  $hora'),
                      ),
                    );
                  },
                );
              },
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
              child: Row(
                children: [
                  IconButton(
                    tooltip: 'Toque',
                    icon: const Icon(Icons.favorite),
                    onPressed: () => intentar(context, s.social.toque),
                  ),
                  Expanded(
                    child: TextField(
                      controller: _texto,
                      decoration: const InputDecoration(hintText: 'Escribe…', border: OutlineInputBorder()),
                      onSubmitted: (_) => _enviar(),
                    ),
                  ),
                  IconButton(tooltip: 'Enviar', icon: const Icon(Icons.send), onPressed: _enviar),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
