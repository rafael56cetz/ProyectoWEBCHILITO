# Informe de fase 4 · Operación de la persona usuaria

Rama: `fase-4-operacion-usuario` (creada sobre `fase-3-flujo-usuario`).

## 1. Resumen

Panel técnico, Mantenimiento, Soporte (sin token, con autodiagnóstico) y Avisos funcionan con datos reales del huerto elegido (`?h=`), con el contador en la campana de todas las pantallas privadas y el aviso fijo de eliminación pendiente. En Mi cuenta › Privacidad se agregaron «Documentos que aceptaste» y «Eliminar mi cuenta» (pide la contraseña). El administrador ya puede abrir `#avisos` y ver su contador. Se agregó `backend/tools/simular_equipo.py` para probar sin ESP32. **No se probó en un navegador**: la interfaz se verificó con pruebas de Node sobre modelo y vistas.

## 2. Archivos

Creado (lo nombra la fase):
- `backend/tools/simular_equipo.py`: simulador de equipo (rol `chilito_pkg_iot`, solo desarrollo).

Modificados (backend):
- `datos/services.py`: propiedad del huerto (`huerto_propio`), soporte (abrir, revocar, cancelar, autodiagnóstico), avisos y contador; `deletionRequestedAt`/`deletionDate` en el perfil.
- `datos/api.py`, `huerto/api.py`, `privacidad/api.py`, `config/urls.py`: endpoints nuevos; se quitan los 503 de avisos, mantenimiento y soporte del usuario.
- `huerto/services.py`: telemetría, bitácora, cuidados con la última revisión vigente, registrar cuidado con fecha; todas las funciones usan `huerto_propio`. `_serie` ahora toma los puntos **más recientes** (antes tomaba los más antiguos si pasaba de 1500).
- `privacidad/services.py`: documentos aceptados, solicitar y cancelar eliminación.
- `web/respuestas.py`: los índices únicos de caso activo y de orden en curso (23505) responden `caso-activo` y `orden-en-curso`.
- `config/settings/base.py`: cuota `eliminar_cuenta` (5/min por usuario).
- `tools/armar_entrega.py` y `tools/README.md`: el simulador se prohíbe en la entrega a la nube y se documenta.
- Pruebas: `huerto/tests.py`, `privacidad/tests.py`, `tests/test_web.py`.

Modificados (frontend):
- `modelos/huerto.js`: `GardenService` y `GardenModel` con lo nuevo; **se elimina `UserGardenService`**.
- `vistas/huerto.js`: `TechnicalViews`, `CareViews`, `SupportViews`, gráfica de varias series (`lineChart`); **se elimina `UserGardenViews`**.
- `controladores/huerto.js`: `TechnicalController`, `CareController`, `SupportController`, `GardenSectionController`, `GardenContext`; **se elimina `UserGardenController`**.
- `modelos/comun.js`, `vistas/comun.js`, `controladores/administracion.js` (`AppController`): avisos con filtros, paginación y detalle; campana con contador; aviso fijo de eliminación. Se eliminan `AppModel.garden`, `AppModel.states`, las lecturas del contrato viejo, `AppViews.assistant/reading/readingNote`.
- `controladores/enrutador.js`: `?h=` en todas las pantallas del huerto; el administrador abre `#avisos`.
- `vistas/cuenta.js`, `controladores/cuenta.js`: documentos aceptados y eliminar cuenta.
- `modelos/administracion.js`, `modelos/cuenta.js`, `vistas/administracion.js`: ajustes por las referencias eliminadas.
- Estilos: `tokens.css` (tres colores de serie), `panel.css`, `apariencia.css` (se borran las reglas de `user-token*`, `user-permission`, `user-support-*`, `notice-card` y otras 12 clases sin uso). `index.html`: recursos `mvc.6`. `pruebas/pruebas.cjs` adaptado.

Eliminados: todo el token de soporte del usuario (emisión, copia, `mailto`, textos, cuenta regresiva), el selector de periodo que no filtraba, los estados que el backend nunca enviaba y el diálogo de consentimiento viejo.

## 3. Líneas

`git diff --shortstat`: 31 archivos modificados, +2023 / −697, más el archivo nuevo del simulador.

## 4. Endpoints

Nuevos (sesión, cuenta activa y propiedad en cada uno; ajeno o inexistente → 404 idéntico):

