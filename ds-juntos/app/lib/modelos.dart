import 'nucleo/sistemas.dart';

class Perfil {
  const Perfil({required this.id, required this.nombre, required this.color, this.parejaId});
  final String id;
  final String nombre;
  final String color;
  final String? parejaId;

  factory Perfil.desdeMapa(Map<String, dynamic> m) => Perfil(
        id: m['id'] as String,
        nombre: m['nombre'] as String,
        color: (m['color'] as String?) ?? '#4F7CFF',
        parejaId: m['pareja_id'] as String?,
      );
}

class Juego {
  const Juego({
    required this.id,
    required this.titulo,
    required this.sistemaId,
    required this.romSha1,
    required this.modo,
  });
  final String id;
  final String titulo;
  final String sistemaId;
  final String romSha1;
  final ModoJuntos modo;

  Sistema? get sistema => sistemaPorId(sistemaId);

  factory Juego.desdeMapa(Map<String, dynamic> m) => Juego(
        id: m['id'] as String,
        titulo: m['titulo'] as String,
        sistemaId: m['sistema'] as String,
        romSha1: m['rom_sha1'] as String,
        modo: ModoJuntos.desdeId(m['modo_juntos'] as String),
      );
}

class EstadoPartida {
  const EstadoPartida({
    required this.juegoId,
    this.sha1,
    this.version = 0,
    this.subidaPor,
    this.actualizada,
    this.bloqueadaPor,
    this.bloqueadaHasta,
  });
  final String juegoId;
  final String? sha1;
  final int version;
  final String? subidaPor;
  final DateTime? actualizada;
  final String? bloqueadaPor;
  final DateTime? bloqueadaHasta;

  /// Bloqueada por otra persona y el candado no ha caducado.
  bool bloqueadaPorOtro(String yo) =>
      bloqueadaPor != null && bloqueadaPor != yo && (bloqueadaHasta?.isAfter(DateTime.now()) ?? false);

  factory EstadoPartida.desdeMapa(Map<String, dynamic> m) => EstadoPartida(
        juegoId: m['juego_id'] as String,
        sha1: m['sha1'] as String?,
        version: (m['version'] as num?)?.toInt() ?? 0,
        subidaPor: m['subida_por'] as String?,
        actualizada: DateTime.tryParse('${m['actualizada']}'),
        bloqueadaPor: m['bloqueada_por'] as String?,
        bloqueadaHasta: DateTime.tryParse('${m['bloqueada_hasta']}'),
      );
}

enum Estado { conectada, jugando }

class Presencia {
  const Presencia({
    required this.userId,
    required this.nombre,
    required this.estado,
    required this.desde,
    this.juego,
    this.ip,
  });
  final String userId;
  final String nombre;
  final Estado estado;
  final DateTime desde;
  final String? juego;
  final String? ip;

  Map<String, dynamic> aMapa() => {
        'user_id': userId,
        'nombre': nombre,
        'estado': estado.name,
        'desde': desde.toIso8601String(),
        'juego': juego,
        'ip': ip,
      };

  factory Presencia.desdeMapa(Map<String, dynamic> m) => Presencia(
        userId: '${m['user_id']}',
        nombre: '${m['nombre'] ?? ''}',
        estado: m['estado'] == 'jugando' ? Estado.jugando : Estado.conectada,
        desde: DateTime.tryParse('${m['desde']}') ?? DateTime.now(),
        juego: m['juego'] as String?,
        ip: m['ip'] as String?,
      );
}

class Invitacion {
  const Invitacion({
    required this.id,
    required this.de,
    required this.juegoId,
    required this.estado,
    required this.creada,
    this.ipAnfitrion,
  });
  final String id;
  final String de;
  final String juegoId;
  final String estado;
  final DateTime creada;
  final String? ipAnfitrion;

  factory Invitacion.desdeMapa(Map<String, dynamic> m) => Invitacion(
        id: m['id'] as String,
        de: m['de'] as String,
        juegoId: m['juego_id'] as String,
        estado: m['estado'] as String,
        creada: DateTime.tryParse('${m['creada']}') ?? DateTime.now(),
        ipAnfitrion: m['ip_anfitrion'] as String?,
      );
}

class Mensaje {
  const Mensaje({required this.id, required this.de, required this.tipo, required this.creado, this.texto});
  final int id;
  final String de;
  final String tipo;
  final String? texto;
  final DateTime creado;

  bool get esToque => tipo == 'toque';

  factory Mensaje.desdeMapa(Map<String, dynamic> m) => Mensaje(
        id: (m['id'] as num).toInt(),
        de: m['de'] as String,
        tipo: m['tipo'] as String,
        texto: m['texto'] as String?,
        creado: DateTime.tryParse('${m['creado']}')?.toLocal() ?? DateTime.now(),
      );
}
