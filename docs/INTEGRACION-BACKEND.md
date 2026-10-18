# Guía central de integración de backend y PostgreSQL

> **Etapa B vigente — registro local con cualquier correo válido.** Ya no se autoriza cada destinatario manualmente. Se mantienen casilla, verificación por código, límites y acceso únicamente desde esta computadora. Rafael confirmó su registro y código reales. Los documentos continúan pendientes y no se asigna un huerto automáticamente. 57 pruebas Django y 48 comprobaciones de navegador aprobadas para esta actualización. Ver [cambio, configuración y comprobaciones](MEJORAS-DE-ACCESO.md). C no iniciada; las notas posteriores conservan la historia de las entregas anteriores.

> **Etapa 4 verificada localmente — 17-10-2026.** Consultar [entrega vigente, arquitectura, contratos y arranque](ETAPA-4-VERIFICACION-Y-ENTREGA.md) y [evidencia actual](EVIDENCIA-ETAPA-4-LOCAL.json). 86 pruebas Django, 64 comprobaciones de acceso, 65 de dashboard, 3 aserciones de concurrencia, 18 de restauración y 15 de reinicio aprobadas. Base principal preservada; sin cambios de frontend/migraciones en esta etapa. Registro cerrado por legales pendientes; IA/ARCO/llaves y hardware real aplazados. Las notas siguientes describen etapas anteriores cuando difieren de este estado. Sin publicación ni push.

> **Etapa 3 vigente — 17-10-2026:** huerto persistido, lista/detalle de avisos y lectura por usuario conectados. Ver [contrato ejecutado y entrega](ETAPA-3-DASHBOARD-Y-CUENTA.md) y [evidencia actual](EVIDENCIA-ETAPA-3-LOCAL.json). Conserva datos ausentes, perfil propio y membresía explícita. Registro cerrado; electrónica, IA, ARCO y llaves reales pendientes. Los contratos/propuestas anteriores quedan como historia en lo que difieran de esta entrega.

> **Estado vigente: Etapa 2 — 17-10-2026.** Acceso/sesión/perfil/cambio y contratos de código/recuperación conectados a Django/allauth en el mismo origen. Gmail de pruebas con un mensaje recibido confirmado. Registro cerrado por documentos pendientes. Ver [entrega y contrato ejecutado](ETAPA-2-ACCESO-Y-CORREO.md) y [evidencia](EVIDENCIA-ETAPA-2-LOCAL.json). El resto conserva historia/propuestas; cualquier afirmación de API no montada, acceso libre, correo desactivado o backend pendiente queda sustituida en ese alcance. Huerto/avisos, IA, ARCO y llaves reales no se integran en esta etapa.

> **Etapa 1 implementada — 17-10-2026.** Ver [entrega y pruebas](ETAPA-1-DJANGO-Y-PERSISTENCIA.md) y [manual backend](../backend/README.md). Django 5.2.18/allauth 65.20.0/psycopg 3.3.6 están fijados en un entorno independiente. La base local ya tiene las migraciones, un huerto y tres zonas; no cuentas o membresías automáticas. El frontend se conserva sin conectar acceso/correo/API de pantallas: eso espera etapas 2–3. Los contratos y decisiones de Etapa 0 siguen como referencia de trabajo; las descripciones de estado anteriores deben leerse como históricas cuando difieran de esta entrega. Sin cambios de pantalla, correo real, telemetría o publicación en este turno.

> **Revisión más reciente — Etapa 0 de integración real, 17-10-2026.** Consultar [hallazgos y plan](ETAPA-0-INTEGRACION-REAL-2026-10-17.md), [contratos locales propuestos](CONTRATOS-INTEGRACION-LOCAL.md), [estado real de PostgreSQL/modelos](REVISION-POSTGRESQL-Y-MODELOS.md) y [seguridad/verificación](SEGURIDAD-Y-VERIFICACION-LOCAL.md). Django en Windows + PostgreSQL Docker ya son decisiones de Rafael; la base y roles existen, sin tablas/migraciones. El frontend local se preservó con sus modificaciones manuales y todavía carga desarrollo ficticio. Las descripciones anteriores de acceso vacío, documentos vacíos/registro bloqueado, revisión separada y Django pendiente son históricas cuando contradicen el código o la revisión actual. El texto legal redactado no tiene aprobación/versiones efectivas acreditadas. Este turno solo revisó y documentó; no implementó backend ni cambió pantallas. Las etapas siguientes esperan autorización expresa.

