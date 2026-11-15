# INFORME FASE 1 · Base v2 en Django

## 1. Resumen
Django usa ahora la base v2. Los modelos de las cinco apps reproducen las 46 tablas del script, las migraciones
(`0001_initial` por app + `web/0002_reglas_v2`) crean una base equivalente a `el_chilito_base_v2.sql` y las pruebas de
la base (`pruebas_v2.py`: 149 correctas; `prueba_depuracion.py`: 7 correctas) pasan sobre la base creada con `migrate`.
El actor se fija por petición, el error `23514` responde 409 `regla-de-datos`, los flujos que se conservan usan las tablas
nuevas y las pantallas que se rediseñan responden 503 `en-actualizacion`. Sin `migrate --fake` y sin tocar el script ni las pruebas.

## 2. Archivos
**Creados**
- `backend/web/migrations/0002_reglas_v2.py`: funciones, CHECK, índices, triggers, vistas, datos iniciales, privilegios y caché; SQL copiado del script (sin sección 0 ni BEGIN/COMMIT).
- `backend/{cuentas,huerto,datos,privacidad,web}/migrations/0001_initial.py`: regeneradas.
- `docs/informes/FASE-1.md`: este informe.

**Modificados**
- `*/models.py` (5): tablas v2. `web/models.py` además define `AHORA`, `EN_10_MINUTOS`, `EN_24_HORAS` y `CampoCharFijo`.
- `config/settings/base.py`: `ATOMIC_REQUESTS=True` y middleware `ActorDeBase`. `config/urls.py`: pantallas rediseñadas → `en_actualizacion`.
- `web/middleware.py` (actor + 23514), `web/respuestas.py` (`respuesta_de_base`), `web/api.py` (solo guías, buzón y contacto + vista 503), `web/services.py` (sin `check_replay`), `web/sesion.py`.
- `datos/services.py` (reescrito: identidad, 10 capacidades, `auditar`, buzón), `datos/avisos_correo.py` (lee `correo_pendiente`), `datos/guias.py` (auditoría v2).
- `cuentas/api.py` (`pendingLegal`), `cuentas/inputs.py` (registro con aceptaciones, sin tabla local), `cuentas/services.py`, comando `retirar_factores`.
- `privacidad/services.py` y `api.py`: textos desde `documento_legal`, cookies con IP recortada y navegador resumido, auditoría de perfil y mis datos.
- Frontend: `modelos/comun.js` (mapa de destinos), `vistas/comun.js`, `vistas/huerto.js`, `vistas/administracion.js`, `controladores/enrutador.js`: mensaje «Esta sección se está actualizando.»; fuera los destinos `comercial` y `vinculacion` del menú y del enrutador.
- Pruebas adaptadas: `tests/` (auth, web, contacto/cookies, segundo factor, sesión, cierre), `privacidad/tests.py`, `cuentas/tests.py`, `datos/tests/test_guias.py` (con concurrencia real restaurada).
- `backend/tools/`: `pruebas_local.py` (sin modo `crud`; publica los textos legales como propietario; usa `CHILITO_PRUEBAS_CLAVE_RUNTIME` para el rol de la aplicación), `probar_privacidad.py` (adaptado a las tablas v2), `probar_seguridad.py` (la comprobación de actividad usa `/api/guias`), `armar_entrega.py`, `tools/README.md` y `README.md` (sin `crud`).

**Eliminados**
- Migraciones antiguas de las cinco apps; `datos/vinculacion.py`, `datos/diagnostico.py`.
- `backend/tools/probar_crud_runtime.py`: lo cubre `pruebas_v2.py`.
- Pruebas de pantallas desactivadas: `datos/tests/{test_contrato,test_diagnostico,test_esquema_ampliado,test_integridad,test_mantenimientos,test_servicios,test_soporte_buzon,test_vinculacion}.py`. Las del buzón se reubicaron en `tests/test_contacto_cookies.py`.

## 3. Líneas
Ver el resumen de `git diff --stat` en el commit; el cambio neto es una reducción grande por las migraciones y el código de las pantallas desactivadas.

