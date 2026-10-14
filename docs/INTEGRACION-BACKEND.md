# Guía de integración para Kevin

Entrega del frontend principal del 14 de octubre de 2026. Conserva HTML, CSS, JavaScript y MVC. No contiene servicios ni datos simulados. Los nombres de acciones y estados siguientes son el contrato que entiende la interfaz actual, no endpoints HTTP ya acordados.

## Dónde comenzar

1. Confirmar framework, endpoints, mecanismo de sesión y permisos cuenta–huerto. Python está definido como responsabilidad del backend; Django aún no está confirmado.
2. Implementar el transporte en `dist/modelo/servicio-acceso.js` y `dist/modelo/servicio-aplicacion.js`, manteniendo las responsabilidades MVC.
3. Hacer que el servidor compruebe sesión y autorización en cada operación. El router solo presenta pantallas: `canEnter` es una ayuda de navegación, no una barrera de seguridad.
4. Conectar la restauración de sesión al arranque de `dist/controlador/site.js`, además de acceso y cierre. Confirmar cómo tratar sesión vencida y respuestas 401/403.
5. Acordar políticas y contratos antes de activar datos reales. Las validaciones de navegador deben repetirse en servidor.

Ambos adaptadores exponen `request(action, payload, {signal})` y devuelven una promesa con un objeto de respuesta. Respetar `AbortSignal`; los controladores cancelan solicitudes al cambiar de pantalla y aplican un tiempo de espera. No incluir secretos, credenciales de base de datos ni claves de servicios en los archivos públicos de `dist/`.

## Acceso y cuenta

Actualmente `AuthService` responde `{status:'unavailable'}`. No existe contraseña de demostración en este repositorio.

| Acción | Datos enviados por la interfaz | Respuestas comprendidas |
| --- | --- | --- |
| `login` | `email`, `password` | `authenticated`, `invalid-credentials` |
| `register` | `email`, `password` | `accepted`, `password-rejected` |
| `verify` | `email`, `code`, `challengeId` | `verified`, `incorrect-code`, `expired-code` |
| `resend` | `email`, `challengeId` | `accepted` |
| `request-reset` | `email` | `accepted` |
| `inspect-reset` | `token` | `reset-valid`, `invalid-link`, `expired-link` |
| `reset` | `password`, `token` | `reset-complete`, `password-rejected`, `invalid-link`, `expired-link` |
| `change-password` | `currentPassword`, `password` | `password-changed`, `incorrect-current-password`, `password-rejected` |

Todas pueden devolver `limited` con `retryAfterSeconds` o `unavailable`. Registro y recuperación tienen confirmación pública neutral para no distinguir cuentas existentes. Registro/reenvío pueden proporcionar `challengeId`, `expiresAt` y `resendAfterSeconds`. Verificación solo navega a sesión cuando el servicio declara `sessionConfirmed: true`; confirmar esta decisión de producto e integración.

El controlador descarta la confirmación antes de llamar al servicio y vacía los campos de contraseña al terminar. La inspección del enlace de recuperación consume `#restablecer?token=...` y retira el token de la URL; se conserva únicamente durante esa vista. Acordar entrega y validación del enlace/código, expiración y uso único en servidor.

`AuthConfig` en `modelo/acceso.js` deja longitudes, formato de códigos, vencimientos y política de contraseña sin decidir (`null` o listas vacías). Deben alinearse con la política real. La creación de cuenta y la verificación del correo no conceden por sí solas acceso al huerto.

## Huerto, avisos y perfil

`AppService` recibe `garden`, `notices`, `profile`, `mark-read` y `logout`. Las dos últimas acciones esperan `{status:'accepted'}` para actualizar la interfaz; `mark-read` envía `{id}`. La resolución de un aviso es distinta de su lectura.

| Consulta | Campos comprendidos |
| --- | --- |
| `garden` | `status`, `name`, `updatedAt`, `plants`, `temperature`, `humidity`, `tank` |
| `notices` | `status`, `items` |
| `profile` | `status`, `email`, `verified` |

Huerto:

- Estados: `waiting`, `ready`, `stale`, `offline`, `error`, `invalid`, `unassigned`.
- `plants`: tres entradas con `id` numérico 1–3 y `reading`.
- Cada `reading`, `temperature` y `humidity`: `value` numérico o `null`, `quality` y `at` (fecha). `quality:'invalid'` impide mostrar el valor. Un dato ausente no se convierte en cero.
- Humedad en porcentaje; temperatura en °C. La normalización rechaza humedad fuera de 0–100 y valores no numéricos. El backend debe definir calibración, calidad, fechas y criterio de obsolescencia/desconexión.
- `tank`: `state` igual a `low`, `not-low` o `unknown`, y `at`. Es un detector binario de nivel bajo; no implica litros, porcentaje ni depósito lleno.
- Se presentan tres humedades de sustrato, temperatura/humedad ambiental y depósito. No hay sensor óptico ni controles de bomba o umbrales. La lámpara LED continúa formando parte del proyecto.

Avisos:

- Estados de consulta: `ready`, `empty`, `loading`, `error`.
- Cada elemento incluye `id` de texto, `title`, `description`, `recommendation`, `zone`, `createdAt`, `resolvedAt` opcional, `importance` (`high`, `medium`, `info`), `condition` (`active`, `resolved`) y `read` booleano.
- El marcado de lectura debe persistirse por usuario sin resolver la condición. Los avisos de comunicación pueden existir aun sin lecturas.
- Acordar paginación y comportamiento del detalle cuando el servicio deje de entregar toda la lista. Actualmente la vista encuentra el detalle por ID en `items`.

Perfil:

- `status:'ready'` o error; `email` de texto o `null`; `verified` booleano o `null`.
- El modelo actual no contempla nombre visible. No se permite editar el correo en esta entrega ni presentar la contraseña como dato del perfil.

## Estado inicial y comprobación local

Sin integración, el huerto muestra «Esperando las primeras lecturas», Avisos muestra error de consulta y Mi cuenta indica que falta información. La presencia de estas pantallas no significa que el usuario esté autenticado.

Se pueden abrir las rutas indicadas en el README para revisar las vistas con sus estados iniciales. Revisar después de conectar servicios: acceso/cierre y sesión vencida, registro/código, recuperación/cambio, permisos por huerto, datos inválidos/ausentes, lectura de avisos, navegación Atrás/Adelante y móvil. La interfaz existente se comprobó a 320, 390, 768, 1024 y 1440 px en la entrega visual; estas comprobaciones no sustituyen las pruebas de la integración real.

El Asistente es únicamente una pantalla informativa de próxima etapa. La IA generativa, las notificaciones y la conexión IoT necesitan una entrega acordada por separado.