> Estado vigente tras organización independiente (17-10-2026): la raíz activa es `C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web`. `dist/index.html` es la única entrada y carga respuestas ficticias desde `dist/desarrollo/` con navegación libre. Las tablas siguientes describen fronteras de integración futura; ya no hay un sitio normal y otro de revisión que abrir. `AuthService`, `PrivacyService` y `AppService` continúan separados y desconectados; el arranque actual inyecta módulos de desarrollo en su lugar. Ver [organización y entrada única](ORGANIZACION-Y-ENTRADA-UNICA.md) para la composición que deberá sustituirse antes de autorizar backend. Las referencias previas a `revision/index.html` son históricas.


**Ajuste posterior al cierre, 17 de octubre de 2026 — solo frontend:** Rafael solicita recorrer el diseño sin credenciales. Las entradas principal y de revisión activan `previewNavigation:true`: enviar el formulario de acceso navega a Mi huerto incluso vacío; cerrar sesión regresa al acceso. No se llaman `login`/`logout`, no se envían o guardan los campos y no se confirma una sesión. Los contratos siguientes conservan su función para integración futura; no se han implementado servicios reales. Desactivar esta opción y establecer autenticación/autorización de servidor será imprescindible al abordar el backend. Registro, ARCO, passkeys, métricas y electrónica no cambian por este ajuste.

Revisión de ETAPA 4: 17 de octubre de 2026. Esta es la referencia vigente de contratos de las interfaces; las entregas 0–3 conservan su historia. El [cierre de la revisión](CIERRE-INTEGRACIONES-FRONTEND.md) contiene rutas, evidencia, ejecución y estado local. Ningún contrato de esta guía representa un endpoint implementado o una integración real aprobada.

**Rafael: backend. Carolina: PostgreSQL. Rafael y Gabriela: frontend y revisión visual.** Carolina conserva el trabajo del logo. Responsable de datos y aprobación de documentos/procedimientos: pendientes de designación. No se cambia Notion.

## 1. Fronteras, estado actual y acuerdos comunes

HTML/CSS/JavaScript y MVC se conservan. Los tres adaptadores de `dist/modelo/` exponen `request(action,payload,{signal})` y devuelven una promesa con respuesta semántica:

| Frontera | Estado normal actual | Integración posterior |
| --- | --- | --- |
| `AuthService`, `servicio-acceso.js` | `register` devuelve `registration-disabled`; las demás acciones, `unavailable`. Además, el controlador bloquea el alta con documentos pendientes | Acceso, registro, código, recuperación, contraseña y llaves |
| `PrivacyService`, `servicio-privacidad.js` | Siempre `unavailable`: no recepción, acuses ni expedientes | ARCO público y seguimiento autorizado |
| `AppService`, `servicio-aplicacion.js` | Huerto `waiting`, avisos `error`, perfil `ready` con correo/verificación nulos; mutaciones `unavailable` | Lecturas, avisos, perfil y cierre, según permisos |

Las pantallas privadas pueden abrirse para revisar su presentación: `canEnter` permite entrar por defecto. **La ruta, el folio, el ID, el modo de revisión o una bandera del frontend no autentican ni autorizan.** El servidor deberá comprobar identidad y autorización en cada operación. Las respuestas semánticas deben derivarse del resultado del servidor, nunca del éxito de una animación o de cambiar una variable local.

Los controladores bloquean envíos repetidos, aplican `AuthConfig.requestTimeoutMs` (actualmente 20000 ms), abortan al salir y descartan respuestas tardías. El transporte futuro debe respetar `AbortSignal`. Cancelación/timeout no prueba que el servidor no procesó una mutación: acordar idempotencia, concurrencia y consulta del resultado. Los textos se escapan antes de representarlos; esto no sustituye validación del servidor.

No existe mapeo HTTP acordado, restauración de sesión, middleware, protección de solicitudes, envío de correos o política de permisos real. Acordarlos antes del adaptador HTTP. No incluir secretos o acceso PostgreSQL en archivos de `dist/`. Python es responsabilidad del backend; Django sigue siendo propuesta pendiente, sin elección nueva en esta entrega.

### Implementado frente a pendiente

- **Implementado en interfaces:** acciones/payloads/respuestas de las tablas, normalización, estados, rutas y validaciones descritas. El arranque normal sigue desconectado.
- **Demostración local:** adaptadores y puente sintéticos inyectados explícitamente desde `revision/`, con las mismas vistas/controladores. No constituyen cuentas, sesiones, consentimiento, expedientes o credenciales reales.
- **Propuesta sin acuerdo:** endpoints, sesión/HTTP, documentos/versiones publicados, formatos/valores definitivos de políticas, idempotencia, paginación y todos los aspectos WebAuthn de producción. No activar el transporte sin resolver los pendientes correspondientes de la sección 7.

