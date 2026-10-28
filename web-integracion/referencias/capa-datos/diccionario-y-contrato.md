# Diccionario de datos y contrato para Django

Paquete de datos de El Chilito para la entrega web del 28 de octubre de 2026.
La fuente de verdad es `backend/huerto/models.py`, `backend/datos/models.py` y sus migraciones; el SQL se obtiene de ellas. Este documento describe contratos para conectar después la API y el frontend, no endpoints HTTP ya publicados. No acredita ejecución en PostgreSQL; consultar `resultado-pruebas.md`.

## 1 Identidad y datos conservados

Se conserva `cuentas.Usuario` y Django/allauth; no existe otra cuenta para el administrador.

| Entidad | Campos relevantes y relación | Tratamiento |
| --- | --- | --- |
| Usuario | `id`, `email`, `password` hash, `is_active`, fechas y banderas de Django; grupos/permisos | Identidad persistida. La contraseña de entrada admite 15–256 caracteres; la columna de hash no limita la entrada a 128. |
| Correo | `account_emailaddress.user_id`, `email`, `verified`, `primary` | Se exige cuenta activa y correo verificado antes de operar. |
| Sesión y cuotas | `django_session`; `cuentas_cuotas_acceso` | Mecanismos del framework; el navegador no determina su validez. |
| Confirmación local | Usuario, fecha, `casilla_marcada`, `documentos_pendientes` | Constancia técnica separada del consentimiento de soporte; no acredita aceptación de políticas legales aprobadas. |
| Huerto | `id`, `clave`, `nombre`, `zona_horaria`, `creado_en` | Identidad del recurso; textos significativos y zona horaria validada por Django. |
| Membresía | Usuario, huerto, `activa`, `asignada_en` | Pareja única e identidad estable. Registro/verificación no asignan un huerto automáticamente. |
| Zona | `id`, huerto, `numero`, `nombre`, `cultivo` | Número 1–3 único por huerto; es distinto de la clave primaria. |
| Aviso | Huerto, zona opcional, severidad, título, descripción, recomendación, creación/resolución | La zona debe pertenecer al mismo huerto. La identidad huerto/zona no se reasigna. |
| Aviso leído | Aviso, usuario y `leido_en` | Único por pareja; leer no resuelve el aviso. |

La nueva migración crea las tres zonas al insertar un huerto y completa las que falten en el antecedente sin sobrescribir nombres/cultivos existentes. Los disparadores impiden borrar zonas o reasignar su identidad; el historial y las FK impiden cascadas accidentales. El usuario de ejecución no dispone de TRUNCATE. El propietario de migraciones conserva facultades administrativas de restauración: no debe usarse como usuario web.

## 2 Entidades nuevas del alcance web

Los identificadores UUID se generan en el servidor. Las FK usan PROTECT en Django; la retención e inmutabilidad también se refuerzan en PostgreSQL.

| Tabla del paquete | Campos | Relación y función |
| --- | --- | --- |
| `datos_dispositivo` | `id` bigint, `huerto_id` único, `identificador` único/significativo, `creado_en` | Como máximo uno por huerto, provisionado por un operador. Su identidad se conserva; no es un sensor conectado ni una credencial de dispositivo. |
| `datos_mantenimiento` | UUID, huerto, actor, tipo, `registrado_en` | Historial inmutable de cuidados, separado de soporte. Tipos: `refill`, `substrate`, `germination`, `harvest`, `inspection`. No se añaden litros, peso o fotos. |
| `datos_casosoporte` | UUID, huerto, dispositivo, solicitante, incidente, `creado_en` | Caso del usuario sobre su recurso. Incidentes: `pump`, `humidity`, `lamp`, `connection`, `other`. No se inventa una operación de cierre de caso inexistente en el frontend. |
| `datos_permisosoporte` | UUID, caso, otorgante, consentimiento explícito, verificador, alcance, emisión, vencimiento, revocación opcional | El otorgante coincide con el solicitante. Alcance fijo `diagnostico_incidente`; duración positiva de hasta 24 h. Nunca contiene el token en claro. |
| `datos_sesiontecnica` | UUID, permiso, administrador, inicio, cierre opcional y motivo | Una sesión abierta por administrador; cada uso revalida el permiso. Cerrar es irreversible. Motivos: `explicit`, `revoked`, `replaced`, `logout`, `expiry`. |
| `datos_validacionversion` | UUID, actor, tipo, versión, notas, `validada_en` | Validación inmutable de los datos exactos. Tipos: `weights`, `math`, `rollback`; versión 3–64 caracteres del alfabeto permitido, notas hasta 2000. No valida un modelo de IA real. |
| `datos_revisionconocimiento` | `id` bigint, autor, contenido, fecha | Cada guardado crea una revisión inmutable; no sobrescribe la anterior. Texto significativo de 20–10 000 caracteres. Su ID ordenado identifica la revisión. |
| `datos_solicitud` | UUID, actor, tipo, huerto/dispositivo/sesión/validación según tipo, fecha y estado | Guarda la intención web. Tipos de usuario: `water`, `lamp-off`, `lamp-auto`; administrativos: tipos de versión, `restart-node`, `restart-platform`. Estado persistido `pending`. |
| `datos_auditoria` | UUID, actor, código de acción, resultado, fecha y referencias a huerto/caso/permiso/solicitud/mantenimiento/sesión/validación/conocimiento | Eventos anexables e inmutables. Sin texto libre, correo, contraseña, token ni cuerpos de errores. Los resultados son `recorded` o `pending`. |