| Ruta | Qué hace |
|---|---|
| `GET /api/huertos/<id>/telemetria?rango=1h|24h|7d|30d` | Series y lecturas por planta (con ADC). 1h/24h de `medicion*`; 7d/30d de `resumen_hora_*` con mín/máx |
| `GET /api/huertos/<id>/bitacora?tipo=ordenes|actuaciones|eventos&page=` | Bitácora de 25 en 25 |
| `GET /api/huertos/<id>/cuidados?planta&tipo&desde&hasta&page=` | Historial con la última revisión vigente |
| `POST /api/huertos/<id>/cuidados` | Ampliado: `plant`, `doneAt` (hasta 7 días atrás) y `chiles` |
| `GET/POST /api/huertos/<id>/soporte` | Caso activo, historial, órdenes de soporte, última revisión / abrir caso |
| `POST /api/soporte/<caso>/revocar`, `/cancelar` | Solo el solicitante |
| `GET /api/autodiagnosticos/<id>` | Con sus 12 revisiones en el orden de 3.7 |
| `GET /api/avisos?filtro=&page=`, `GET /api/avisos/<id>` | Lista y detalle |
| `POST /api/avisos/<id>/leido`, `/resuelto`, `POST /api/avisos/leer-todos`, `GET /api/avisos/contador` | Resolver solo críticos del equipo |
| `GET /api/cuenta/aceptaciones` | Términos y aviso aceptados |
| `POST /api/cuenta/eliminar {password}`, `POST /api/cuenta/eliminar/cancelar` | Pide/cancela el borrado (15 días) |

`POST /api/huertos/<id>/comandos` y `GET /api/comandos/<id>` ahora devuelven `diagnosticId` en las órdenes de autodiagnóstico. Eliminados los 503 de `api/huertos/actual/avisos*`, `api/huertos/actual/mantenimiento` y `api/soporte*` (usuario). Siguen en 503 los `api/admin/*`.

## 5. Seguridad

| Requisito | Cómo se cumple | Prueba |
|---|---|---|
| ASVS V8 | Todo se busca por dueño, solicitante o destinatario; revocar y cancelar solo el solicitante; un aviso ajeno no se lee ni se marca | `test_otra_cuenta_recibe_404` en soporte, avisos, telemetría, bitácora y cuidados; `test_no_adjunta_el_autodiagnostico_de_otra_cuenta` |
| V6 | Eliminar la cuenta exige `check_password`; la fecha siempre es `now()` (la base no la valida) | `EliminarCuenta.test_exige_la_contrasena`, `test_solicitar_y_cancelar` |
| V2 | Listas blancas de `rango`, `tipo`, `filtro`, `planta`, fechas ISO con `desde<=hasta`, `page` 1–10000, consentimiento `True` estricto, nota ≤ 500 | `test_validacion_*`, `test_filtros_no_validos`, `test_sin_consentimiento_o_con_datos_no_validos` |
| V16 | Auditoría de `abrir_caso`, `revocar_soporte`, `cancelar_caso`, `solicitar_eliminacion`, `cancelar_eliminacion`, sin contraseña ni notas | `test_abrir_revisar_y_auditar`, `test_revocar_deja_el_caso_abierto…`, `test_solicitar_y_cancelar` |
| Cuota real | La cuota de `eliminar_cuenta` se gasta **antes** de la transacción de la escritura: un intento fallido ya no se revierte con ella | `test_cuota_de_intentos` |
| V1/V3 | Todo dato del servidor entra con `escaparHTML`; ids de ruta solo dígitos o UUID | suite «Mi huerto…» y «contrato de adaptadores» (Node) |
| SSDF PO/PS | El simulador exige `CHILITO_ENV=local|testing` y `CHILITO_DEBUG=1`, solo escribe en bases de desarrollo o de pruebas, usa variables propias y se prohíbe en la entrega | `SimuladorDeEquipoEntorno`, `SimuladorDeEquipo` |

Hallazgo corregido durante la fase: consumir una cuota **dentro** de la transacción de idempotencia (la caché de cuotas vive en la base) deshacía el contador cuando la petición fallaba, así que los intentos fallidos no contaban. El endpoint del ESP32 de la Fase 3 no tenía el problema (no usa esa transacción).

## 6. Comprobaciones ejecutadas

| Comando | Resultado |
|---|---|
| `python3 backend/tools/pruebas_local.py suite` (base temporal) | 243 pruebas, OK (eran 203) |
| `python3 backend/tools/pruebas_local.py flujos` | 29/29, 45/45 y 56/56 |
| `node frontend/pruebas/pruebas.cjs` | 5 de 6 suites OK; falla `comercial` (ya fallaba desde la Fase 1; la rehace la fase 5) |

