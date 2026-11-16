# Matriz de seguridad · fases 1 a 7

Qué requisito de OWASP ASVS 5.0.0 o de NIST SSDF 1.1 se cumple, dónde está en el código y qué prueba automática lo verifica. Solo aparece en la primera tabla lo que tiene una prueba que corre; lo que se comprobó solo leyendo el código está en la segunda tabla y no se declara como probado.

Las pruebas de Django están en `backend/` (`tests/`, `datos/tests/`, `huerto/tests.py` y `privacidad/tests.py`); las de la interfaz, en `frontend/pruebas/pruebas.cjs` (se citan por el nombre de su suite). Las de la base están en `sql/pruebas/`.

## 1. Con prueba automática

| Requisito | Dónde se implementa | Prueba que lo verifica |
|---|---|---|
| ASVS V8 · actor en cada escritura | `web/middleware.py` (`ActorDeBase`): `set_config('chilito.actor_id', id, true)` en la transacción de la petición | `tests.test_web.ActorEnLaTransaccion` |
| V8 · capacidad y segundo factor en cada endpoint | `web/api.py` (`endpoint(cap=…)`) y `require_cap` en `web/services.py` | `Sesion.test_las_capacidades_son_independientes`; `Capacidades.test_sin_sesion_sin_capacidad_y_sin_factor` (`datos/tests/test_admin.py`, ahora con las rutas de flota, consola y mantenimientos); `test_la_capacidad_de_otra_pantalla_no_sirve` |
| V8 · propiedad del recurso (huertos, soporte, avisos, telemetría, cuidados) | `huerto/services.py` (`_huerto()` filtra por propietario), `datos/services.py` | `test_otra_cuenta_recibe_404_en_cada_endpoint`, `test_inexistente_y_ajeno_responden_igual`, `test_no_adjunta_el_autodiagnostico_de_otra_cuenta` |
| V8 · solo quien atiende el caso opera la consola | `datos/services.py` (consola) | `test_el_segundo_admin_no_conecta_ni_opera_ni_resuelve_el_caso_del_primero`, `test_sin_atender_no_se_conecta_ni_se_resuelve` |
| V8 · autorización de soporte vigente en cada orden | `datos/services.py`; la base también lo rechaza | `test_la_revocacion_durante_la_sesion…`, `test_el_vencimiento_tambien_lo_rechaza_la_base` |
| V8 · el administrador no se da a sí mismo capacidades ni `gestionar_administradores` | `datos/services.py` (administradores) | `test_no_deja_dar_gestionar_administradores`, `test_no_deja_cambiar_las_propias_capacidades`, `test_cuenta_sin_correo_verificado…` |
| V7 · la sesión técnica se cierra con la sesión de la cuenta | `datos/apps.py` (`user_logged_out`) | `test_cerrar_la_sesion_de_la_cuenta_cierra_la_sesion_tecnica` |
| V2 · validación en el servidor (tipos, longitudes, listas blancas) | `web/api.py` (`leer_json`), servicios de cada app, CHECK de la base | `Escrituras.*`, `Plantas.test_validacion`, `Ordenes.test_validacion`, `Huertos.test_nombre_no_valido`, `test_ordenes_validadas_en_el_servidor`, `test_resolver_valida_resultado_y_nota`, `test_validacion_de_la_correccion` |
| V2 · concurrencia: registro desactualizado | `huerto/services.py` (corregir y anular con número de revisión) | `test_corregir_con_motivo_y_numero_de_revision` |
| V6 · eliminar la cuenta exige la contraseña | `datos/services.py` | `EliminarCuenta.test_exige_la_contrasena`, `test_solicitar_y_cancelar` |
| V6/V11 · código de vinculación: aleatorio, solo su HMAC | `huerto/services.py` (`CHILITO_VINCULACION_SECRETO`) | `test_solo_se_guarda_el_hmac_del_codigo` |
| V11/V13 · el código y la credencial no quedan en el recibo de idempotencia | `web/services.py` (`_sin_secretos`) | `test_reintento_con_la_misma_clave_no_devuelve_el_codigo`, `test_alta_muestra_la_credencial_una_vez…`, `test_rotar_credencial` |
| V13 · secretos exigidos y de 32 bytes o más | `config/settings/base.py` (`CHILITO_IDEMPOTENCIA_SECRETO`, `CHILITO_VINCULACION_SECRETO`) | `tests.test_configuracion_despliegue` |
| V4 · endpoint del equipo: cuota y respuesta que no distingue causas | `datos/api.py` (`link_device`) | `test_cuota_por_identificador`, `test_credencial_invalida_y_equipo_desconocido_responden_igual` |
| V1/V3 · texto legal saneado en el servidor | `privacidad/legales.py` (`sanear_html`), `privacidad/documentos_html.py` | `test_vista_previa_y_detalle…`; `privacidad.tests` (`html` de los documentos) |
| V1/V3 · exportación CSV sin inyección de fórmulas | `privacidad/consentimientos.py` | `test_exportar_csv_sin_inyeccion…`, `test_celda_neutraliza_cada_caracter_peligroso` |
| V1/V3 · datos del servidor entran escapados en las vistas | `escaparHTML` y `textContent` en `frontend/vistas/*.js` | Node: «administración…texto escapado», «flota, consola remota y mantenimientos», «Mi huerto (A, B y C)…» (incluye, en la fase 7, la etapa y el origen del riego de una planta) |
| V1/V3 · los controladores no escriben el DOM; las vistas no llaman al servidor | estructura MVC del frontend | Node: «MVC: controladores sin escrituras al DOM» |
| V14 · IP recortada y navegador resumido | `privacidad/services.py` | `Registro.test_ip_recortada`, `test_navegador_resumido…`, `CookiesPermanecen.test_la_bitacora…` |
| V14 · exportar consentimientos exige capacidad y se audita | `privacidad/consentimientos.py` | `test_exportar_exige_ver_consentimientos`, `test_bitacora_con_filtros…` |
| V16 · errores sin trazas; los `23514` se traducen | `web/respuestas.py` | `ReglasDeLaBase.*`, `test_cuarto_huerto…`, `test_segundo_huerto…`, `test_no_archiva_con_equipo` |
| V16 · auditoría sin valores personales | `auditar` en cada servicio | `test_auditoria_sin_valores_personales`, `test_flujo_completo_con_auditoria`, `test_auditoria_sin_el_motivo`, `PerfilYMisDatos` (privacidad) |
| V16 · intentos fallidos sí consumen la cuota | `datos/services.py` (cuota antes de la transacción) | `test_cuota_de_intentos` |
| V9/V10 (acceso y segundo factor, sin cambios en estas fases) | `cuentas/` | `tests.test_auth`, `tests.test_segundo_factor`; flujos `probar_seguridad.py` (29), `probar_mfa.py` (45), `probar_privacidad.py` (56) |
| Base de datos: reglas, roles y triggers | `sql/` y migraciones | `sql/pruebas/pruebas_v2.py` (149), `prueba_depuracion.py`; `makemigrations --check` |
| SSDF PW.8 · pruebas ejecutadas antes del cierre | `backend/tools/pruebas_local.py`, `frontend/pruebas/pruebas.cjs` | resultados en `docs/informes/FASE-7.md` §6 |
| SSDF PO/PS · el simulador solo corre en desarrollo o pruebas | `backend/tools/simular_equipo.py` | `SimuladorDeEquipoEntorno`, `SimuladorDeEquipo` |

