# Implementación de seguridad — etapa 4

> Matriz de la integración inicial. El contraste con la redacción más reciente del diseño y con requisitos/amenazas corregidos está pendiente de recibir esos documentos. No se presume aprobación formal. Véase [cierre-entrega.md](cierre-entrega.md).

27 de octubre de 2026. Base: diseño web v1.0 del mismo día, identificado como «para revisión del equipo»; no se inventa aprobación humana. Se conservan las decisiones confirmadas y el paquete PostgreSQL validado. La propuesta de 30 minutos de inactividad no se activa; permanecen ocho horas de sesión y cierre de navegador según el contrato.

## Habilidades y alcance

`sdlc-seguro` condujo la etapa 4, con las referencias 04 Desarrollo y 05 Pruebas. `ssdf-practicas` y `asvs-requisitos` se aplicaron únicamente a integración web. Se conserva NIST SSDF 1.1 y OWASP ASVS 5.0.0; no se realiza una auditoría integral ni se añaden otros marcos.

## Decisiones y evidencia

| Diseño | Implementación | Evidencia y límite | Referencias seleccionadas |
|---|---|---|---|
| D01 cuentas/sesiones | `cuentas/api.py`, inputs exactos y allauth; 15–256 puntos de código, seis dígitos/600s/3fallos/60s/5reenvíos; recuperación1800s; sesión28800s | `tests/test_auth.py`: flujos HTTP con correo en memoria, sesión/recuperación/logout. No SMTP real | ASVS5.0.0-6.2.1,6.2.8,6.2.9; SSDF PW.1.3,PW.8.2 |
| D02 autorización | Actor de sesión; `datos/services.py`; membresía activa y cuatro capacidades explícitas. Sin atajos staff/superuser | Tests HTTP usuario/otro recurso/capacidades, pruebas de servicios y runtime | ASVS5.0.0-8.2.1,8.2.2,8.3.1,8.3.2 |
| D03 presentación/datos | Adaptadores reales, salida escapada, IDs bigint como cadenas, null preservado; CSP script-src self | Pruebas de adaptadores y navegador; CSP admite estilos inline heredados para conservar aspecto, no scripts inline | ASVS5.0.0, capítulos V1/V3/V14 citados por D03; no se atribuye cobertura completa de esos capítulos |
| D04 API | CSRF, JSON estricto, límites de tamaño, campos permitidos, sin cambios por GET, errores neutros, ORM | Pruebas HTTP positivas/negativas; no cuerpos ni secretos en logs de peticiones | ASVS5.0.0-1.2.4,15.3.3; SSDF PW.5.1 |
| D05 persistencia | Migraciones históricas preservadas, nuevas de datos y `web.0001`; rol runtime limitado | Instalación/migraciones coherentes y HTTP con runtime, denegaciones de DDL/TRUNCATE/historial | ASVS5.0.0-13.2.2; SSDF PW.9.1,PW.9.2 |
| D06 soporte | Servicios transaccionales existentes, token43 exacto, verificador HMAC, consentimiento, caso/recurso/alcance/24h/revocación. Logout cierra sesiones incluso al perder elegibilidad, sin revocar permiso | Regresiones de servicios y HTTP; no hardware. Cambiar caso/cerrar consola usa cierre técnico | ASVS5.0.0-8.3.2,15.4.2,15.4.3,16.2.1,16.2.5,16.4.2 |
| D07 operación | Secretos externos, correo local protegido, SMTP opt-in, configuración HTTPS separada, imagen PostgreSQL por digest | No se probaron TLS/VM/SMTP real ni recuperación de producción; referencia del respaldo previo limitada a su ensayo sintético | SSDF PW.9.1,PW.9.2,PS.3.1 |

Las referencias de la capa de datos se conservan en `../referencias/capa-datos/evidencias/referencias-seguridad.md`. Identificadores REQ/AM del diseño se tratan como referencias del documento, no como requisitos nuevos inventados ni controles certificados.

## Adaptaciones técnicas de esta integración

- Idempotencia persistente por actor, UUID, ruta y huella HMAC del cuerpo. La misma clave no repite una mutación; otro cuerpo devuelve409. El registro solo permite SELECT/INSERT al runtime. Una respuesta repetida es **recibo histórico**, no prueba de vigencia actual de una autorización. Los replays vuelven a comprobar cuenta, capacidad y recurso pertinente.
- Los tokens de soporte no se guardan en respuestas idempotentes. El reintento devuelve token:null: si el primer secreto se perdió, el usuario revoca/emite otra autorización. No se recupera de la base ni del navegador persistente.
- Las cuotas adicionales son decisiones técnicas locales: 15 escrituras técnicas por minuto y usuario; 60 restantes por minuto y usuario. Ventana fija y contador compartido serializado mediante bloqueo transaccional PostgreSQL. Los límites allauth compatibles se conservan en configuración; no se afirma limitación universal de toda superficie.
- Listados de mantenimiento/avisos/solicitudes/casos paginan25 elementos desde la consulta; flota y publicaciones devuelven hasta100. No se descargan listas completas para que JavaScript aplique autorización.
- Recuperación de contraseña conserva la respuesta de estado no autenticado de allauth tras el cambio; la interfaz reconoce éxito únicamente si no hay errores, sin iniciar sesión.
- El cierre técnico usa exclusivamente identidad de sesión del servidor. La pérdida de verificación/actividad no impide la limpieza irreversible durante logout; no concede acceso ni reabre sesiones.

## Configuración y límites

Mismo origen, sesiones de servidor, CSRF también en los endpoints allauth browser. Cookies HttpOnly/SameSite=Lax; Secure únicamente bajo el perfil HTTPS de despliegue. La excepción HTTP local se limita a loopback y no modifica el perfil de entrega HTTPS. No hay JWT, CORS abierto, segundo sistema de autenticación ni RLS. Un proceso comprometido con credenciales runtime queda fuera del aislamiento de autorización Django.

Fuera: políticas/ARCO, WebAuthn, sensores/MQTT, IA, reinicios y despliegues reales. El diseño general aún requiere revisión humana independiente (SSDF PW.2.1); esta implementación no la suplanta.

## Fuentes técnicas consultadas

- Django5.2: https://docs.djangoproject.com/en/5.2/howto/csrf/ y código instalado de sesiones/migraciones.
- allauth: guía oficial https://docs.allauth.org/en/latest/headless/installation.html como orientación; comportamiento contrastado con **65.20.0 instalado**, no supuesto por latest.
- PostgreSQL17: https://www.postgresql.org/docs/17/ddl-priv.html.
- Versiones SSDF/ASVS: las fijadas y verificadas en las referencias previas del proyecto. No se cambian por publicaciones posteriores.