Incluye: dos cuentas por endpoint (la ajena recibe 404); el contador baja al marcar leído (`test_el_contador_baja_al_marcar_leido`); el simulador contra la base de pruebas con el rol IoT real (mediciones, riego confirmado con su actuación, lámpara, autodiagnóstico completado antes de confirmar, orden fallida, equipo desconectado, evento `simulador`).

## 7. Pendientes y dudas

- **No probado en navegador.** El CSS nuevo (campana, avisos, diagnóstico, gráfica de tres series) se escribió sin verlo. Falta el recorrido manual de la sección 8.
- **`?page=` y no `?pagina=`** en bitácora, cuidados y avisos (decisión tuya): es el nombre del ayudante común y de `/api/huertos/<id>/ia`.
- **`CHILITO_SUPPORT_KEY` no se borró**: no es del token (que nunca existió en el backend) sino la clave HMAC de la idempotencia de todos los POST. Su nombre engaña: el renombre de `CHILITO_SUPPORT_KEY` pasa a la **fase 7**.
- **Lado administrador, sin tocar:** `AdminService.validateToken` (y `api/admin/soporte/…/abrir`, que sigue en 503) y el enlace `#admin/consola` que la base pone en los avisos de caso nuevo (una ruta que no existe; el menú usa `#admin/soporte`) pasan a la **fase 6**.
- **Cancelar la eliminación no tiene ventana en la base:** se puede mientras no se anonimice (hasta una hora después de los 15 días). Django siempre usa `now()`/`NULL`.
- **Tarea periódica ausente en desarrollo:** sin ella, las órdenes sin respuesta no pasan a «Sin respuesta» y los rangos 7 y 30 días salen vacíos. El simulador llama `chilito_resumir_mediciones` al medir.
- **Mantenimiento:** «Registrar cuidado» de la ficha de planta lleva a `#mantenimiento` sin la planta preseleccionada. Los filtros de fecha reutilizan `DateFilterViews`, que depende del marcado del calendario de `MaintenanceViews` (lado administrador).
- **Soporte:** «vence en…» se calcula al pintar; con un caso activo se vuelve a consultar cada 15 s (hasta 10 min) en segundo plano.
- **`--garden-green`:** de sus usos fuera de la gráfica, `.user-metric-icon` y `.user-status-line` ya tenían color propio en `apariencia.css`; `.user-diagnosis-mark` y los íconos de `.user-history-list` eran blancos sobre fondo casi blanco y ahora se ven en verde. No quedó ningún uso que dependiera del blanco. El selector de huertos usa `--garden-tint`, que no cambió.
- **Entrega a la nube:** `armar_entrega.py` prohíbe `simular_equipo.py`; las pruebas del simulador se omiten si la copia no lo incluye.

## 8. Cómo probarlo a mano

Variables del simulador (en tu terminal; no usa las de la app):
`CHILITO_ENV=local CHILITO_DEBUG=1 CHILITO_SIM_DB=chilito_integracion_sinteticos CHILITO_SIM_CLAVE_IOT=<clave de chilito_pkg_iot>`

1. Con el equipo vinculado a un huerto: `python3 backend/tools/simular_equipo.py CHI-PRUEBA-0001 conectar`, luego `… medir --n 12 --intervalo 300 --luz`.
2. **Panel técnico:** gráficas de 1 h a 30 días, tabla con ADC, Luz solo si hay lecturas; cambia de periodo y de huerto.
3. **Regar:** pide un riego y en otra terminal `… atender` → «Pendiente» → «Enviada» → «Confirmada»; con `--fallar regar`, «Falló». La bitácora de órdenes y actuaciones se actualiza.
4. **Soporte:** «Revisar mi equipo» + `… atender --falla bomba_2` → «Encontramos 1 problema». Solicita revisión con consentimiento; revoca y cancela con confirmación.
5. **Mantenimiento:** registra con planta y fecha pasada; filtra por planta, tipo y fechas. Un cuidado anulado o corregido desde la base aparece tachado o con su insignia.
6. **Avisos:** desconecta el equipo (`… desconectar`); la campana muestra el contador; abre un aviso (baja), marca todo como leído; entra como administrador y abre `#avisos`.
7. **Cuenta › Privacidad:** documentos aceptados; eliminar mi cuenta con contraseña incorrecta y correcta (aparece el aviso ámbar en todas las pantallas) y cancelar.
