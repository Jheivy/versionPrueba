/// Utilidades de red sin dependencias de Flutter.
library;

/// Tailscale reparte direcciones del rango 100.64.0.0/10.
bool esIpTailscale(String ip) {
  final partes = ip.split('.');
  if (partes.length != 4) return false;
  final n = partes.map(int.tryParse).toList();
  if (n.any((x) => x == null || x < 0 || x > 255)) return false;
  return n[0] == 100 && n[1]! >= 64 && n[1]! <= 127;
}

/// Elige la IP de Tailscale entre las direcciones del dispositivo.
String? elegirIpTailscale(Iterable<String> direcciones) {
  for (final d in direcciones) {
    if (esIpTailscale(d)) return d;
  }
  return null;
}

/// Código de pareja: 6 letras/números sin caracteres que se confunden.
bool codigoValido(String codigo) => RegExp(r'^[A-HJ-NP-Z2-9]{6}$').hasMatch(codigo.toUpperCase());