## 2. Comprobado solo leyendo el código (sin prueba automática)

| Requisito | Qué se revisó | Por qué no hay prueba |
|---|---|---|
| ASVS V3 · CSP intacta, sin estilos ni scripts en línea nuevos | Fase 2: el diff no tocó `web/middleware.py` ni añadió `style=`/`<script` | No hay prueba de la CSP en el repositorio; el responsable la miró en el navegador |
| SSDF PW.4 · reutilización de componentes existentes | Revisión de los diffs de las fases | Es una práctica de revisión, no un comportamiento |
| SSDF PW.5 · solo ORM o SQL parametrizado | Revisión de los diffs | Sin prueba que busque SQL armado con texto |
| SSDF PW.7 · revisión de código | Revisión propia de cada diff y, en la fase 7, de los 44 `innerHTML` (tabla en el informe) | Revisión manual |
| V8 · rol `chilito_pkg_runtime` en los endpoints de consola, flota y mantenimientos | Privilegios del rol leídos contra el código | Las pruebas de Django corren con el propietario; falta el recorrido manual con el rol de la aplicación |
| SSDF PS.3 · registro de versión | Commit por fase e informe en `docs/informes/` | Es un registro, no un comportamiento |
| SSDF RV.1 · registro de pendientes | Sección «Pendientes» de cada informe | Es un registro, no un comportamiento |

## 3. No cubierto

- `pip-audit` no está instalado en el entorno: las vulnerabilidades conocidas de las dependencias no se comprobaron.
- La contraseña, el segundo factor y la recuperación de acceso (V6, V7, V9, V10) pertenecen al flujo de acceso, que las fases 1 a 7 no modificaron; solo se cita su prueba existente.
- La comparación visual de la fase 7 queda a cargo del responsable.
