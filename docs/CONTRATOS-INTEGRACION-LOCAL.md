# Propuesta de contrato para la aplicación local integrada

> **Dashboard actual (17-10-2026):** una cuenta sin membresia ve la estructura generica de Mi huerto y el dialogo visual de vinculacion; la API conserva 403 garden-unassigned. No hay asociacion de equipos ni permisos automaticos. [Entrega y comprobaciones](HUERTO-SIN-ASIGNACION-Y-VINCULACION-VISUAL.md). Las descripciones anteriores que sustituian todo el dashboard por Sin huerto asignado quedan como historia.

> **Etapa B vigente — registro local con cualquier correo válido.** Ya no se autoriza cada destinatario manualmente. Se mantienen casilla, verificación por código, límites y acceso únicamente desde esta computadora. Rafael confirmó su registro y código reales. Los documentos continúan pendientes y no se asigna un huerto automáticamente. 57 pruebas Django y 48 comprobaciones de navegador aprobadas para esta actualización. Ver [cambio, configuración y comprobaciones](MEJORAS-DE-ACCESO.md). C no iniciada; las notas posteriores conservan la historia de las entregas anteriores.

> **Histórico — diagnóstico del modo restringido (17-10-2026):** POST /_allauth/browser/v1/auth/signup devuelve 403 con {"status":403,"code":"email-not-authorized"} cuando el destinatario no está en la lista privada. El rechazo precede al alta, no depende de la existencia de una cuenta y no expone destinatarios permitidos. Configuración no disponible o fallo de entrega conserva 503 mail-unavailable. El frontend asocia el nuevo error al campo de correo. Solo aplica a la excepción local de B; no habilita registro público.

> **Etapa 4 verificada localmente — 17-10-2026.** Consultar [entrega vigente, arquitectura, contratos y arranque](ETAPA-4-VERIFICACION-Y-ENTREGA.md) y [evidencia actual](EVIDENCIA-ETAPA-4-LOCAL.json). 86 pruebas Django, 64 comprobaciones de acceso, 65 de dashboard, 3 aserciones de concurrencia, 18 de restauración y 15 de reinicio aprobadas. Base principal preservada; sin cambios de frontend/migraciones en esta etapa. Registro cerrado por legales pendientes; IA/ARCO/llaves y hardware real aplazados. Las notas siguientes describen etapas anteriores cuando difieren de este estado. Sin publicación ni push.

> **Etapa 3 vigente — 17-10-2026:** huerto persistido, lista/detalle de avisos y lectura por usuario conectados. Ver [contrato ejecutado y entrega](ETAPA-3-DASHBOARD-Y-CUENTA.md) y [evidencia actual](EVIDENCIA-ETAPA-3-LOCAL.json). Conserva datos ausentes, perfil propio y membresía explícita. Registro cerrado; electrónica, IA, ARCO y llaves reales pendientes. Los contratos/propuestas anteriores quedan como historia en lo que difieran de esta entrega.

> **Estado vigente: Etapa 2 — 17-10-2026.** Acceso/sesión/perfil/cambio y contratos de código/recuperación conectados a Django/allauth en el mismo origen. Gmail de pruebas con un mensaje recibido confirmado. Registro cerrado por documentos pendientes. Ver [entrega y contrato ejecutado](ETAPA-2-ACCESO-Y-CORREO.md) y [evidencia](EVIDENCIA-ETAPA-2-LOCAL.json). El resto conserva historia/propuestas; cualquier afirmación de API no montada, acceso libre, correo desactivado o backend pendiente queda sustituida en ese alcance. Huerto/avisos, IA, ARCO y llaves reales no se integran en esta etapa.

Estado: **propuesto en Etapa 0, no implementado**. Fecha 17-10-2026. Complementa [revisión actual](ETAPA-0-INTEGRACION-REAL-2026-10-17.md); cuando difiera de contratos de la maqueta, este documento expresa el objetivo nuevo, no el comportamiento de hoy.

## 1. Arquitectura y límites de confianza

