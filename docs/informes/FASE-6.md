# Informe de fase 6 · Administración adaptada

Rama: `fase-6-admin-adaptada` (sobre `fase-5-admin-nueva`).

## 1. Resumen

Telemetría de flota con datos reales, Consola remota sin token (atender, conectar, órdenes, cierre y resolución, con sondeo de revocación cada 10 s), Mantenimientos de todos los huertos con búsqueda, filtros y paginación visible, y confirmaciones en Solicitudes (Archivar), Guías (Publicar y Retirar) y Mantenimientos (Anular). Se quitaron el token, los «pines GPIO», los registros simulados, las métricas de flota sin fuente y los últimos 503 `en-actualizacion`. Al cerrar la sesión de la cuenta se cierra su sesión técnica. **No se probó en un navegador ni con el rol `chilito_pkg_runtime` sobre los endpoints nuevos.**

## 2. Archivos

Sin archivos nuevos, salvo este informe.

Backend:
- `datos/services.py`: consola (bandeja, detalle, atender, conectar, estado de la sesión, órdenes, cerrar, resolver) y el cierre de la sesión técnica al salir.
- `datos/equipos.py`: flota (totales, tendencias de 7 días, tabla paginada y problemas recientes) junto al inventario, que ya consultaba `v_estado_equipos`.
- `datos/api.py`, `huerto/api.py`, `config/urls.py`: vistas y rutas nuevas; se borran las del token (`solicitar-token`, `abrir`).
- `datos/apps.py`: conecta `user_logged_out` (cubre cerrar sesión y vencimiento por inactividad).
- `huerto/services.py`: mantenimientos de todos los huertos; `registrar_cuidado` se parte en `_validar_cuidado` y `_crear_cuidado`, y `cuidados` en `_filtrar_cuidados`, para reutilizarlos.
- `web/respuestas.py`: mensajes y códigos claros para las reglas de la base de soporte y cuidados.
- `web/api.py`, `tests/test_web.py`: se borran `en_actualizacion` y su prueba.
- Pruebas: `datos/tests/test_admin.py` (`Flota`, `Consola`, `Mantenimientos` y las 14 rutas nuevas en `Capacidades`).

Frontend:
- `modelos/administracion.js`, `vistas/administracion.js`, `controladores/administracion.js`: `AdminService/AdminViews/AdminController` se sustituyen por `FleetService/Views/Controller` y `ConsoleService/Views/Controller`; confirmación al archivar una consulta.
- `modelos/huerto.js`, `vistas/huerto.js`, `controladores/huerto.js`: Mantenimientos reescrito con los componentes de la fase 5 (se conserva el calendario compartido); confirmaciones de Guías; los títulos de órdenes incluyen las de soporte (el usuario ve «Prueba de bomba · planta 2 · 3 s», no «Orden»).
- `modelos/cuenta.js`: `keepalive` en `ChilitoHTTP.request`; el cierre de sesión ya no llama a la consola (lo hace el servidor).
- `modelos/comun.js`: `#admin/consola` redirige a `#admin/soporte`.
- `vistas/comun.js`: `AdminTableViews.dateField` acepta un valor (los filtros conservan las fechas al repintar).
- `vistas/estilos/panel.css`, `apariencia.css`: se borran las reglas de lo eliminado (ticket, token, GPIO, logs, gestión) y se añade la maqueta de la consola con los tokens existentes.
- `index.html`: versión de los archivos `mvc.7` → `mvc.8` para que el navegador no use los anteriores.
- `pruebas/pruebas.cjs`: se quitan los casos del token y se añade la suite de esta fase.

## 3. Líneas

`git diff --stat`: 24 archivos, 1578 añadidas y 566 eliminadas (más este informe).

## 4. Endpoints

Nuevos o cambiados (todos con capacidad y segundo factor):