## 2. Acceso, registro y contraseña — AuthService

Respuestas comunes: `limited` con `retryAfterSeconds` positivo permite la espera presentada por el controlador; `unavailable` muestra indisponibilidad. Respuestas desconocidas caen en aviso genérico, sin confirmar éxito. Los estados específicos de sesión vencida/reautenticación de Seguridad no están implementados como un nuevo flujo en los formularios clásicos: acordar su traducción antes de integrar.

| Acción | Pantalla y disparador | Entrada enviada | Respuestas propias comprendidas | Validación/presentación frontend | Validación del servidor y acuerdo pendiente |
| --- | --- | --- | --- | --- | --- |
| `login` | `#acceso`, Iniciar sesión | `email`, `password` | `authenticated`, `invalid-credentials` | Correo recortado, formato y validez nativa; contraseña no vacía. Solo `authenticated` permite el callback hacia huerto. Sin código adicional | Credenciales, límites, sesión y permisos. Definir establecimiento/restauración/cierre de sesión y mapeo de errores (D4) |
| `register` | `#registro`, Crear cuenta | `email`, `password`, `termsAccepted` booleano | `accepted`, `password-rejected`, `terms-required`, `legal-version-changed`, `registration-disabled` | Correo, contraseña/confirmación, política suministrada y `termsAccepted === true`. Descarta confirmación antes del envío. Normal bloqueado por documentos pendientes; revisión puede mostrar el paso de código | Alta/verificación, aceptación válida de versión publicada, registro habilitado y política real. Resultado público neutral sin enumerar cuentas. Versiones/aprobación y evidencia por acordar (D1, D2, D4) |
| `verify` | `#verificar`, Verificar correo del registro | `email`, `code`, `challengeId` | `verified`, `incorrect-code`, `expired-code` | Correo y código no vacío; longitud/patrón solo si el backend configura valores. Recorta código. `verified` sin sesión deja enlace al acceso; con `sessionConfirmed === true` muestra oferta opcional de llave | Desafío asociado a operación/destinatario, caducidad, uso único, intentos y verificación efectiva. Solo declarar sesión cuando se haya establecido (D4) |
| `resend` | `#verificar`, Reenviar código | `email`, `challengeId` | `accepted` | Valida correo; espera y bloqueo según servicio. Vacía código y actualiza contexto, sin afirmar que llegó un correo | Elegibilidad, destinatario, límite de reenvío, vigencia/invalidez de desafíos previos y respuesta neutral (D4) |
| `request-reset` | `#recuperar`, Enviar enlace | `email` | `accepted` | Formato; confirmación pública neutral «Si existe una cuenta…». No autentica | Recuperación autorizada, entrega por canal acordado, límites y respuesta que no enumere cuentas (D4) |
| `inspect-reset` | Entrada `#restablecer?token=…`, automática y Reintentar | `token` | `reset-valid`, `invalid-link`, `expired-link`; otras respuestas muestran enlace no comprobable | Retira token del fragmento, mantiene solo contexto temporal; sin token muestra enlace inválido. El formulario se abre solo después de `reset-valid` | Verificar token, propósito, destinatario, vigencia y uso. Formato/transporte/caducidad por acordar (D4) |
| `reset` | Formulario habilitado de `#restablecer`, Guardar contraseña | `password`, `token` | `reset-complete`, `password-rejected`, `invalid-link`, `expired-link` | Contraseña, confirmación local y política configurada; vacía secretos al terminar. Éxito ofrece iniciar sesión | Revalidar token al mutar, política de contraseña y consumo atómico; no basta inspección previa. Definir sesiones y recuperación (D4) |
| `change-password` | `#cuenta/contrasena`, desde Cuenta/Seguridad | `currentPassword`, `password` | `password-changed`, `incorrect-current-password`, `password-rejected` | Contraseña actual no vacía, nueva/confirmación y política. Un único formulario/controlador; éxito solo tras `password-changed` | Sesión, autorización, contraseña actual, política y consecuencias sobre otras sesiones. Reautenticación/errores definitivos pendientes (D4) |

