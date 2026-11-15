"""Decisiones confirmadas para integrar después; este módulo no ejecuta servicios.

Importar estas constantes no basta para implementar expiración, consentimiento ni purga. La aplicación integrada conserva su configuración hasta su propio cambio."""
VERIFICACION_CORREO_SEGUNDOS = 600
RECUPERACION_CONTRASENA_SEGUNDOS = 600
SESION_ABSOLUTA_SEGUNDOS = 8 * 60 * 60
SESION_INACTIVA_USUARIO_SEGUNDOS = 30 * 60
SESION_INACTIVA_ADMIN_SEGUNDOS = 15 * 60
PREFERENCIA_COOKIES_SEGUNDOS = 180 * 24 * 60 * 60
IDENTIFICADOR_ESTADISTICAS_SEGUNDOS = 30 * 60
FINALIDAD_ESTADISTICAS = "estadisticas_internas_navegacion"
# El plazo de conservación de bitácoras todavía no está aprobado: no fijarlo aquí.
