import 'package:flutter/material.dart';

import '../app.dart';
import '../nucleo/red.dart';

class PantallaEmparejar extends StatefulWidget {
  const PantallaEmparejar({super.key});

  @override
  State<PantallaEmparejar> createState() => _PantallaEmparejarState();
}

class _PantallaEmparejarState extends State<PantallaEmparejar> {
  final _codigo = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final sesion = Servicios.de(context).sesion;
    return Scaffold(
      appBar: AppBar(
        title: Text('Hola, ${sesion.yo?.nombre ?? ''}'),
        actions: [IconButton(tooltip: 'Salir', onPressed: sesion.salir, icon: const Icon(Icons.logout))],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.all(24),
            children: [
              Text('Conectad vuestras cuentas', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              const Text('Uno crea la pareja y le pasa el código al otro.'),
              const SizedBox(height: 24),
              FilledButton.icon(
                icon: const Icon(Icons.favorite),
                label: const Text('Crear pareja'),
                onPressed: () => intentar(context, () async {
                  final codigo = await sesion.crearPareja();
                  if (context.mounted) avisar(context, 'Vuestro código: $codigo');
                }),
              ),
              const SizedBox(height: 32),
              TextField(
                controller: _codigo,
                textCapitalization: TextCapitalization.characters,
                maxLength: 6,
                decoration: const InputDecoration(labelText: 'Código de tu pareja'),
              ),
              OutlinedButton(
                onPressed: () {
                  if (!codigoValido(_codigo.text)) {
                    avisar(context, 'El código tiene 6 letras o números');
                    return;
                  }
                  intentar(context, () => sesion.unirse(_codigo.text));
                },
                child: const Text('Unirme'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