## 4. Endpoints
- **Cambiados:** `GET /api/cuenta` (añade `pendingLegal`; `role` y `capabilities` con los 10 codenames), `/api/privacidad/documentos/<tipo>` (lee `documento_legal`), `/api/privacidad/cookies`, `/api/contacto`, `/api/guias`, `/api/admin/guias*`, `/api/admin/consultas*`, registro.
- **Ahora 503 `{"status":"error","code":"en-actualizacion"}`** (401 sin sesión): `/api/huertos/actual*`, `/api/soporte*`, `/api/vinculacion`, `/api/admin/{flota,soporte*,sesiones*,mantenimientos*,vinculacion*}`.
- **Eliminados de la lógica** (hoy solo responden 503): token de soporte, sesión técnica, mantenimientos, solicitudes, avisos y vinculación por código largo.
- **Nuevo comportamiento común:** `23514` → 409 `{"code":"regla-de-datos"}`.

## 5. Seguridad
| Requisito | Cómo se cumple | Prueba |
|---|---|---|
| ASVS V8 (autorización en servidor, actor) | `ActorDeBase` ejecuta `set_config('chilito.actor_id', id, true)` dentro de la transacción de cada petición con sesión; la petición no puede elegir el actor. Capacidad y segundo factor en cada endpoint (`require_cap`). | `tests.test_web.ActorEnLaTransaccion`, `Sesion.test_las_capacidades_son_independientes`, `tests.test_segundo_factor` |
| ASVS V2 (validación) | Lista blanca de campos y tipos en `leer_json`; límites de página; validación de texto en perfil, guías y contacto; la base valida con CHECK. | `Escrituras.*`, `datos.tests.test_guias.Validacion` |
| ASVS V16 (errores y auditoría) | Mensajes genéricos; el detalle de `23514` (tabla, regla y mensaje fijo) solo va al registro. Auditoría con acción, actor, recurso y resultado; perfil guarda el nombre del campo, nunca el valor. | `ReglasDeLaBase.*`, `privacidad.tests.PerfilYMisDatos` |
| ASVS V14 (minimización) | IP recortada (IPv4 último bloque 0; IPv6 /48) y navegador resumido («Chrome 130 · Android»); nunca el user-agent completo. | `privacidad.tests.Registro.test_ip_recortada`, `test_navegador_resumido…`, `CookiesPermanecen.test_la_bitacora…` |
| SSDF PW.4 | Se reutilizan `leer_json`, `endpoint`, `paginar`, el saneador legal y las funciones de la base (`chilito_documento_vigente`, `chilito_aceptaciones_pendientes`). | revisión del diff |
| SSDF PW.5 | Solo ORM o SQL parametrizado; `textContent`/saneado sin cambios. | revisión del diff |
| SSDF PW.8 | 168 pruebas de Django, 130 flujos con el rol limitado, 149 + 7 de la base y comparación de catálogos. | ver §6 |

Decisión de diseño: el middleware abre su propia transacción porque corre antes de que `ATOMIC_REQUESTS` abra la de la vista, y `set_config(…, true)` solo vive dentro de una transacción. `ATOMIC_REQUESTS` queda activo y la de la vista es un savepoint.

## 6. Comprobaciones
| Comando | Resultado |
|---|---|
| `manage.py check` (configuración normal, sin la temporal) | 0 problemas |
| `manage.py makemigrations --check --dry-run` | sin cambios |
| `manage.py migrate` en base vacía (owner) | todas aplicadas, incluida `web.0002_reglas_v2` |
| Tablas y vistas de la base migrada | 46 y 5 |
| `pruebas_v2.py` contra la base de `migrate` | 149 correctas, 0 fallos |
| `prueba_depuracion.py` contra la misma base (tras `pruebas_v2.py`) | 7 correctas, 0 fallos |
| `manage.py test` (base temporal) | 168 pruebas OK en ≈ 60 s (incluye `ConcurrenciaReal` con `serialized_rollback`) |
| `backend/tools/pruebas_local.py flujos` (rol limitado, base temporal) | seguridad 29/29, MFA 45/45, privacidad 56/56 |
| `node --check` de los cinco JS tocados | sin errores |

