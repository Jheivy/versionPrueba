import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'app.dart';
import 'config.dart';
import 'pantallas/emparejar.dart';
import 'pantallas/inicio.dart';
import 'pantallas/login.dart';
import 'servicios/ajustes_local.dart';
import 'servicios/sesion.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (!configurado) {
    runApp(const _SinConfigurar());
    return;
  }
  await Supabase.initialize(url: supabaseUrl, publishableKey: supabaseAnonKey);
  final sesion = Sesion();
  final ajustes = await AjustesLocal.cargar();
  await sesion.iniciar();
  runApp(Servicios(sesion: sesion, ajustes: ajustes, child: const DsJuntos()));
}

class DsJuntos extends StatelessWidget {
  const DsJuntos({super.key});

  @override
  Widget build(BuildContext context) {
    final sesion = Servicios.de(context).sesion;
    return MaterialApp(
      title: 'DS Juntos',
      debugShowCheckedModeBanner: false,
      theme: tema(Brightness.light),
      darkTheme: tema(Brightness.dark),
      home: ListenableBuilder(
        listenable: sesion,
        builder: (context, _) {
          if (sesion.cargando && sesion.yo == null) {
            return const Scaffold(body: Center(child: CircularProgressIndicator()));
          }
          if (sb.auth.currentUser == null) return const PantallaLogin();
          if (sesion.parejaId == null) return const PantallaEmparejar();
          return PantallaInicio(key: ValueKey(sesion.parejaId));
        },
      ),
    );
  }
}

class _SinConfigurar extends StatelessWidget {
  const _SinConfigurar();

  @override
  Widget build(BuildContext context) => MaterialApp(
        theme: tema(Brightness.light),
        home: const Scaffold(
          body: Center(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Text(
                'Falta conectar Supabase.\n\nEjecutad la app con:\n'
                'flutter run --dart-define-from-file=supabase.json\n\n'
                '(copiad supabase.example.json a supabase.json y poned vuestra URL y clave anon)',
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ),
      );
}