| Capacidad | Rutas |
|---|---|
| `ver_flota` | `GET admin/flota?busqueda&estado&conexion&page` |
| `atender_soporte` | `GET admin/soporte?estado&page`, `GET admin/soporte/<id>`, `POST …/atender`, `POST …/conectar`, `POST …/resolver` |
| `atender_soporte` | `GET admin/sesiones/<id>` (estado en vivo), `POST …/accion`, `POST …/cerrar` |
| `gestionar_mantenimientos` | `GET/POST admin/mantenimientos`, `GET admin/mantenimientos/<id>`, `POST …/corregir`, `POST …/anular` |

Eliminados: `admin/soporte/<id>/solicitar-token` y `admin/soporte/<id>/abrir`. No queda ninguna ruta en 503.

## 5. Seguridad

| Requisito | Cómo se cumple | Prueba |
|---|---|---|
| ASVS V8 (capacidad) | `@endpoint(cap=…)` y `require_cap` en cada servicio; `ver_flota` la exige solo Django (la base no la conoce) | `Capacidades.test_sin_sesion_sin_capacidad_y_sin_factor` (ahora con las rutas nuevas) |
| V8 (propiedad del caso) | Solo `atendido_por` conecta, da órdenes, cierra y resuelve; la sesión se busca por su dueño (otro administrador recibe 404). Cada orden vuelve a leer la autorización | `test_el_segundo_admin_no_conecta_ni_opera_ni_resuelve_el_caso_del_primero`, `test_sin_atender_no_se_conecta_ni_se_resuelve` |
| V8 (autorización vigente) | Revocada o vencida: `conectar` y `accion` fallan y el estado responde `closed`; la base también lo rechaza | `test_la_revocacion_durante_la_sesion…`, `test_autorizacion_vencida_*`, `test_el_vencimiento_tambien_lo_rechaza_la_base` |
| V7 | Al cerrar la sesión de la cuenta (a mano o por vencimiento) se cierra la sesión técnica con `cierre_sesion` | `test_cerrar_la_sesion_de_la_cuenta_cierra_la_sesion_tecnica` |
| V2 | Lista blanca de órdenes; `probar_bomba` pide planta 1–3 y 1–5 s; resultado y nota (500, obligatoria con «Otro»); filtros y `revision` validados | `test_ordenes_validadas_en_el_servidor`, `test_resolver_valida_resultado_y_nota`, `test_validacion_de_la_correccion` |
| V16 | Auditoría: `atender_caso`, `conectar_sesion`, `crear_comando`, `cerrar_sesion_tecnica`, `resolver_caso`, `corregir_cuidado`, `anular_cuidado` (y `registrar_cuidado`); sin notas, motivos ni correos | `test_flujo_completo_con_auditoria`, `test_auditoria_sin_el_motivo` |
| V1/V3 | Todo dato del servidor entra escapado en las vistas nuevas | suite de Node «flota, consola remota y mantenimientos» |
| Concurrencia | Corregir o anular lleva el número de revisión visto: si otra persona se adelantó, `stale-record` (también si la base lo detecta) | `test_corregir_con_motivo_y_numero_de_revision` |

## 6. Comprobaciones ejecutadas

| Comando | Resultado |
|---|---|
| `python3 backend/tools/pruebas_local.py suite` (base temporal) | 308 pruebas, OK (eran 285) |
| `python3 backend/tools/pruebas_local.py flujos` | 29/29, 45/45 y 56/56 |
| `node frontend/pruebas/pruebas.cjs` | 7 de 7 suites OK |

Cubren: dos administradores (el segundo no puede conectar al caso del primero), revocación durante la sesión, vencimiento de 24 h (con el disparador del caso apagado solo en la prueba), paginación de 28 registros, búsqueda por correo y por huerto, corrección y anulación visibles para la persona, flota sin datos (sin ceros inventados) y con tendencias ponderadas.

## 7. Pendientes y dudas