Propuesta: un proceso Django en Windows sirve **el mismo dist/index.html y sus recursos**, junto con API de autenticación/dominio en un único origen de loopback. Sin duplicar dist, plantillas visuales, Node, React, Vue o una segunda aplicación.

Objetivo de URL, al autorizar integración: `http://127.0.0.1:8766/`. Hoy 8766 sigue ocupado por http.server, sirviendo el frontend estático. La sustitución de ese proceso no se hace en Etapa 0. Mantener un host/puerto canónico también en enlaces de correo; localhost y 127.0.0.1 no deben alternarse para las cookies. Django enlazado únicamente a 127.0.0.1; ALLOWED_HOSTS explícito.

Flujo propuesto: navegador (vistas/controladores y adaptadores HTTP) → Django (sesión, validación, autorización y servicios) → PostgreSQL en 127.0.0.1:5433. SMTP es otra frontera, solo saliente y autorizado. El navegador no recibe credenciales DB/SMTP/Django ni habla directamente con PostgreSQL.

Los fragmentos #huerto, #cuenta, etc. continúan siendo rutas de presentación; el servidor nunca puede autorizar basándose en un fragmento. Los recursos estáticos pueden ser públicos; las API privadas verifican identidad y membresía en cada llamada, aun con IDs manipulados o rutas directas.

Configuración local separada de producción. HTTP en loopback es una limitación de la presentación, no una evidencia de transporte cifrado ni autorización para exponer la computadora. En producción: HTTPS, cookies Secure y configuración distinta. No se promete ASVS integral bajo HTTP local.

## 2. Versiones y autoridad de autenticación

Observado en Python 3.13.7 del equipo: Django 5.2.8 y django-allauth 65.14.3 instalados en site-packages del usuario; psycopg no instalado en ese intérprete. No existe entorno/manifiesto backend en el proyecto.

La revisión del tag oficial allauth **65.14.3**, commit `d729357926074a1af64a4b881afac45db305aa16`, confirma una base compatible por requisitos declarados con Python 3.13 y Django 5.2. Eso no demuestra una instalación headless funcional o segura. El extra headless y sus dependencias, configuración, middleware, migraciones y envío no se han probado aquí.

La página oficial consultada de Django lista **5.2.18** para 5.2 LTS; la instalada 5.2.8 no se adopta como versión definitiva. El sitio allauth anuncia versiones posteriores a la instalada. En Etapa 1 revisar parches/notas, elegir y fijar versiones exactas mantenidas de Django 5.2, psycopg 3 y allauth headless compatibles, incluyendo dependencias resueltas. Revalidar este mapeo contra el tag elegido; no congelar por accidente un inventario global o copiar la documentación latest a una versión antigua.

Usar usuario por correo antes de la primera migración. El estado verificado se consulta en la biblioteca, sin campo booleano independiente que pueda contradecirla. No implementar código, hash, sesión o recuperación criptográfica propios. No activar login por código obligatorio: el código corresponde al **registro/verificación del correo**, la recuperación utiliza enlace y el acceso habitual conserva contraseña.

## 3. Configuración funcional prevista

Estas claves son propuesta para contrastar con la versión final, no settings escritos:

- AUTH_USER_MODEL=cuentas.Usuario; USERNAME_FIELD=email; sin username obligatorio.
- allauth con acceso exclusivamente por email, verificación mandatory y verificación del correo por código.
- LOGIN_BY_CODE_ENABLED=False; recuperación por enlace, no PASSWORD_RESET_BY_CODE.
- HEADLESS_ONLY=True y clientes browser; no se necesita app-client, JWT o X-Session-Token para este navegador.
- Las URLs de correo apuntan al origen local y a la vista existente de restablecimiento. No se devuelven códigos de registro al cliente.
- Registro cerrado por servidor hasta tener términos/aviso y versiones efectivas aprobados. La bandera JavaScript y la casilla no autorizan el alta.
- Caducidad de código, intentos, reenvíos, recuperación y duración de sesión se fijan en servidor. El frontend recibe solo metadatos públicos necesarios, no los secretos ni una política inventada. La ayuda actual «6 dígitos» debe coincidir con la política final.

