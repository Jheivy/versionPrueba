/// Qué hacer con una partida guardada antes y después de jugar.
library;

enum AccionSync {
  /// Las dos copias son iguales.
  nada,

  /// La copia de este dispositivo es la nueva: se sube.
  subir,

  /// La copia de la nube es la nueva: se baja.
  bajar,

  /// Las dos cambiaron desde la última sincronización: se guardan las dos
  /// y se pregunta cuál vale.
  conflicto,
}

/// Decide comparando huellas (SHA-1) del archivo local, del de la nube y
/// del último que este dispositivo sincronizó. `null` = no existe.
AccionSync decidirSync({
  required String? local,
  required String? remoto,
  required String? ultimoSincronizado,
}) {
  if (local == remoto) return AccionSync.nada;
  if (remoto == null) return AccionSync.subir;
  if (local == null) return AccionSync.bajar;
  if (local == ultimoSincronizado) return AccionSync.bajar;
  if (remoto == ultimoSincronizado) return AccionSync.subir;
  return AccionSync.conflicto;
}
