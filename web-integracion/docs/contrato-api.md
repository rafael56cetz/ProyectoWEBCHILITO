# Contrato de API de integración

27 de octubre de 2026. Sesión de navegador Django/allauth, mismo origen. Todas las escrituras requieren CSRF. JSON estricto, errores neutrales y sin datos sensibles. GET no modifica datos de negocio. Los campos actor, propietario, estados y fechas de servidor no son entradas permitidas. Identificadores bigint se serializan como cadenas; UUID opacos; fechas ISO con zona salvo emisión del permiso (epoch ms). Endpoints sin slash final.

## Cuentas

Se conserva la superficie `_allauth/browser/v1/` del backend anterior: auth/session GET/DELETE, auth/login POST, auth/signup POST, auth/email/verify POST, auth/email/verify/resend POST, auth/password/request POST, auth/password/reset GET/POST, account/password/change POST. Solo browser, sin tokens de aplicación. GET api/acceso/configuracion prepara CSRF y políticas; GET api/acceso/verificacion devuelve el proceso sin código. GET api/cuenta devuelve perfil/capacidades/session y gardenAssigned. Login y restauración deben consultar api/cuenta; el navegador no asigna roles.

## Usuario

| Método y ruta | Entrada permitida | Resultado | Autorización/servicio |
|---|---|---|---|
| GET api/huertos/actual | Ninguna | Proyección del huerto o error garden-unassigned | identity, membresía; garden_projection |
| GET api/huertos/actual/avisos | page opcional | items, paginación | notices_projection |
| GET api/huertos/actual/avisos/{id} | Ninguna | notice | notices_projection filtrada |
| POST api/huertos/actual/avisos/{id}/lectura | {} | accepted | mark_notice_read |
| GET/POST api/huertos/actual/mantenimiento | POST {type} | items / registro | maintenance_history / record_maintenance |
| GET/POST api/huertos/actual/solicitudes | POST {type} | items / solicitud pending | user_requests / record_user_request |
| GET/POST api/soporte | POST {incident,consent} | items / permission token una sola vez | support_reports / issue_support |
| POST api/soporte/{uuid}/revocar | {} | accepted | revoke_support |

## Administración

| Método y ruta | Entrada permitida | Resultado | Capacidad/servicio |
|---|---|---|---|
| GET api/admin/flota | Ninguna | proyección | ver_flota / fleet_projection |
| GET api/admin/gobernanza | Ninguna | proyección | ver_gobernanza / governance_projection |
| GET api/admin/cambios | Ninguna | proyección | gestionar_cambios / changes_projection |
| GET api/admin/soporte | page opcional | items | atender_soporte / administrative_reports |
| POST api/admin/soporte/{uuid}/solicitar-token | {} | accepted | request_support_token |
| POST api/admin/soporte/{uuid}/abrir | {token} | session {id,...} | open_technical |
| POST api/admin/sesiones/{uuid}/accion | {action} | diagnóstico sin fuente o solicitud pending | technical_action |
| POST api/admin/sesiones/{uuid}/cerrar | {} | accepted | close_technical; solo sesión propia |
| POST api/admin/validaciones | {type,version,notes} | validation {id,...} | gestionar_cambios / validate_version |
| POST api/admin/despliegues | {validationId} | solicitud pending | request_deployment |
| POST api/admin/conocimiento | {content} | revisión | save_knowledge |
| POST api/admin/reinicio | {} | solicitud pending | request_platform_restart |

## Respuestas, límites y repetición

Las respuestas de datos usan {status:"ready",...}; escrituras {status:"accepted",...}. Error {status:HTTP,code}, sin traza ni existencia de recursos ajenos. No se acepta contenido fuera de application/json ni claves adicionales. Listados limitados/paginados. Operaciones POST de negocio exigen Idempotency-Key UUID para deduplicación transaccional por actor/ruta/cuerpo; misma clave y cuerpo devuelve la misma respuesta; cuerpo distinto se rechaza. Secretos de soporte no se guardan en esa respuesta: el reintento de emisión devuelve permiso/caso y token:null, debe explicarse al usuario y emitir una autorización nueva si perdió el original. Login/recuperación utilizan los límites allauth; apertura/uso técnico y escrituras también tienen cuotas de servidor.

Ningún endpoint ejecuta hardware, despliegues, IA o SMTP real durante las pruebas. WebAuthn y políticas legales fuera de alcance. El diseño de entrada es v1.0 para revisión, no revisión humana cerrada; el timeout de inactividad propuesto no se activa sin decisión posterior.

## Aclaraciones de implementación comprobada

Paginación de listados: 25 filas por página, aplicada antes de serializar, más `page`/`total`. Flota y publicaciones se limitan a100; auditoría ya se limita a100. Las cuotas adicionales de servidor son15 escrituras técnicas/minuto y60 restantes/minuto por usuario, ventana fija serializada en PostgreSQL; valores locales documentados, no mandatos normativos.

Una respuesta idempotente es un recibo histórico: no reabre una consola cerrada/revocada ni garantiza que el permiso siga vigente. Se revalida acceso al recurso antes de volver a entregar datos. La emisión de soporte nunca recupera su secreto en un replay; retorna token:null en ese caso.