- **No probado en navegador.** El CSS nuevo (consola, listas) se escribió sin verlo.
- **Las pruebas de Django corren con el rol propietario**, así que no ejercitan las reglas de la base que solo aplican al rol de la aplicación (que el actor coincida con `administrador_id`, `atendido_por_id` y `editor_id`). Revisé que los privilegios del rol cubran lo que hace el código (`UPDATE` por columna en `soporte_caso` y `soporte_sesion`, `INSERT` en `comando`, `cuidado_revision` y `auditoria`), pero falta el recorrido manual con el servidor como `chilito_pkg_runtime`.
- **`#admin/consola`:** el aviso de «Nueva solicitud de soporte» lo escribe una función de la base con ese enlace. No se cambió la base: la interfaz redirige `#admin/consola` a `#admin/soporte`. Cambiar el texto del enlace en la función es una decisión tuya.
- **`ver_flota` no la exige la base** (ni ninguna tabla): solo Django. Y retirar `atender_soporte` no cierra las sesiones abiertas; la base sí rechaza las órdenes siguientes de esa cuenta.
- **Sesión técnica y pestaña:** al salir de la pantalla o cerrar la pestaña se cierra con `keepalive`. Si el cierre no llega, la sesión sigue abierta hasta resolver el caso, cerrar sesión o vencer (24 h); volver a «Conectar» reutiliza la misma.
- **Un administrador, una sesión abierta** (lo impone la base): si intenta conectar otro caso, se le pide cerrar la anterior. Al abrir otro caso en la bandeja, la sesión abierta se cierra.
- **Mantenimientos:** el filtro «Huerto» y el alta usan el número de huerto (no hay lista de todos los huertos); la fecha del alta admite de hoy a 6 días atrás (la base admite 7, pero el mediodía de hace 7 días puede quedar fuera). Corregir no usa `FOR UPDATE` en `cuidado` (el rol no tiene `UPDATE` ahí): la base y su índice único detienen una carrera.
- **Tendencias de flota:** promedio diario de todos los huertos ponderado por las muestras de cada hora, por día de Mérida; un día sin muestras no tiene punto.
- **Órdenes de soporte:** lámpara y ventilador son botones separados (el plan decía menús desplegables). Solo «Reiniciar equipo», «Probar bomba» y «Resolver caso» piden confirmación, como en 5.2.
- **Solicitudes:** se añadió la confirmación al archivar; la búsqueda por correo y las insignias de 5.4 no entraban en esta fase.
- **Cuota:** las rutas de soporte y sesiones tienen 15 operaciones por minuto (alcance técnico); el sondeo de 10 s es de lectura y no la gasta.

## 8. Cómo probarlo a mano

Con el simulador (`backend/tools/simular_equipo.py`) y dos ventanas, una de administrador con `atender_soporte`, `ver_flota` y `gestionar_mantenimientos`, y otra de la persona usuaria:

1. **Flota:** totales, dos gráficas de 7 días y la tabla; filtra por conexión; con `simular_equipo.py … desconectar` y un autodiagnóstico con falla, mira «Problemas recientes».
2. **Consola:** la persona pide «Solicitar revisión técnica» → al administrador le llega el aviso y aparece en «Nuevos» · «Atender» → «Conectar» → lecturas, eventos y órdenes.
3. «Probar bomba» (elige planta y segundos) y «Reiniciar equipo» piden confirmación; con `… atender` el equipo las confirma; la persona ve lo que hizo soporte.
4. La persona pulsa «Revocar acceso» → en menos de 10 s aparece «La persona revocó el acceso. La sesión se cerró.» y la siguiente orden falla.
5. Otro administrador intenta atender o conectar el mismo caso: se lo niega.
6. Conecta, sal de la pantalla (o cierra sesión) y vuelve: la sesión técnica quedó cerrada.
7. «Resolver caso» con «Otro» sin nota (lo pide) y con nota (confirma); el caso pasa a «Resueltos».
8. **Mantenimientos:** busca por correo y por nombre; pasa a la página 2; corrige un cuidado (la persona lo ve «Corregido por soporte») y anúlalo (lo ve «Anulado»); abre el mismo registro en dos pestañas y corrige en ambas: la segunda avisa que está desactualizado.
9. **Archivar** una consulta y **Publicar/Retirar** una guía piden confirmación.