`AuthConfig` conserva longitud/política de contraseña, longitud/patrón/vigencia de código y reenvío sin aprobar (`null` o lista vacía). No representan una política de seguridad real. Registro y reenvío pueden devolver `challengeId`, `expiresAt` y `resendAfterSeconds`; el frontend solo utiliza tiempos válidos proporcionados/configurados. El servidor debe mantener sus propias comprobaciones aunque el cliente no configure una restricción.

El controlador vacía contraseñas al terminar y no envía la confirmación. El correo, el código, la aceptación y el contexto no se guardan en almacenamiento persistente. Recargar no demuestra verificación. La aceptación es distinta de consultar el aviso y no constituye consentimiento genérico para todos los tratamientos.

### Documentos y aceptación

`#terminos` y `#privacidad` usan una plantilla pública de contenido pendiente. `PrivacyModel.documents` mantiene versiones nulas y `registrationAllowed:false`. No hay servicio de documentos implementado. `termsVersion`, `privacyNoticeVersion`, consulta de publicación/política, actualización de versión y vínculo de aceptación con alta verificada son **propuestas**: no se envían ni se inventan ahora.

Antes de registros reales, aprobar responsable/contacto, textos, versiones y publicación; definir qué aceptación se acredita y cómo se conserva. El servidor debe comprobar esos datos junto con el alta. Cambiar la bandera local o usar `review:true` nunca debe habilitar un registro real sobre documentos vacíos (D1, D2, D4).

## 3. Privacidad y ARCO — PrivacyService

Rutas públicas y de cuenta se detallan en el cierre. La creación pública no debe exigir cuenta o aceptar términos del registro. La relación con una cuenta declarada por la persona no prueba titularidad. La lectura/aportación requiere autorización: **un ID o folio solo localiza**. Seguimiento sin cuenta, acreditación y representación siguen pendientes (D3).

| Acción | Pantalla y disparador | Entrada enviada | Respuesta comprendida | Validación/presentación frontend | Validación del servidor y acuerdo pendiente |
| --- | --- | --- | --- | --- | --- |
| `arco-create` | `#derechos-arco` o formulario compartido de `#cuenta/privacidad`, Enviar solicitud | `requesterName`, `contactEmail`, `right`, `description`, `accountRelation`, `requestedCorrection` | `accepted` y `receipt:{id,reference,receivedAt,state:'received'}`; `validation-error` y `fieldErrors`; sesión/indisponibilidad | Nombre libre no vacío, correo con formato, tipo válido, descripción y corrección solo para rectificación. Relación opcional. Solo acuse válido muestra recepción | Canal operativo, procedimiento, campos/límites, contacto, minimización, acreditación y protección contra abuso. Crear sin imponer cuenta, registrar recepción auténtica y resolver idempotencia (D1–D4) |
| `arco-list` | `#cuenta/privacidad`, carga/Reintentar | `{}`; sin ID de cuenta del cliente | `ready` y `items:[resumen]`; errores de sesión/permisos o indisponibilidad | Solo arreglo válido vacío confirma ausencia; no convierte un fallo en vacío. Rechaza registros/IDs duplicados | Identidad de sesión, expedientes autorizados, campos visibles y lista completa. Paginación por acordar (D3, D4) |
| `arco-detail` | `#cuenta/privacidad/solicitudes/:id`, carga/Reintentar | `{id}` | `ready` y `request:expediente`; sesión/permisos/no encontrado o indisponibilidad | ID completo válido; no consulta con barras codificadas o segmentos sobrantes. Expediente debe coincidir con ID y tener historial válido | Identidad, titularidad o representación, permisos por expediente y proyección pública del historial. No autorizar solo por folio (D3, D4) |
| `arco-add-info` | Detalle, Enviar información de requerimiento habilitado | `{id,informationRequestId,message}` | `accepted` y `request:expedienteActualizado`; `validation-error` y `fieldErrors`; errores de sesión/permisos o indisponibilidad | Mensaje no vacío; solo si estado `awaiting-information` y `canRespond === true`. Muestra únicamente historial actualizado válido | Revalidar sesión, expediente y requerimiento vigente/permitido, concurrencia, minimización e idempotencia. El cliente no decide estado (D3, D4) |

`right`: `access`, `rectification`, `cancellation`, `opposition`, `unsure`. Obligatoriedad y límites son una propuesta de interfaz pendiente del procedimiento: nombre/correo/tipo/descripción, corrección condicional; relación con cuenta opcional. Se recortan espacios, sin patrón arbitrario para nombres. Opcionales vacíos viajan como `''`; corrección se vacía al elegir otro derecho. No se piden términos, identificaciones, documentos, fotografías, firmas, contraseña o archivos.

