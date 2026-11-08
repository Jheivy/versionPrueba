// Claves de vuestro proyecto de Supabase. No se escriben aquí: se pasan al
// compilar con  --dart-define-from-file=supabase.json  (ver README).
const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
const supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');

bool get configurado => supabaseUrl.isNotEmpty && supabaseAnonKey.isNotEmpty;