No se persisten etiquetas, iconos, botones, contadores de caracteres, filtros ni el estado abierto/cerrado de un menú. Los indicadores de flota y las gráficas son proyecciones; no se crea una tabla por métrica. Telemetría, sensores, WebAuthn, IA y ejecución física/remota quedan fuera de este paquete.

## 3 Identidad y capacidades de la aplicación

`identity(actor)` relee la cuenta en servidor y comprueba actividad y correo verificado. La futura API pasa exclusivamente `request.user`; nunca un actor, propietario o rol recibido del JSON. Una FK válida no demuestra que la petición esté autorizada.

Las capacidades se obtienen de asignaciones explícitas de permisos Django, directas o por grupo. No se usa el bypass implícito de `is_superuser` ni se interpreta `is_staff` como permiso sobre el panel.

| Capacidad Django | Área del administrador | Operaciones permitidas |
| --- | --- | --- |
| `datos.ver_flota` | Telemetría de flota | Proyección mínima de dispositivos y agregados disponibles. No incluye tokens ni acceso técnico individual. |
| `datos.atender_soporte` | Consola remota | Consultar casos autorizados, registrar solicitud de token; abrir/usar consola solo con permiso vigente del caso y sesión técnica del mismo administrador. |
| `datos.ver_gobernanza` | Gobernanza | Leer los principios y límites técnicos. No concede soporte ni acceso global a datos privados. |
| `datos.gestionar_cambios` | Despliegues y parámetros | Validar versiones, registrar solicitudes de publicación/reversión/reinicio de plataforma y guardar revisiones de conocimientos. |

`session_contract(actor)` produce `role: "admin"` cuando existe alguna de estas capacidades; en otro caso produce `role: "user"`. Devuelve además `capabilities`, `sessionConfirmed` y `profile` verificado. El rol de navegación no concede las otras capacidades. El frontend deberá elegir una primera área autorizada y mostrar el rechazo de las demás.

Los privilegios PostgreSQL son distintos: propietario/migrador instala; usuario de ejecución tiene DML acotado y no puede conceder permisos web, alterar tablas, desactivar disparadores ni truncar. Las asignaciones iniciales de capacidades se realizan por el operador autorizado fuera de una petición web; no hay autoascenso de privilegios.

## 4 Operaciones para la futura API

Las funciones siguientes están implementadas en `datos/services.py`. Su exposición HTTP, serialización completa, control CSRF, manejo neutral de recursos ajenos/inexistentes y límites de frecuencia siguen siendo trabajo de integración. No se copiaron endpoints ni transporte SMTP del backend anterior para presentarlos como API nueva.