### Diferencias aceptadas entre la base del script y la de `migrate`
Comparación de columnas, tipos, nulos, defaults, CHECK por nombre, UNIQUE, FK, índices, triggers, funciones, vistas, privilegios por tabla y columna y datos iniciales:
1. Las FK de Django son `DEFERRABLE INITIALLY DEFERRED`; nombres automáticos de FK e índices.
2. La expresión de `soporte_caso.folio` y `consulta_producto.folio` lleva `COALESCE`; mismo resultado.
3. Índices `varchar_pattern_ops` que Django crea para columnas únicas de texto, y tres índices de tablas de unión (`auth_group_permissions`, `cuentas_usuario_groups`, `cuentas_usuario_user_permissions`).
4. 24 permisos estándar de Django (`change`, `delete`, `view`) de sus modelos y de `Usuario`.
5. Orden de columnas distinto en algunas tablas (`comando`, `autodiagnostico`, `cuentas_usuario`, `privacidad_decision` y las de Django); no afecta a las pruebas porque usan lista de columnas.

Corregido en modelo o migración (nunca en el script): `now()` en lugar de `statement_timestamp()`, `alias` con `db_default`, `char(64)` en dos columnas, FK sin índice propio, `ON DELETE CASCADE` de `medicion_planta` y orden de columnas de `medicion_planta`.

## 7. Pendientes o dudas
- **Rutas de documentos:** los archivos v2 están en la raíz y no en `docs/` o `sql/`; no existe `docs/seguridad/` (diseño Etapa 3). Trabajé con CLAUDE.md, el prompt y la guía v2.
- **`.env`:** `CHILITO_DB_PASSWORD` (12 caracteres) no coincide con la clave real del rol `chilito_pkg_runtime`: PostgreSQL la rechaza. La aplicación no arrancará con el rol de la aplicación hasta que se actualice. Las pruebas usan `CHILITO_PRUEBAS_CLAVE_RUNTIME`.
- **Pruebas de concurrencia de mantenimientos y soporte** (`test_servicios`, `test_mantenimientos`): se eliminaron con esas funciones, hoy en 503. Vuelven con su pantalla en las fases 4 a 6.
- **Código del frontend que queda sin ruta:** `CommerceController`, `CommerceViews`, `CommerceModel`, `BindingAdminController` y `modelos/equipos.js` (parte admin). La fase 5 los elimina; los quité del menú y del enrutador.
- **Mensaje «Esta sección se está actualizando.»:** reemplaza el texto genérico de error en esas pantallas (huerto, avisos, panel de administración y mantenimientos). Las fases 3 a 6 deben restaurar mensajes de error reales.
- **Actividad de sesión:** Django no guarda la sesión en respuestas 5xx, así que una visita a una pantalla en 503 no renueva la inactividad. Otros endpoints con respuesta 200 sí la renuevan; desaparece con las fases 3 a 6.
- **Cierre de sesión técnica:** `close_actor_sessions` se eliminó porque ya no hay sesiones técnicas; la fase 6 lo reincorpora con motivo `cierre_sesion`.
- **`frontend/legales/*.html`** ya no se leen; se borran en la fase 7.
- **`FUNCIONAMIENTO-BASE-DE-DATOS-v2.md`:** no cambia nada de sus secciones 3 y 15, así que no lo toqué.
- **Sin probar en navegador:** no recorrí la interfaz; solo revisión de sintaxis y pruebas HTTP.

## 8. Cómo probarlo a mano
1. Crear la base y migrar como en `EJECUCION-v2.md` §2.2 (pasos 2–4, con textos legales 0.1).
2. Registrarse con y sin casillas; verificar el código; iniciar sesión con segundo paso; recuperar contraseña.
3. Mi cuenta: Perfil, Seguridad, Privacidad y Mis datos. Cookies (aceptar, rechazar, configurar).
4. Textos legales visibles con su versión; «Consíguelo» llega a Solicitudes del producto; guías visibles en Mantenimiento.
5. `SELECT chilito_designar_super_admin('tu-correo');` y ver el panel; las pantallas desactivadas dicen «Esta sección se está actualizando.».
