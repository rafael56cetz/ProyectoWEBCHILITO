# Informe de fase 3 · Flujo de la persona usuaria

Rama: `fase-3-flujo-usuario`.

## 1. Resumen

Una persona puede aceptar textos legales nuevos, crear su huerto, vincular su equipo con un código de 8 caracteres, ver «Mi huerto» en sus tres versiones (A sin huerto, B sin equipo, C con equipo), editar sus plantas y gestionar sus huertos desde Mi cuenta. El backend expone 14 rutas nuevas con propiedad comprobada en el servidor (ids ajenos o inexistentes → 404 idéntico). Se eliminó la vinculación de 26 caracteres con su ayuda por `mailto` y el diagnóstico por reglas de la pantalla anterior. **No se probó en un navegador**: la interfaz se verificó con pruebas de Node sobre modelo y vistas, no con una sesión real.

## 2. Archivos

Creados (los nombra la fase):
- `backend/huerto/api.py`: vistas JSON del huerto, plantas, órdenes y cuidados.
- `backend/huerto/services.py`: lógica de huertos, plantas, órdenes, cuidados y vinculación.
- `backend/datos/api.py`: `legales/aceptar`, `comandos/<id>` y el endpoint del ESP32.
- `backend/huerto/tests.py`: 35 pruebas de Django de esta fase (la fase pide pruebas por endpoint).

Modificados:
- `backend/config/settings/base.py`: lee y valida `CHILITO_VINCULACION_SECRETO` (≥32 bytes); cuota `vincular_dispositivo`.
- `backend/config/urls.py`: rutas nuevas; se quitan las rutas 503 que se reemplazan (`huertos/actual`, `huertos/actual/solicitudes`, `vinculacion`).
- `backend/web/api.py`: `@endpoint` responde 404 `not-found` a `Http404` (decisión del responsable).
- `backend/web/respuestas.py`: los `23514` de esta fase devuelven un `code` propio con mensaje claro; el resto sigue como `regla-de-datos`.
- `backend/privacidad/services.py`: `aceptar_textos`.
- `backend/tests/test_web.py`, `backend/tests/test_configuracion_despliegue.py`, `backend/tools/generar_sql_instalacion.py`: ajustados a las rutas y al secreto nuevos.
- Frontend: `modelos/huerto.js` (`GardenService`, `GardenModel`), `vistas/huerto.js` (`GardenViews`), `controladores/huerto.js` (7 controladores), `controladores/enrutador.js`, `controladores/administracion.js` (`AppController` monta las pantallas nuevas), `modelos/comun.js` (`PrivacyData.acceptLegal`), `modelos/cuenta.js`, `vistas/comun.js` (pestañas de cuenta compartidas), `vistas/cuenta.js` y `controladores/cuenta.js` (aceptación de textos), `modelos|vistas|controladores/equipos.js` (se quita la parte de usuario), estilos (`tokens.css`, `panel.css`, `apariencia.css`), `index.html` (`mvc.5`), `pruebas/pruebas.cjs`.

Eliminados (dentro de archivos existentes):
- `BindingHelp`, `BindingService.consume/normalize`, `BindingViews.userPanel/userStatus/help*`, `BindingUserController`, `BindingHelpController`, `AppViews.gardenLink`.
- `GardenDiagnosis`, `GardenDiagnosisViews` y la tarjeta «Resumen de tu huerto» por reglas (la reemplaza el resumen de IA).
- El bloque «sin huerto → contenido deshabilitado» (`user-locked`, marcador `<!--vincular-huerto-->`) y su CSS (`.garden-link`, `.binding-form`, `.binding-support*`).
- La suite de pruebas «ayuda de vinculación» y las partes de «tarjeta del huerto» que probaban el diagnóstico.

## 3. Líneas

`git diff --shortstat` (sin los 4 archivos nuevos del backend): 26 archivos, +959 / −719.

## 4. Endpoints

Nuevos (todos con sesión, cuenta activa, propiedad del huerto y, en POST, cuota e `Idempotency-Key`, salvo el del ESP32):