| Operación de servicio | Comprobaciones y persistencia | Respuesta/contrato esperado |
| --- | --- | --- |
| `session_contract` | Cuenta activa y correo verificado; permisos explícitos | Sesión autenticada, `role`, capacidades y perfil. No crea una sesión alternativa a allauth. |
| `record_maintenance`, `maintenance_history` | Membresía activa del huerto; tipo permitido; actor del servidor | Registro/historial con UUID, tipo, fecha y actor. La etiqueta de tarea puede derivarse del tipo. |
| `mark_notice_read` | Cuenta verificada, membresía activa y aviso del recurso | Marca única por usuario; mantiene intacto `resuelto_en`. |
| `record_user_request` | Membresía activa, dispositivo del huerto y tipo permitido | Solicitud duradera `pending`; no envía MQTT ni afirma que el agua/lámpara cambiaron. |
| `issue_support` | Membresía activa, recurso identificado, incidente válido y `consent is True` | Crea caso, permiso y auditoría en una transacción; devuelve token una sola vez. |
| `revoke_support` | Usuario otorgante/solicitante del caso | Revoca permiso, cierra sesiones vinculadas y conserva caso/historia. |
| `request_support_token` | Capacidad de soporte y recurso del caso | Evento de solicitud; no genera token ni concede acceso al administrador. |
| `open_technical` | Capacidad, caso, token exacto, permiso activo, propietario aún elegible | Sesión técnica ligada al administrador y permiso. Reemplaza su sesión anterior. |
| `technical_action` | Revalida capacidad, cuenta, membresía del otorgante, caso, permiso, caducidad y sesión en cada uso | Diagnóstico sin servicio: `pins: []`, `logs: []`, `at: null`; reinicio: solicitud `pending`. |
| `close_technical` | Identidad y propiedad de la sesión | Cierre explícito o por logout; no ejecuta una orden física. |
| `validate_version`, `request_deployment` | Capacidad de cambios; validación del mismo actor, tipo/versión/notas; uso único | UUID de validación y solicitud `pending` vinculada a esos datos exactos. |
| `save_knowledge`, `request_platform_restart` | Capacidad de cambios; longitud/contenido permitido | Nueva revisión o solicitud `pending`, con auditoría. |
| `fleet_projection`, `governance_projection` | Capacidad específica | Metadatos disponibles o ausencia explícita, sin lecturas fabricadas. |

Los futuros listados de casos, historial técnico y solicitudes también deberán filtrar por capacidad y recurso en servidor; no basta enviar todas las filas para que JavaScript las oculte. El consumidor no puede cambiar `actor`, `otorgante`, `verificador`, `estado` o las fechas de servidor mediante asignación masiva.

## 5 Soporte temporal y estados

El token tiene exactamente 43 caracteres ASCII del alfabeto base64url sin relleno: `[A-Za-z0-9_-]{43}`. Se obtiene de `secrets.token_urlsafe(32)`: 256 bits de origen aleatorio. Es sensible a mayúsculas; no se aplica `trim()`, mayúsculas ni otra normalización al validarlo.

El servidor guarda únicamente un HMAC SHA-256 hexadecimal de 64 caracteres, calculado con `CHILITO_SUPPORT_KEY`, una clave externa independiente de `SECRET_KEY` de al menos 32 bytes. El dato en claro aparece solo en la respuesta de emisión. La API no debe devolver el verificador ni volver a mostrar el token al listar casos. Pérdida del token implica emitir una nueva autorización, no recuperarlo de la base. Rotar la clave externa invalida verificadores anteriores; revocar y emitir de nuevo es la ruta prevista.

El caso persiste aunque el permiso se revoque o venza. El estado de permiso se deriva como `active`, `expired` o `revoked`; no se usa un CHECK con la hora actual. La consola añade el estado de su sesión técnica. Las etiquetas «Token solicitado», «Espera validación» o «Diagnóstico autorizado» se derivan de estos registros/eventos, no son estados de resolución del incidente. No se añadió una transición de cierre de caso no definida por la interfaz.

Cada emisión con consentimiento conserva caso, otorgante, alcance, emisión y auditoría `support-granted`. Esa constancia técnica no es un expediente legal ni reutiliza la casilla del registro. Emitir otro permiso del mismo usuario revoca el anterior y conserva sus reportes.

Revocación y uso técnico se serializan con bloqueos transaccionales: sujetos en orden numérico, membresía, caso, permiso y sesión. Si la revocación obtiene el bloqueo primero, el uso se rechaza; si el uso confirma primero, su solicitud queda registrada y la revocación impide usos posteriores. No promete deshacer una actuación física: este paquete no la realiza. La vigencia se comprueba en cada operación, aunque una fila de sesión vencida siga almacenada.

## 6 Traducciones PostgreSQL y JSON