Resumen: `{id,reference,right,state,receivedAt,updatedAt,publicSummary?}`. Expediente añade `history:[{state,at,publicMessage}]` no vacío e `informationRequest?:{id,message,canRespond:boolean}`. Fechas como texto ISO con fecha/hora interpretable; zona/precisión definitivas pendientes. Los ID de transporte de esta interfaz admiten 1–128 caracteres ASCII alfanuméricos, guion o guion bajo. No es un formato para nombres personales ni una prueba de autorización.

Estados provisionales: `received`, `awaiting-information`, `in-review`, `responded`. No son plazos, aprobación automática o borrado inmediato. El acuse necesita ID válido, folio de texto no vacío, fecha válida y `received`. Un `accepted` incompleto no confirma recepción. `fieldErrors` admite solo nombres de campos conocidos (solo `message` en aclaración), con mensajes escapados, errores asociados y foco.

`unauthenticated`, `forbidden` y `not-found` mantienen su distinción en lista/detalle y aportación. En creación, sesión vencida tiene aviso propio y los demás fallos son indisponibilidad. Respuestas desconocidas, error de conexión, datos incompletos, `limited` o `conflict` se presentan como indisponibilidad: su tratamiento específico sigue pendiente. Ninguno confirma recepción o vacío.

## 4. Seguridad y llaves — AuthService

Las seis acciones mantienen la frontera de autenticación. La interfaz normal no tiene interacción con el dispositivo; incluso un `begin` preparado no finaliza una operación. No se invoca ninguna API de creación/obtención de credenciales, no se captura biometría ni PIN y no se imitan diálogos del sistema.

| Acción | Pantalla y disparador | Entrada enviada | Respuesta válida | Validación/presentación frontend | Validación del servidor y acuerdo pendiente |
| --- | --- | --- | --- | --- | --- |
| `passkey-list` | `#cuenta/seguridad`, carga/Consultar lista | `{}` | `ready` y `items:[{id,name?,createdAt?,lastUsedAt?}]` | Lista válida; solo arreglo vacío confirma ausencia. Metadatos nulos/ausentes se muestran como falta de información, no nombre/fecha inventados | Identidad, autorización y llaves propias visibles. Lista completa/consistencia después de mutación por acordar (D4, D5) |
| `passkey-register-begin` | Seguridad u oferta tras verificación, Crear llave | `{}`; no se pide nombre ahora | `ready`, `operationId`, `expiresAt`; opciones públicas futuras todavía no utilizadas | ID opaco no vacío, sin espacios/control; fecha futura válida. Sin puente demostrativo explícito no pasa a finalizar | Sesión, correo verificado, reautenticación y recuperación según política aprobada; emitir operación ligada a propósito/cuenta (D4, D5) |
| `passkey-register-finish` | Creación, después de interacción **solo demostrativa** | `{operationId,response}` | `created` y `credential:{id,name?,createdAt?,lastUsedAt?}` | Respuesta de interacción sintética identificada; operación vigente y metadato válido. Después consulta la lista | Verificador y respuesta de autenticador de producción por acordar; validar desafío/propósito y autorización, rechazar mensajes sintéticos, guardar únicamente material permitido (D4, D5) |
| `passkey-login-begin` | `#acceso`, Acceder con llave | `{}`; no utiliza correo/contraseña del formulario | `ready`, `operationId`, `expiresAt` | Preparación independiente, bloqueo de envíos concurrentes. Sin enumerar existencia de cuenta o llaves | Contexto descubrible/de correo por acordar, operación caducable de un uso, límites y respuesta neutral (D4, D5) |
| `passkey-login-finish` | Acceso, después de interacción **solo demostrativa** | `{operationId,response}` | `authenticated` y `sessionConfirmed:true` | Ambos valores exactos antes de ofrecer Continuar a Mi huerto; error/cancelación permite volver al correo | Verificar autenticación de producción y establecer sesión autorizada antes de confirmar. Contrato/verificador pendientes (D4, D5) |
| `passkey-revoke` | Seguridad, Quitar llave y confirmación explícita | `{id}` | `revoked` e `id` coincidente | Conserva elemento hasta confirmación válida; luego consulta lista. Confirmación dentro de la página, sin imitar ventana del dispositivo | Propiedad, sesión, reautenticación y recuperación requeridas; autorización, concurrencia e idempotencia antes de revocar (D4, D5) |