| Método y ruta | Qué hace |
|---|---|
| `POST /api/legales/aceptar {documents}` | Guarda las decisiones; solo ids de `chilito_aceptaciones_pendientes()` |
| `GET/POST /api/huertos` | Lista / crea (`name?`) |
| `GET /api/huertos/<id>` | Huerto, 3 plantas con su última `medicion_planta`, métricas, lámpara, último resumen de IA, equipo |
| `POST /api/huertos/<id>/renombrar`, `/archivar` | Renombra / archiva |
| `GET /api/huertos/<id>/ia?page=` | Resúmenes de 30 días |
| `POST /api/huertos/<id>/codigo` | Genera el código `XXXX-XXXX`; cancela el pendiente |
| `GET /api/huertos/<id>/vinculacion` | Estado del código y del equipo (sondeo) |
| `POST /api/huertos/<id>/desvincular` | `chilito_desvincular_dispositivo()` |
| `GET/POST /api/huertos/<id>/plantas/<n>` | Ficha (`?rango=1h/24h/7d/30d`) / edición con `save(update_fields)` |
| `POST /api/huertos/<id>/comandos`, `GET /api/comandos/<id>` | Crea la orden / consulta su estado |
| `POST /api/huertos/<id>/cuidados` | «Registrar recarga» y demás cuidados |
| `POST /api/dispositivos/vincular` | Endpoint del ESP32 |

Eliminados: `/api/huertos/actual`, `/api/huertos/actual/solicitudes` y `/api/vinculacion` (respondían 503). `/api/huertos/actual/avisos|mantenimiento`, `/api/soporte*` y `/api/admin/*` siguen en 503 hasta sus fases.

**Por qué `/api/dispositivos/vincular` no usa sesión ni CSRF.** Lo llama un ESP32, no un navegador: no hay cookies ni sesión, y el token CSRF solo protege peticiones que el navegador acompaña con credenciales ambientales. Aquí la autenticación va en el cuerpo: identificador + credencial del equipo (verificada con el hasher de Django contra `credencial_hash`) + código de un solo uso de 10 minutos (solo se compara su HMAC). `@csrf_exempt` está solo en esta vista. Tiene cuota por IP (20/min) y por identificador (5/min), responde únicamente `{status, result}`, y credencial inválida e identificador desconocido dan la misma respuesta y tardan lo mismo (hash ficticio).

## 5. Seguridad

| Requisito | Cómo se cumple | Prueba |
|---|---|---|
| ASVS V8 propiedad | `_huerto()` filtra por `propietario` y estado activo; `Http404` → 404 `not-found` | `test_otra_cuenta_recibe_404_en_cada_endpoint`, `test_inexistente_y_ajeno_responden_igual` |
| V2 validación | nombre (1–60 / 1–40, imprimible), fecha no futura, etapa, planta 1–3, duración {5,8,10,15,20}, `bool` rechazado | `Plantas.test_validacion`, `Ordenes.test_validacion`, `Huertos.test_nombre_no_valido` |
| V6/V11 código | `secrets.choice`, alfabeto Crockford, solo HMAC-SHA256 con `CHILITO_VINCULACION_SECRETO` en la base | `test_solo_se_guarda_el_hmac_del_codigo` |
| V11 recibo de idempotencia | la clave de respuesta se llama `code`, que `_sin_secretos` vacía: el código no queda en `web_idempotencia` | `test_reintento_con_la_misma_clave_no_devuelve_el_codigo` |
| V4 endpoint del ESP32 | cuota, respuesta mínima, sin distinguir equipo desconocido de credencial mala | `test_cuota_por_identificador`, `test_credencial_invalida_y_equipo_desconocido_responden_igual` |
| V16 auditoría | `crear_huerto`, `renombrar_huerto`, `archivar_huerto`, `generar_codigo`, `desvincular_dispositivo`, `crear_comando`, `registrar_cuidado`, `editar_planta`, `aceptar_legales`; sin nombres ni códigos | `test_auditoria_sin_valores_personales`, `test_solo_se_guarda_el_hmac_del_codigo` |
| V16 errores | los `23514` de esta fase devuelven `huerto-limite`, `huerto-sin-equipo`, `huerto-con-equipo`, `equipo-no-vinculado` | `test_cuarto_huerto…`, `test_segundo_huerto…`, `test_no_archiva_con_equipo` |
| V1/V3 salida | todo dato del servidor entra con `escaparHTML` o `textContent`; ids en rutas solo dígitos | suite de Node «Mi huerto…» |

