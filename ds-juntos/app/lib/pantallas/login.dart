import 'package:flutter/material.dart';

import '../app.dart';

class PantallaLogin extends StatefulWidget {
  const PantallaLogin({super.key});

  @override
  State<PantallaLogin> createState() => _PantallaLoginState();
}

class _PantallaLoginState extends State<PantallaLogin> {
  final _email = TextEditingController();
  final _clave = TextEditingController();
  final _nombre = TextEditingController();
  bool _registro = false;
  bool _ocupado = false;

  Future<void> _enviar() async {
    final sesion = Servicios.de(context).sesion;
    setState(() => _ocupado = true);
    final ok = await intentar(context, () async {
      if (_registro) {
        if (_nombre.text.trim().isEmpty) throw Exception('Escribe tu nombre');
        await sesion.registrarse(_email.text, _clave.text, _nombre.text);
      } else {
        await sesion.entrar(_email.text, _clave.text);
      }
    });
    if (mounted) setState(() => _ocupado = false);
    if (ok && _registro && mounted && sesion.yo == null) {
      avisar(context, 'Cuenta creada. Si Supabase pide confirmar el email, abrid el enlace y entrad.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 380),
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.all(24),
            children: [
              Text('DS Juntos', style: Theme.of(context).textTheme.headlineMedium, textAlign: TextAlign.center),
              const SizedBox(height: 4),
              const Text('Vuestra consola compartida', textAlign: TextAlign.center),
              const SizedBox(height: 28),
              if (_registro) ...[
                TextField(controller: _nombre, decoration: const InputDecoration(labelText: 'Tu nombre')),
                const SizedBox(height: 12),
              ],
              TextField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'Email'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _clave,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Contraseña'),
                onSubmitted: (_) => _enviar(),
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _ocupado ? null : _enviar,
                child: Text(_registro ? 'Crear cuenta' : 'Entrar'),
              ),
              TextButton(
                onPressed: () => setState(() => _registro = !_registro),
                child: Text(_registro ? 'Ya tengo cuenta' : 'Crear una cuenta'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