`name`, `createdAt` y `lastUsedAt` pueden faltar o ser nulos. Fechas presentes deben ser interpretables; nombres no vacíos se presentan tal como llegan, escapados. Un dato ausente no significa «nunca usada». No se asocia necesariamente una llave con un único aparato. Nombre opcional de la propuesta, formato de ID y fechas, opciones públicas y serialización definitivos siguen pendientes.

Estados comprendidos: `error`, `unavailable`, `unauthenticated`, `reauthentication-required`, `recovery-required`, `verification-required`, `cancelled`, `not-supported`, `expired-operation`, `rejected`. Respuestas desconocidas, `invalid-response`, límites/conflictos y confirmaciones incompletas producen error genérico, no éxito o vacío. Reautenticación/recuperación son avisos de bloqueo preparados; no implementan procedimientos o política nueva. Un fallo al recargar la lista tras una mutación confirmada no se sustituye por una lista inventada.

### Puente de revisión: no es un protocolo de producción

Solo `revision/index.html` inyecta `review:true` y `passkeyInteraction`. El puente devuelve `{status:'completed',response:{demonstration:true,operationId,purpose}}` o un estado de cancelación/error. **Ese objeto no es una respuesta WebAuthn serializada y debe rechazarse en producción.** Conserva únicamente el lugar conceptual `response` de la propuesta; integrar una función real exige acordar y reemplazar este mecanismo, con autorización posterior.

El adaptador sintético relaciona ID/propósito y utiliza una caducidad ficticia de un minuto, sin fijar política real. Sus nombres/fechas son muestras. Ningún parámetro de URL habilita la revisión. Los estados de espera no usan huella, rostro, PIN o una credencial real.

La oferta vive en el controlador después de `verified` y `sessionConfirmed === true`, sin ruta para forzarla ni condición persistida. «Ahora no» cancela si procede y continúa al huerto. No se pide autenticarse en cada pantalla. El acceso clásico permanece disponible; el código verifica el registro y la recuperación conserva el enlace.

## 5. Aplicación existente — AppService, inventario congelado

Esta sección conserva los contratos del código existente; no actualiza electrónica o métricas. Ninguna apertura de pantalla demuestra sesión real. El servidor deberá autorizar cada consulta/mutación; los errores de sesión/permisos aún no tienen un flujo específico en estas vistas, por lo que se debe acordar su traducción (D4). Cambios de datos IoT dependen del documento definitivo de electrónica (D6).

| Acción | Pantalla/disparador | Entrada | Respuesta comprendida | Frontend | Servidor / pendiente |
| --- | --- | --- | --- | --- | --- |
| `garden` | `#huerto`, carga/Reintentar | `{}` | Estado/datos de huerto del inventario inferior | Normaliza tres plantas, lecturas/calidad, ausencias y nivel; desconocido produce error | Sesión, permisos de huerto, procedencia/calidad/fecha de lecturas. Contrato definitivo congelado hasta D6 |
| `notices` | `#avisos` y `#avisos/:id`, carga/Reintentar | `{}` | `ready`, `empty`, `loading`, `error`, con `items` | Filtros locales, detalle por ID dentro del arreglo, normalización de campos existentes | Sesión, avisos autorizados e información visible; definir consulta/paginación de detalle (D4, D6) |
| `profile` | `#cuenta`, carga/Reintentar | `{}` | `ready` con `email`/`verified`; otros estados se normalizan a error | Correo de texto o nulo, verificación booleana o nula. No permite editar correo | Perfil de la sesión, no un ID declarado por el cliente; restauración y errores por acordar (D4) |
| `mark-read` | Detalle de aviso, Marcar como leído | `{id}` | `accepted`; otros resultados muestran error | Solo tras aceptación cambia lectura local; no cambia condición activa/resuelta | Autorizar aviso/usuario, persistir lectura e idempotencia; no resolver el aviso por leerlo (D4, D6) |
| `logout` | Encabezado/cuenta, Cerrar sesión | `{}` | `accepted`; otros resultados mantienen vista y avisan | Solo aceptación navega al acceso. No existe sesión real local que cerrar hoy | Invalidar sesión según mecanismo acordado, limpiar permisos/contexto y decidir alcance del cierre (D4) |

Inventario de huerto preservado:

- Estados: `waiting`, `ready`, `stale`, `offline`, `error`, `invalid`, `unassigned`.
- Campos de consulta: `status`, `name`, `updatedAt`, `plants`, `temperature`, `humidity`, `tank`.
- `plants`: tres entradas con `id` numérico 1–3 y `reading`.
- Cada `reading`, `temperature` y `humidity`: `value` numérico o `null`, `quality` y `at` (fecha). `quality:'invalid'` impide mostrar el valor. Un dato ausente no se convierte en cero.
- Humedad en porcentaje; temperatura en °C. La normalización rechaza humedad fuera de 0–100 y valores no numéricos. El backend debe definir calibración, calidad, fechas y criterio de obsolescencia/desconexión.
- `tank`: `state` igual a `low`, `not-low` o `unknown`, y `at`. Es un detector binario de nivel bajo; no implica litros, porcentaje ni depósito lleno.
- Se presentan tres humedades de sustrato, temperatura/humedad ambiental y depósito. No hay sensor óptico ni controles de bomba o umbrales. La lámpara LED continúa formando parte del proyecto.

Avisos: `id` de texto, `title`, `description`, `recommendation`, `zone`, `createdAt`, `resolvedAt` opcional, `importance` (`high`, `medium`, `info`), `condition` (`active`, `resolved`) y `read` booleano. Actualmente se entrega la lista y se encuentra el detalle en ella. El perfil no contempla nombre visible ni contraseña como dato presentado. El Asistente es informativo, sin servicio de IA. Los campos anteriores son inventario; no una aprobación del modelo electrónico.

## 6. Entidades y relaciones conceptuales para Carolina

**No son tablas, SQL o migraciones aprobadas.** Son necesidades de relación para acordar con Rafael y el responsable de datos; no deciden retención, esquema, índices, framework o infraestructura.

| Concepto | Relación necesaria | Datos y decisiones pendientes |
| --- | --- | --- |
| Cuenta | Una identidad de cuenta, vinculada con sesiones/procesos de acceso y credenciales públicas | Correo, estado de verificación y representación segura de contraseña, nunca texto plano. Unicidad/normalización, estados, políticas y conservación (D4) |
| Desafío de registro/recuperación y sesión | Asociados a cuenta/proceso y propósito; vida temporal | Verificación por código, recuperación por enlace, caducidad/uso único y sesión. No se decide si se guardan en PostgreSQL u otro mecanismo aprobado (D4) |
| Documento legal y versión publicada | Un documento tiene versiones identificables; términos y aviso son documentos distintos | Contenido aprobado, identificador, versión y publicación efectiva. Responsable/contacto y vigencia por definir, sin versiones ficticias (D1, D2) |
| Evidencia de aceptación | Relaciona versión de términos con cuenta/proceso de alta y acción confirmada | Momento/fuente/evidencia mínima y conservación por acordar. Consultar el aviso no es aceptación genérica de tratamientos ni registro automático de consentimiento (D1, D2, D4) |
| Solicitud ARCO | Vínculo opcional con cuenta; identidad/representación acreditada según procedimiento | Tipo, descripción, contacto mínimo, recepción/estado e información pública. No confiar en relación declarada o correo para probar titularidad (D3) |
| Historial y requerimiento ARCO | Solicitud tiene historial; requerimiento pertenece a solicitud; aportación corresponde a requerimiento | Separar mensajes públicos de información interna, autor/permiso, fechas y concurrencia. Campos, acreditación, representación, conservación y seguimiento sin cuenta por definir (D3, D4) |
| Credencial pública de llave | Una cuenta puede tener varias; no se asume una llave por dispositivo | Identificador y material público necesario para el verificador acordado, nombre/metadatos opcionales, fechas y revocación. Nunca clave privada, biometría o PIN. Política, sincronización y conservación pendientes (D5) |
| Relación cuenta–huerto/permisos | Autoriza lectura/mutación existente por cuenta y recurso | Necesita definición del backend; no se redefine la estructura IoT ni sensores en esta etapa (D4, D6) |

El contacto de una solicitud no se convierte automáticamente en cuenta. Un folio o ID no otorga permiso. No se almacenan solicitudes ARCO como avisos IoT ni se reutilizan códigos de registro como acceso al seguimiento. La política de eliminación/conservación debe definirse antes de borrar o conservar datos por inferencia.

## 7. Pendientes consolidados y efecto real

Esta es la lista vigente; el cierre enlaza aquí para no repetir decisiones. «Visual» distingue aprobación de un recorrido/contenido de continuar diseñando con estados pendientes; no todos los puntos bloquean diseño.