El alta y aceptación legal deben validarse en una extensión soportada del flujo allauth **antes de guardar usuario o enviar correo**. El payload stock de signup no incluye termsAccepted/termsVersion. Revisar el punto de extensión de la versión fijada y probar también llamadas directas al endpoint allauth: un wrapper no sirve si permite saltarse la validación por otra URL. No inventar una segunda autoridad de verificación o precrear usuarios fuera del flujo.

## 4. Sesión, CSRF, respuestas y transporte

- Sesión de servidor persistida mediante Django; cookie de sesión HttpOnly, host local canónico, SameSite=Lax y ruta definida; Secure en HTTPS. La cookie de sesión no es el token CSRF.
- Bootstrap de CSRF antes de mutaciones; enviar X-CSRFToken según Django y renovar referencia después de login si rota. La entrega concreta puede ser cookie CSRF legible de propósito limitado o bootstrap, sin revelar cookie HttpOnly.
- Fetch del mismo origen con credentials same-origin y AbortSignal. No CORS abierto, csrf_exempt propio o JWT en localStorage.
- No decidir sesión por response.ok aislado. Allauth devuelve status HTTP, data, meta.is_authenticated, flows/errors. Un 401 puede describir estado anónimo o flujo de verificación pendiente; un 409, conflicto de flujo. Traducción depende de operación/cuerpo válido.
- GET /_allauth/browser/v1/auth/session restaura identidad al inicio/recarga. Mientras se consulta, no pedir garden/notices ni renderizar datos de otra sesión. Una falla de red no es «no hay cuenta».
- Ante sesión perdida: abortar consultas privadas, limpiar DOM/contexto/datos previos y dirigir a acceso; no retener perfiles/lecturas con la nueva cuenta.
- Sin sesión: 401; con sesión sin permiso: 403; recurso ajeno o inexistente: respuesta neutral 404 cuando se haya acordado para IDs, sin filtrar su existencia.
- Errores de campos 400; conflicto 409; límite 429 y Retry-After válido; servicio 5xx/red/timeout: error comprensible y reintento controlado, nunca éxito/vacío.
- Operaciones idempotentes: cerrar sesión y marcar leído pueden repetirse sin efectos adicionales. Registro, reenvío y envío de correo no se repiten automáticamente tras timeout; la cancelación del navegador no revierte una transacción ni prueba que el servidor no procesó la solicitud.
- Respuestas de API privadas y recuperación: Cache-Control:no-store; logs saneados sin cuerpos sensibles, contraseñas, códigos, cookies, tokens o claves de enlaces.

Los estados semánticos del frontend son una **capa de adaptación**; no se exige que allauth implemente el JSON antiguo. Datos desconocidos/incompletos deben dar error sin sesión, acuse o valores inventados.

## 5. Matriz de acciones de acceso

La ruta de transporte de esta tabla se verificó en el OpenAPI/tag 65.14.3 como referencia; ninguna API está montada en la aplicación actual. La versión futura fijada exige retest. No enviar confirmation de contraseña al transporte.