## 6. Comprobaciones ejecutadas

| Comando | Resultado |
|---|---|
| `manage.py test huerto` (base temporal, vía `pruebas_local.py`) | 35 pruebas, OK |
| `python3 backend/tools/pruebas_local.py suite` (base temporal) | 203 pruebas, OK |
| `node frontend/pruebas/pruebas.cjs` | 6 de 7 suites OK; falla `comercial` (ya fallaba al empezar la fase: lo rehace la fase 5) |

Casos cubiertos: otra cuenta → 404, código vencido, reutilizado, equipo ocupado, cuarto huerto, segundo huerto sin equipo, ESP32 simulado con `Client.post('/api/dispositivos/vincular')` incluido el cierre del paso «Listo».

## 7. Pendientes y dudas

- **No probado en navegador.** Falta recorrer las pantallas con un ESP32 simulado (curl) y revisar el aspecto: el CSS nuevo se escribió sin verlo.
- **Rotar secretos.** Durante la exploración, un volcado del `.env` mostró en claro varias variables `CHILITO_*` (claves de pruebas y `CHILITO_VINCULACION_SECRETO`). Conviene rotarlas si este historial se comparte.
- **Paginación del resumen de IA:** el endpoint usa `?page=` (el ayudante común) y no `?pagina=` como escribe la fase. La pantalla pide solo la primera página (25 resúmenes).
- **Código visible junto a las instrucciones:** el plan separa la pantalla del código (3.8) del paso 2; aquí se muestran juntas (código grande con contador, copiar y las instrucciones al lado). No hay botón «Ya lo tengo, continuar».
- **Fecha de siembra:** se usa `<input type="date">` con `max` de hoy, no el calendario `DateFilterViews` (pensado para rangos y con marcado propio).
- **«Registrar un cuidado» y «Registrar cuidado»** enlazan a `#mantenimiento` sin formulario abierto: esa pantalla es de la fase 4.
- **Gráfica del Panel técnico:** `--garden-green` valía `#fff` en el panel; ahora vale `var(--claro-verde)` (`tokens.css`). Corrige la línea blanca de FASE-2, pero cambia el color de la línea de las gráficas, de íconos `.user-metric-icon` y del `accent-color` de `.user-consent`. Hay que mirarlo en pantalla.
- **Pantallas de la fase 4** (Panel técnico, Mantenimiento, Soporte) siguen llamando a `/api/huertos/actual*`, que ya no existe: muestran su estado de error hasta que se rehagan, como antes (antes era 503).
- **Selección de huerto:** `?h=<id>` manda; si no, el último elegido en la visita (en memoria, no se guarda); si no, el primero. Solo Mi huerto, crear, vincular y planta aceptan `?h=` por ahora.
- **Cuarto huerto:** la base ya limita a 3 huertos activos y a 1 sin equipo; la interfaz lo muestra en el selector y en Mis huertos.
- La campana sigue sin contador (fase 4).

## 8. Cómo probarlo a mano

1. Publicar desde pgAdmin un término 1.1 e iniciar sesión → aparece «Actualizamos nuestros documentos»; sin marcar las casillas el botón está desactivado; ninguna otra ruta privada abre.
2. Cuenta sin huerto → «Aún no tienes un huerto» → «Crear mi huerto» (con y sin nombre).
3. Se abre el asistente: «Generar código» → `XXXX-XXXX` con cuenta regresiva.
4. Simular el ESP32: `curl -X POST /api/dispositivos/vincular -H 'Content-Type: application/json' -d '{"identifier":"…","credential":"…","code":"XXXX-XXXX"}'` → la pantalla pasa a «¡Tu equipo quedó vinculado!» en menos de 5 s.
5. Mi huerto con equipo: métricas «Sin lectura» mientras no haya mediciones, tarjeta de orden al pedir «Revisar mi equipo», confirmación al apagar la lámpara.
6. «Ver planta» → editar nombre, fecha y etapa; ver la línea de vida; «Regar esta planta».
7. Crear un 2.º huerto sin vincular el 1.º → debe impedirlo; con equipo en el 1.º, aparece el selector.
8. Mi cuenta → Mis huertos: renombrar, desvincular (con confirmación), archivar.
