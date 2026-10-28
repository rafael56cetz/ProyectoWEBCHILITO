# Cuentas y correo de la integración

27 de octubre de 2026. Componentes reutilizados: cuentas/models.py y migraciones históricas, adapter de longitud, inputs exactos, Django 5.2.18 y django-allauth 65.20.0. No se creó un algoritmo de autenticación paralelo.

Se reemplazó la excepción histórica de presentación local por registro normal habilitado desde configuración del servidor (`ELCHILITO_REGISTRATION_ENABLED`). Nunca se asignan huertos ni capacidades al registrarse. La casilla conserva la confirmación técnica con documentos pendientes; no aprueba políticas legales.

La API de cuentas acepta solo campos definidos y rechaza campos protegidos, JSON ambiguo, tipos incompatibles y cuerpos no JSON. JSON excesivamente anidado devuelve 400 y el cuerpo que supera el límite configurado devuelve 413, sin trazas. CSRF se aplica también a login, registro, recuperación y logout. Todos los errores de transporte/correo son controlados y no imprimen secretos.

`api/cuenta` usa `datos.services.session_contract`, además de consultar membresías activas. Devuelve rol y capacidades explícitas, sin bypass de staff/superuser. El frontend no decide permisos. El logout cierra las sesiones técnicas propias mediante el servicio de datos y después invalida la sesión Django; cerrar no revoca el permiso de soporte. El cierre de sesión también cierra irreversiblemente las sesiones técnicas propias si se retiró la verificación o se desactivó la cuenta. La limpieza obtiene identidad exclusivamente de la sesión Django existente y comprueba su hash cuando Django devuelve AnonymousUser por inactividad; no toma identificadores del JSON ni concede permisos. Usa el orden de bloqueos de sujetos/caso del servicio, después permiso/sesión, y guarda el cierre y su auditoría en una transacción bajo los disparadores existentes. Reactivar la cuenta no permite reutilizar esa sesión técnica cerrada.

El framework conserva código de seis dígitos, 600 segundos, tres fallos, 60 segundos entre reenvíos y cinco reenvíos sin reiniciar el plazo. Recuperación utiliza el token framework de 30 minutos, inválido tras cambiar contraseña; otra petición no revoca automáticamente enlaces previos. El restablecimiento correcto devuelve el estado no autenticado de allauth (HTTP 401 con `meta.is_authenticated=false` y sin errores de validación); el adaptador debe reconocerlo como contraseña cambiada y volver al inicio de sesión, no como fallo de la mutación. El cambio autenticado conserva la sesión actual y hace inválidas las otras según el hash de sesión. No se activa el timeout de inactividad de 30 minutos, que el diseño presenta como propuesta pendiente.

## Correo

Pruebas automatizadas: backend locmem, sin SMTP. Demostración local: `cuentas.email.ProtectedFileEmailBackend`, buzón externo a frontend con directorio 0700 y archivos 0600; contienen códigos/enlaces y no deben enviarse como evidencia ni subirse al repositorio. No se muestra el código en JSON ni en terminal.

Transporte preparado: `cuentas.email.AuthorizedSMTPBackend`. Requiere opt-in `ELCHILITO_SMTP_ENABLED=True`, configuración externa `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, TLS y lista externa `ELCHILITO_SMTP_ALLOWED_RECIPIENTS`. La selección del backend y la lista no provienen de la petición. Sin autorización/configuración falla antes de conectarse; no hay fallback a consola. Los secretos originales no se leen.

El envío real queda pendiente de destinatario expresamente autorizado y configuración por canal seguro. El buzón local acredita generación del correo de prueba, no entrega SMTP al destinatario.

## Evidencia esperada

`backend/tests/test_auth.py` contiene pruebas HTTP con PostgreSQL para registro, límites de contraseña, verificación/errores/reenvíos, recuperación, cambios, límites de frecuencia, CSRF, manipulación de campos, capacidades y logout técnico. Una prueba escrita no es resultado: consultar la evidencia de ejecución de la integración.