| Acción actual → ruta propuesta | Entrada y respuesta para las vistas | Permiso / persistencia / errores |
| --- | --- | --- |
| sesión nueva, GET /_allauth/browser/v1/auth/session | Sin ID de usuario. Adaptar meta/data a authenticated o anonymous/verification-required; consultar membresía aparte | Cookie válida; sesión servidor. 401 anónimo/flujo pendiente según cuerpo, 410 sesión expirada; red/JSON inválido se distinguen |
| login, POST /_allauth/browser/v1/auth/login | {email,password}. authenticated solo cuando biblioteca confirma sesión; credenciales erróneas → invalid-credentials; correo pendiente → verification-required | Público con CSRF/límites; contraseña nunca persistida en claro; rota sesión; no crear membresía. No convertir todo 401 en contraseña errónea |
| register, POST /_allauth/browser/v1/auth/signup con extensión legal soportada | {email,password,termsAccepted:true,termsVersion,privacyVersion}. accepted/verification-required neutro, nunca código. Los IDs de documento son versiones efectivas, no null | Alta habilitada, políticas y versiones validadas antes de efectos. Persistir usuario pendiente vía biblioteca y aceptación mínima en transacción; envío tras commit según estrategia. Duplicados sin enumeración; terms-required, legal-version-changed, registration-disabled, password-rejected, limited |
| verify, POST /_allauth/browser/v1/auth/email/verify | Adaptar code → {key:code} en referencia 65.14.3. El proceso/destinatario los vincula la sesión pendiente; no confiar en email editable/challengeId del cliente | Biblioteca valida, caduca, limita y consume; sin proceso válido no comprobar un código global. Actualiza autoridad EmailAddress; sesión solo si la biblioteca la establece. incorrect-code/expired-process/limited/unavailable sin omisión |
| resend, POST /_allauth/browser/v1/auth/email/verify/resend | Referencia 65.14.3 liga reenvío al proceso; no cuerpo con dirección arbitraria. accepted y cooldown público, no previewCode | Proceso pendiente, destino validado por servidor, límites por cuenta/proceso/origen. Invalidación/vigencia de código anterior de la biblioteca, no frontend. 409 proceso ausente, 429 límite |
| request-reset, POST /_allauth/browser/v1/auth/password/request | {email}. Mensaje neutro si la solicitud se admite, sin token/código. No botón para continuar sin abrir correo | Público CSRF/límites; correo real solo al destinatario. Fallos de proveedor tratados sin revelar existencia de cuenta; no guardar email en storage |
| inspect-reset, GET /_allauth/browser/v1/auth/password/reset | La especificación usa X-Password-Reset-Key. Adaptar el token del fragmento al encabezado; no crear otro verificador | Biblioteca valida propósito/vigencia; GET no cambia contraseña. reset-valid/invalid-link/expired-link o indisponibilidad. Nunca loggear encabezado, fragmento o contenido del correo |
| reset, POST /_allauth/browser/v1/auth/password/reset | {key:token,password}. Revalidar al mutar; éxito solo por respuesta válida, luego ofrecer login | CSRF/proceso protegido; contraseña de biblioteca; consumo/invalidación según flujo probado. Un GET previo no garantiza POST válido. Restablecimiento no concede membresía; definir/revisar invalidación de sesiones |
| change-password, POST /_allauth/browser/v1/account/password/change | Adaptar currentPassword → current_password, password → new_password | Sesión de cuenta activa/verificada; exigir contraseña actual y validadores; no aceptar otro user_id. Política de sesiones y reautenticación por acordar. password-changed solo tras resultado verificado |
| logout, DELETE /_allauth/browser/v1/auth/session | Sin datos. accepted solo al confirmar destrucción/estado anónimo; borrar datos locales y regresar a acceso | CSRF y sesión. En el contrato 65.14.3 el DELETE puede devolver 401 con estado anónimo como resultado esperado; adaptar operación/cuerpo, no success=2xx. Error de red no debe afirmar cierre servidor |

El frontend actual conserva challengeId, expiresAt y tiempos en memoria. Al integrar, no reconstruir una tabla propia de desafíos para encajar ese contrato: usar el proceso pendiente de allauth y adaptar o retirar únicamente ese contexto. Hay que probar reanudación tras recarga y apertura del enlace en otro contexto, sin aceptar un email declarado como identidad.

La inspección del código instalado confirma que VerifyEmailInput.key compara el código cuando hay proceso de verificación; no confundirlo con login-by-code. No habilitar passkeys automáticamente porque la biblioteca las soporte.

### Documentos y aceptación

Nueva consulta propuesta GET /api/legal/documents: habilitación del alta, documentos/versiones efectivas y contenido aprobado o referencias a las rutas legales existentes. Sin documentos aprobados: registrationAllowed=false, versiones ausentes y rechazo de signup en servidor. La respuesta no convierte borradores en definitivos.