| Fuente persistente | Contrato JSON y criterio |
| --- | --- |
| IDs bigint de usuario/huerto/zona/dispositivo/revisión | Cadena decimal, nunca `Number`/`parseInt` para identidad. JavaScript no representa con exactitud todo bigint. |
| UUID de mantenimiento/caso/permiso/sesión/solicitud/auditoría | Cadena UUID opaca; validar sintaxis en servidor sin convertirla en prueba de acceso. |
| `Zona.numero` | Número JSON 1, 2 o 3; coincide con `plants[].id` de la interfaz actual. Añadir `zoneId` como cadena si hace falta la PK, sin sustituir el número visual. |
| `Zona.cultivo` | `plants[].crop` como texto persistido, además de `name`; el adaptador y la vista deberán conservarlo. |
| Fechas `timestamptz` | ISO 8601 con zona/UTC para avisos, mantenimiento, versiones y solicitudes. El formato localizado se deriva en la vista. |
| Emisión de permiso | Se conserva la excepción actual: `createdAt` y `expiresAt` como enteros epoch en milisegundos; `ticket` es UUID de caso y `user` es ID decimal como cadena. |
| `titulo`, `descripcion`, `recomendacion`, `creado_en`, `resuelto_en` | `title`, `description`, `recommendation`, `createdAt`, `resolvedAt`. |
| Severidad `informacion`, `advertencia`, `critico` | `importance: "info"`, `"medium"`, `"high"`. |
| `resuelto_en`; marca del usuario | `condition: "active"/"resolved"`; `read` deriva de `AvisoLeido`, no de la resolución. `zona_id = NULL` se presenta como «Huerto». |
| Ausencia de mediciones | `value: null, quality: "missing", at: null`; flotador `state: "unknown", at: null`. Sin cero, fecha actual ni conexión inventados. |
| `Solicitud.estado = pending` | Etiqueta «Sin confirmación»; puede derivarse `origin` del actor/contexto. No traducir como «ejecutado». |

Las métricas agregadas, disponibilidad, calidad y estados de conexión necesitan datos de una fuente real para calcularse. La capacidad fija de 19 L es una especificación del equipo, no lectura de volumen. No se define el origen de la lectura general de sustrato ni el reparto físico de dos bombas entre tres plantas: pertenecen a una integración posterior.

## 7 Ajustes pendientes del frontend sin modificarlo en este paquete

1. Sustituir el arranque `vista-trabajo.js` por el contrato real allauth/Django y configuración 15–256; conservar seis dígitos, 600 s, tres fallos, 60 s y cinco reenvíos. La expiración y los intentos los decide el servidor.
2. Transportar `session.role` y capacidades del servidor; el rol no se selecciona por correo en JavaScript. Autorizar también cada endpoint, aunque una URL no aparezca en el menú.
3. Cambiar los servicios de mantenimiento, soporte y administración a operaciones asíncronas; esperar confirmación del servidor antes de mostrar guardado. Conservar cancelación, error y reintento; una respuesta perdida no debe inventar éxito.
4. Usar el token de soporte de 43 caracteres exactos en ambos extremos; retirar el límite incompatible 512/80 y la conversión a mayúsculas. Mantener las fechas de la emisión en milisegundos o acordar una conversión explícita en el adaptador.
5. Los listados administrativos y la selección de caso deben consumir el mismo UUID y recurso persistidos que usa el usuario; no sincronizar arrays en memoria como autorización.
6. Conservar `crop` desde la API hasta las tarjetas, actualmente fijadas a «Chile habanero». No confundir `numero` con la PK de zona.
7. Preservar nulos, fechas originales y enumeraciones traducidas; arreglar el render de conectividad para que `null` no se interprete como desconexión medida.
8. Mantener WebAuthn, sensores, IA y ejecutores de órdenes/despliegues fuera de operación hasta su entrega. Las solicitudes web sí se registran; la versión en servicio sigue sin cambiar sin confirmación externa.
9. Vincular cierre de consola, cambio de caso y logout a los servicios de sesión técnica. La revocación/caducidad se verifica en servidor incluso si la interfaz no se actualiza.

## 8 Límites del contrato

Código de correo y token de recuperación conservan el ciclo de vida del framework; no se crean tablas paralelas. WebAuthn no tiene credencial ni PIN web en este paquete. SMTP permanece sin envío real en pruebas. Fuerza bruta, cookies, CSRF, respuestas HTTP, ocultación de errores y disponibilidad de correo se comprobarán al integrar la API; disponer de SQL no demuestra esas funciones.

## Consultas incluidas en la capa de datos

`garden_projection`, `notices_projection`, `maintenance_history`, `user_requests` y `support_reports` comprueban membresía antes de consultar. `administrative_reports` requiere atender soporte; `changes_projection` requiere gestionar cambios y limita la proyección de auditoría. No devuelven verificadores ni tokens. Esas proyecciones no son endpoints; la futura API debe serializar/cerrar la consulta en su frontera autorizada y conservar respuestas neutrales.