| ID | Pendiente y causa de cierre pendiente | Responsable / siguiente decisión | Efecto sobre revisión visual, integración y publicación |
| --- | --- | --- | --- |
| D1 | Responsable de datos y contacto no designados | Equipo designa; revisión jurídica valida identidad/contacto y funciones | Visual: puede seguir con pendiente visible. Integración/publicación de canal ARCO y documentos reales: bloqueadas por falta de responsable/procedimiento |
| D2 | Textos legales, versiones, aprobación y publicación inexistentes | Responsable/revisión jurídica con Rafael y Carolina para evidencia | Visual: páginas pendientes revisables. Registro real y publicación de documentos definitivos: bloqueados; no habilitar alta con contenido vacío |
| D3 | Procedimiento ARCO, acreditación/representación, seguimiento sin cuenta, campos visibles y conservación sin acuerdo | Responsable de datos, Rafael y Carolina; frontend ajusta campos cuando se aprueben | Visual: formulario/estados provisionales disponibles. Recepción/seguimiento reales y publicación del canal: bloqueados; sin cuenta no se usa correo+folio como contraseña |
| D4 | Backend, sesión, permisos, errores HTTP, políticas de contraseña/código, correo e idempotencia sin integrar | Rafael acuerda contratos/políticas con equipo; Carolina define persistencia correspondiente | Visual: no bloquea maquetas ni revisión local. Funciones reales de cuenta/recuperación/datos y publicación operativa: bloqueadas; mantener indisponibilidad hasta integrar y probar |
| D5 | Passkeys: dominio/HTTPS, RP ID, compatibilidad, opciones/serialización, verificador, recuperación y reautenticación sin acuerdo | Rafael coordina política/verificador; Carolina material público; frontend integra solo con autorización posterior | Visual: estados demostrativos revisables. Integración y publicación de llaves reales: bloqueadas; los mensajes `demonstration` nunca son autenticación de producción |
| D6 | Documento definitivo de electrónica no entregado/revisado | Equipo confirma responsable y documento; Rafael/Carolina/frontend contrastan después | Visual de acceso/legales/ARCO/Seguridad: puede continuar. Cambiar métricas, modelo o integrar IoT: bloqueado hasta revisión; no frena definir sesiones o cuentas |
| D7 | Pruebas manuales no realizadas: teléfono/teclado reales, lectores de pantalla y, al integrar, autenticadores | Rafael y Gabriela coordinan accesibilidad; Rafael valida integración real con equipo | Visual: aprobación final de esas condiciones pendiente. Publicación accesible/operativa exige resolver resultados; pruebas de autenticadores esperan integración autorizada |
| D8 | Destino/contenido del enlace público `#seguridad` sin aprobación | Producto/equipo decide su destino público y contenido, sin afirmaciones de protección inexistente | Visual: pendiente localizado en navegación pública, independiente de Mi cuenta. Publicación con enlace completo exige resolverlo; no bloquea gestión privada o contratos |
| D9 | Cambios locales sin commit/push y `revision/` excluida de Git | Rafael y Gabriela acuerdan entrega versionada y paquete de revisión separado | Integración colaborativa/reproducción por clon: falta compartir la revisión exacta. No bloquea esta revisión local. Publicación futura debe excluir herramientas y casos de prueba |

Lista manual breve (D7): recorrer con Tab/Shift+Tab/Enter/Espacio y lector real las ayudas/errores/estados; probar teclado virtual, foco y barras en teléfonos; confirmar legibilidad/contraste sobre pantallas y preferencias reales; probar autenticadores/recuperación/cancelación reales únicamente cuando se apruebe la integración. Las matrices automatizadas no sustituyen estas pruebas ni una aprobación jurídica.

## 8. Primer trabajo concreto para integrar

Preparar con Rafael y Carolina un acuerdo ejecutable para **sesión y acceso por correo/contraseña**, antes de llaves o IoT: entradas/respuestas del `login`, restauración de sesión, `profile`, `logout`, permisos, tratamiento 401/403 y protección de solicitudes. Elegir entonces mecanismo de sesión y framework si sigue pendiente, sin reutilizar adaptadores de revisión. Definir las entidades mínimas conceptuales correspondientes y pruebas de contrato de servidor.

Después, en una tarea autorizada distinta, implementar y probar ese transporte en `AuthService`/`AppService` con autorización real, mientras registro sigue bloqueado hasta D1/D2. Continuar registro/correos, ARCO y llaves únicamente al resolver sus dependencias. Esta etapa no escribe endpoints, SQL, migraciones o servicios.