Propuesta de evidencia mínima: cuenta/proceso, versión de términos y aviso consultable, fecha servidor, acción de aceptación; no usar datos técnicos adicionales como IP o agente por defecto sin necesidad/retención aprobadas. Consultar el aviso no equivale a consentimiento genérico de todos los tratamientos. La tabla de aceptaciones no está aún en el borrador de BD.

## 6. Dominio: cuenta, membresía, huerto y avisos

Rutas /api siguientes son **propuestas propias**, no endpoints allauth existentes.

| Acción → endpoint | Entrada/respuesta | Permiso, persistencia, errores |
| --- | --- | --- |
| profile → GET /api/me | Sin ID externo. {status:ready,email,verified}; verified desde allauth | Solo cuenta de sesión; no requiere membresía para Mi cuenta. 401 o fallo real; no perfil ready con null como sustituto permanente |
| asignación inicial de membresía → comando administrativo controlado | Identidad/huerto explícitos desde operador autorizado; no botón nuevo en frontend | Solo operación administrativa Rafael; membresía única activa; no señal post_save que agregue todas las cuentas |
| garden → GET /api/huertos/actual | Sin selección de otro propietario. Devuelve forma garden vigente; fechas ISO/nulos, números finitos. Sin lecturas: waiting, values:null, tank.state:unknown, updatedAt:null | Sesión activa, correo verificado y membresía activa al huerto. Sin asignación: 403 code:garden-unassigned → estado unassigned. Sin sesión 401. No devolver ni nombre/ID del huerto a la cuenta no autorizada |
| notices → GET /api/huertos/actual/avisos | {status:ready,items:[]} es vacío válido. Filtros actuales son locales y deben operar sobre conjunto completo o paginación explícita futura | Misma membresía. Solo avisos reales persistidos. Sin filas no es error. Fallo de DB/API no es items vacío con éxito |
| detalle de aviso → GET /api/huertos/actual/avisos/:id si se adopta paginación | Mismos campos del detalle actual; inicialmente puede resolverse de lista completa como hoy | Resolver aviso dentro del huerto autorizado; recurso ajeno/inexistente 404 neutro. No filtrar un ID global antes de comprobar relación |
| mark-read → PUT /api/huertos/actual/avisos/:id/lectura | Sin usuario declarado; accepted/read:true, solo tras commit | Membresía + aviso propio; AvisoLeido único por aviso/usuario, fecha servidor; idempotente/concurrente. Leer no resuelve ni crea alerta |
| asistente | No endpoint en este hito | Aplazado; mantener estado informativo, sin respuestas estáticas disfrazadas de API |

Verificar correo **no concede huerto**. Una cuenta verificada sin membresía puede ver perfil, cambiar contraseña y cerrar sesión; garden/notices deben denegarse. Una cuenta no verificada no obtiene acceso por conocer #huerto o un ID. La comprobación de membresía no depende del rol SQL ni del JavaScript.

Campos de garden se mantienen: tres entradas plants con id 1–3 y reading:{value,quality,at}; temperature y humidity independientes; tank:{state,at}; name y updatedAt. quality missing/invalid/valid y fechas reales por lectura. Sin historial no aplicar umbral offline/stale ficticio. Los límites temporales requieren frecuencia de reporte acordada.

Contrato futuro de lecturas: DHT22 entrega temperatura/humedad (dos canales); tres sondas de sustrato son índices calibrados; flotador informa low/not-low/unknown, nunca litros ni 0/100 %. Estados y fechas de medición, recepción y última comunicación no son intercambiables. El adaptador conserva plant.id 1–3 como presentación y el servidor resuelve las zonas propias; ese número no autoriza la consulta.

Avisos: id, title, description, recommendation, zone, createdAt, resolvedAt, importance, condition, read. Propuesta de mapeo de borrador: critico→high, advertencia→medium, informacion→info; resuelto_en determina resolved. Revisar antes de usar: una severidad inválida debe rechazarse, no convertirse silenciosamente en informativa.

## 7. Acciones aplazadas y transiciones

| Grupo | Acciones frontend localizadas | Contrato de esta etapa |
| --- | --- | --- |
| ARCO | arco-create, arco-list, arco-detail, arco-add-info; folios, historial, aclaraciones | Sin backend ni acuse real aquí. Responsable, acreditación, relación autorizada, retención y navegación pendientes. No usar email/folio como contraseña |
| Llaves | passkey-list, register-begin/finish, login-begin/finish, revoke; interacción y oferta | Decisión de alcance pendiente. No interpretar response.demonstration como credencial; sin captura biométrica, PIN propio ni WebAuthn en este turno |
| IA | Entrada Asistente, menciones públicas | Etapa posterior con proveedor/API y reglas de datos. Sin respuesta prefabricada ni acceso a actuadores |
| IoT/actuación | Métricas y mensajes públicos de automatización; no hay botón de bomba actual | Sin ingesta, simulación o nuevos controles; contrato de dispositivo por acordar antes de endpoints |

Antes de Etapa 3 aprobar cómo presentar la indisponibilidad de estos apartados manteniendo la navegación principal. No mantener la composición de desarrollo para hacerlos parecer operativos.

## 8. Pruebas de contrato futuras mínimas

1. Bootstrap/CSRF, login correcto/incorrecto y sesión pendiente; acceso por ruta directa sin sesión denegado.
2. Signup con legales deshabilitados/versiones cambiadas rechazado incluso llamando directamente a allauth; sin correo ni cuenta parcial por ese rechazo.
3. Código correcto/incorrecto/vencido, reuso y reenvío; nunca en JSON/logs; recarga no verifica por sí sola.
4. Recuperación realmente entregada a cuenta autorizada; enlace local, caducidad/uso, key falsa y doble envío; sin acceso alternativo.
5. Cookies/rotación/cierre/cambio de contraseña e invalidación según política; perfil nunca de otro usuario.
6. Cuenta verificada sin membresía frente a cuenta asignada, para cada consulta/mutación; ID de aviso ajeno denegado.
7. Estado sin lecturas y lista vacía válidos frente a error de servicio; null no 0; persistencia tras reiniciar.
8. Ningún script desarrollo cargado, código fijo, interacción demonstration o almacenamiento de credenciales. No probar estas expectativas contra los mocks como si fueran backend.
9. Roles de DB y permisos estructurales/DML comprobados con conexiones reales separadas, en base de pruebas preprovisionada y aislada.
10. Movilidad/teclado de las vistas conservadas; revisar solo los cambios de comportamiento autorizados.

## 9. Fuentes primarias consultadas

- [Django 5.2, usuario personalizado](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/) y [CSRF](https://docs.djangoproject.com/en/5.2/ref/csrf/).
- [Descarga/mantenimiento Django](https://www.djangoproject.com/download/) y [notas 5.2.18](https://docs.djangoproject.com/en/5.2/releases/5.2.18/).
- [allauth 65.14.3: requisitos](https://github.com/pennersr/django-allauth/blob/65.14.3/docs/installation/requirements.rst), [instalación headless](https://github.com/pennersr/django-allauth/blob/65.14.3/docs/headless/installation.rst), [configuración headless](https://github.com/pennersr/django-allauth/blob/65.14.3/docs/headless/configuration.rst).
- [OpenAPI fijado 65.14.3](https://github.com/pennersr/django-allauth/blob/65.14.3/allauth/headless/spec/doc/openapi.yaml), [VerifyEmail/ResetPassword inputs](https://github.com/pennersr/django-allauth/blob/65.14.3/allauth/headless/account/inputs.py) y [respuestas de autenticación](https://github.com/pennersr/django-allauth/blob/65.14.3/allauth/headless/base/response.py).
- [Notas actuales allauth](https://docs.allauth.org/en/latest/release-notes/): referencia para revisar actualizaciones, no contrato de la instalada.

Fecha de consulta: 17-10-2026. Compatibilidad declarada, fuentes y contratos no sustituyen instalación, migraciones o pruebas reales de Etapa 1–4.
