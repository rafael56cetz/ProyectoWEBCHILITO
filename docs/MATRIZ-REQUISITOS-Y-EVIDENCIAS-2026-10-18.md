# Matriz de requisitos y evidencias · entrega del 19 de octubre

**Revisión:** 18 de octubre de 2026. **Código evaluado:** fab3193075b7b3ac5c1fded558a636d2cd43a5fb. **Entregable:** E19-02.

Se actualizaron los 13 requisitos seleccionados previamente. La revisión contrasta código, documentos y resultados existentes del CI; no ejecutó una nueva auditoría ni modificó la aplicación.

## Interpretación y alcance

- **Verificado local:** las pruebas y la revisión citadas respaldan el comportamiento en el alcance indicado. No acredita conformidad global ni de un nivel ASVS.
- **Parcial:** existe implementación o evidencia útil, pero falta demostrar una parte expresa del requisito.
- **Pendiente de evaluación:** no se ha decidido o verificado su aplicación; no significa no aplicable.

**Selección:** 13 aplicables, 7 verificados localmente y 6 parciales. **Catálogo:** 345 requisitos; 332 pendientes de evaluación y ninguno declarado no aplicable. Son 70 de nivel mínimo L1, 183 L2 y 92 L3. L2 se conserva como objetivo propuesto sin demostrar: requiere evaluar al menos los 253 requisitos L1/L2 y los riesgos adicionales pertinentes. No se calcula cobertura global a partir de esta selección.

## Evidencia común

- [CI aprobado: 127 pruebas del servidor, configuración, migraciones y sintaxis JavaScript](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [Matriz completa CSV](ASVS-5.0.0-ALCANCE-LOCAL.csv).
- [Registro estructurado: resultados y correspondencias](EVIDENCIA-MATRIZ-ASVS-2026-10-18.json).
- [Estado anterior de la matriz](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/docs/ASVS-5.0.0-ALCANCE-LOCAL.csv).

Los tests del CI usan PostgreSQL aislado, rol limitado y correo en memoria. No acreditan recepción Gmail, pruebas en teléfono físico, hardware ni auditoría WSTG completa. Los documentos del 17 se conservan como históricos; no se cuentan como ejecuciones nuevas.

## Tabla de resultados

| ID interno / ASVS | Nivel / historia | Requisito | Resultado | Límite |
| --- | --- | --- | --- | --- |
| AS-01 / v5.0.0-1.2.1 | L1 / HU-01; HU-02 | Codificar los valores dinámicos según su contexto de salida. | Parcial | Falta inventario de contextos HTML/atributo/URL y pruebas con entradas maliciosas en el DOM; sintaxis JavaScript no prueba resistencia XSS. |
| AS-02 / v5.0.0-2.2.1 | L1 / HU-01; HU-02 | Validar en servidor las entradas que deciden seguridad y reglas de negocio. | Verificado local | Verificado para las entradas críticas enumeradas, al nivel de alcance L1 de este requisito. No se ha inventariado toda entrada requerida por L2. |
| AS-03 / v5.0.0-3.3.4 | L2 / HU-01 | Proteger el identificador de sesión de la lectura por scripts y entregarlo mediante Set-Cookie. | Verificado local | No demuestra el atributo Secure ni HTTPS: el perfil HTTP de loopback mantiene Secure desactivado. Ese transporte es otro requisito. |
| AS-04 / v5.0.0-3.5.1 | L1 / HU-01; HU-02 | Rechazar solicitudes sensibles que no acrediten su origen mediante la protección CSRF. | Verificado local | Evaluación de las rutas web actuales. No incluye APIs IoT futuras ni una app instalada. |
| AS-05 / v5.0.0-6.3.1 | L1 / HU-01 | Aplicar controles documentados contra intentos de autenticación abusivos. | Parcial | Faltan pruebas de credential stuffing distribuido, efectividad bajo concurrencia/varias cuentas, recuperación tras ventanas y monitoreo operativo; la cuota por IP en loopback no representa una red pública. |
| AS-06 / v5.0.0-6.4.3 | L2 / HU-01 | Recuperar una contraseña mediante un proceso seguro sin eludir factores habilitados. | Verificado local | No hay MFA ni passkeys habilitados; no se ha demostrado recuperación para esos factores. El correo del CI es en memoria y no acredita entrega Gmail. |
| AS-07 / v5.0.0-7.2.1 | L1 / HU-01; HU-02 | Validar la sesión mediante el servicio confiable del backend. | Verificado local | La estructura genérica del dashboard visible sin membresía no es información privada ni un permiso de consulta. |
| AS-08 / v5.0.0-7.2.4 | L1 / HU-01 | Renovar el identificador de sesión al autenticar y terminar el identificador anterior. | Parcial | El requisito incluye reautenticación. No se ha demostrado un recorrido específico de reautenticación y rotación para todos los cambios de privilegio/factor. |
| AS-09 / v5.0.0-7.4.1 | L1 / HU-01 | Impedir reutilizar una sesión una vez terminada por cierre o vencimiento. | Parcial | El cierre se demostró. Falta prueba explícita de vencimiento de la sesión en servidor; cerrar un navegador no acredita por sí solo caducidad ni revocación. |
| AS-10 / v5.0.0-8.2.1 | L1 / HU-01; HU-02 | Restringir funciones a cuentas con permisos explícitos. | Verificado local | No se evalúan funciones inexistentes de mando de bombas, IA, ARCO ni vinculación real. |
| AS-11 / v5.0.0-8.2.2 | L1 / HU-01; HU-02 | Restringir cada dato u objeto a la identidad y permisos correspondientes. | Verificado local | Los registros lógicos adicionales solo son fixtures transaccionales de pruebas; no implican construir otro dispositivo físico. |
| AS-12 / v5.0.0-13.3.1 | L2 / HU-01; HU-02 | Gestionar creación, almacenamiento, acceso y retirada de secretos fuera de código y artefactos. | Parcial | No hay ciclo completo documentado y ensayado de rotación, revocación y destrucción; tampoco se verificó la historia completa de Git ni todas las copias/respaldos. |
| AS-13 / v5.0.0-16.2.5 | L2 / HU-01; HU-02 | Excluir, enmascarar o limitar datos sensibles de acuerdo con su nivel de protección al registrar eventos. | Parcial | Las pruebas de respuesta no prueban por sí mismas el contenido de todos los logs. Falta capturar y revisar registros de proceso/proxy/dependencias y documentar clasificación/retención. Silenciar logs tampoco demuestra auditoría de seguridad. |

Se conservan las historias existentes: **HU-01, acceso y cierre**, y **HU-02, consulta del huerto**. Su backlog y el enlace detallado de criterios se completarán en la tarea posterior acordada.

## Detalle y trazabilidad

### AS-01 · v5.0.0-1.2.1 · Parcial

**Requisito del hito:** Codificar los valores dinámicos según su contexto de salida. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** Las vistas de acceso, perfil y avisos insertan valores que podrían contener marcado.

**Implementación:** authEscape escapa los cinco caracteres HTML; las vistas de cuenta y avisos lo reutilizan y los mensajes usan textContent.

**Código revisado:** [dist/vista/acceso.js](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/dist/vista/acceso.js), [dist/vista/aplicacion.js](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/dist/vista/aplicacion.js), [dist/controlador/acceso.js](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/dist/controlador/acceso.js).

**Casos ejecutados:**
- [tests.test_garden_integration.GardenIntegrationTests.test_garden_projects_persisted_names_and_no_physical_readings](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L78) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** Texto legítimo se muestra conservando su significado.

**Esperado negativo:** Marcado y comillas se muestran como texto sin ejecutar código; caso adversario aún pendiente.

**Resultado observado:** Se revisó el escape existente y pasó el transporte de nombres persistidos. Esa prueba no envía contenido XSS.

**Límite que justifica el estado:** Falta inventario de contextos HTML/atributo/URL y pruebas con entradas maliciosas en el DOM; sintaxis JavaScript no prueba resistencia XSS.

**Siguiente verificación:** Probar valores con marcado, comillas y URLs en cada salida dinámica dentro de una base aislada.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-02 · v5.0.0-2.2.1 · Verificado local

**Requisito del hito:** Validar en servidor las entradas que deciden seguridad y reglas de negocio. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** Contraseña, casilla, identidad, identificador de aviso y relaciones entre zona, huerto y lectura afectan decisiones.

**Implementación:** Formularios Django/allauth, casilla booleana literal, ID con patrón/rango, identidad tomada de sesión y restricciones PostgreSQL.

**Código revisado:** [backend/cuentas/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/cuentas/api.py), [backend/cuentas/inputs.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/cuentas/inputs.py), [backend/huerto/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/huerto/api.py), [backend/huerto/migrations/0004_relaciones_avisos.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/huerto/migrations/0004_relaciones_avisos.py).

**Casos ejecutados:**
- [tests.test_local_registration.LocalRegistrationTests.test_signup_exact_password_code_session_and_no_automatic_membership](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_local_registration.py#L85) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_local_registration.LocalRegistrationTests.test_checkbox_requires_literal_boolean_true](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_local_registration.py#L66) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_local_registration.LocalRegistrationTests.test_server_rejects_invalid_passwords_even_without_frontend](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_local_registration.py#L106) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_garden_integration.GardenIntegrationTests.test_invalid_ids_are_neutral_not_found](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L149) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_garden_integration.GardenIntegrationTests.test_read_cannot_choose_another_user](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L180) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_garden_integration.GardenIntegrationTests.test_zone_from_another_garden_rejected_even_bypassing_model_clean](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L203) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** Alta, contraseña y lectura con valores válidos se aceptan.

**Esperado negativo:** Casilla no booleana, ID inválido, contraseña fuera de política o relación cruzada se rechazan.

**Resultado observado:** Alta válida y verificación aceptadas en aislamiento; casillas no booleanas, contraseñas inválidas, IDs fuera de rango, usuario impuesto y relaciones cruzadas rechazados.

**Límite que justifica el estado:** Verificado para las entradas críticas enumeradas, al nivel de alcance L1 de este requisito. No se ha inventariado toda entrada requerida por L2.

**Siguiente verificación:** Ampliar inventario a cada endpoint nuevo e integración IoT. La selección completa L2 permanece pendiente.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-03 · v5.0.0-3.3.4 · Verificado local

**Requisito del hito:** Proteger el identificador de sesión de la lectura por scripts y entregarlo mediante Set-Cookie. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** La aplicación usa sesión de navegador, sin necesidad de exponer un token de aplicación a JavaScript.

**Implementación:** Django usa cookie de sesión HttpOnly y sesiones en PostgreSQL; el frontend lee solo csrftoken para CSRF.

**Código revisado:** [backend/config/settings/base.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/settings/base.py), [backend/config/urls.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/urls.py), [dist/modelo/servicio-acceso.js](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/dist/modelo/servicio-acceso.js).

**Casos ejecutados:**
- [tests.test_access_integration.AccessIntegrationTests.test_session_restores_in_another_client_and_logout_revokes_it](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L92) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_allauth_compatibility.AllauthCompatibilityTests.test_browser_session_has_no_app_token](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_allauth_compatibility.py#L8) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_code_metadata_does_not_consume_attempts_or_expose_code](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L128) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** La cookie permite recuperar sesión con HttpOnly.

**Esperado negativo:** No se entrega identificador de sesión mediante un token de aplicación en JSON ni se permite su lectura JavaScript prevista.

**Resultado observado:** Cookie de sesión HttpOnly comprobada y sesión recuperable por cookie; la respuesta de sesión de navegador no expone session_token. La revisión de rutas/código no encontró otro canal previsto para ese identificador.

**Límite que justifica el estado:** No demuestra el atributo Secure ni HTTPS: el perfil HTTP de loopback mantiene Secure desactivado. Ese transporte es otro requisito.

**Siguiente verificación:** Revalidar cookies y canales de respuesta al añadir otro cliente o pasar a HTTPS.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-04 · v5.0.0-3.5.1 · Verificado local

**Requisito del hito:** Rechazar solicitudes sensibles que no acrediten su origen mediante la protección CSRF. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** Login, registro, cierre, recuperación, contraseña y marcar aviso son operaciones sensibles.

**Implementación:** CsrfViewMiddleware activo, token X-CSRFToken del mismo origen, métodos de mutación explícitos y sin CORS abierto.

**Código revisado:** [backend/config/settings/base.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/settings/base.py), [backend/config/urls.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/urls.py), [backend/huerto/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/huerto/api.py), [dist/modelo/servicio-acceso.js](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/dist/modelo/servicio-acceso.js).

**Casos ejecutados:**
- [tests.test_access_integration.AccessIntegrationTests.test_mutations_require_csrf_including_login_signup_and_logout](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L73) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_foreign_origin_rejected_even_with_token](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L80) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_local_registration.LocalRegistrationTests.test_csrf_and_foreign_origin_remain_blocked](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_local_registration.py#L77) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_garden_integration.GardenIntegrationTests.test_read_requires_csrf_and_put_not_get](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L187) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_garden_integration.GardenIntegrationTests.test_mark_read_is_persisted_idempotent_and_does_not_resolve_notice](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L155) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** Solicitud legítima con CSRF y permiso ejecuta la operación.

**Esperado negativo:** Mutación sin token, origen ajeno o método no permitido se rechaza sin cambiar datos.

**Resultado observado:** Solicitud válida de lectura aceptada; mutaciones sin token y login desde origen ajeno con token devuelven 403. GET de lectura devuelve 405.

**Límite que justifica el estado:** Evaluación de las rutas web actuales. No incluye APIs IoT futuras ni una app instalada.

**Siguiente verificación:** Repetir la comprobación al agregar endpoints y en el origen HTTPS definitivo.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-05 · v5.0.0-6.3.1 · Parcial

**Requisito del hito:** Aplicar controles documentados contra intentos de autenticación abusivos. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** Las contraseñas, códigos y reenvíos pueden probarse repetidamente.

**Implementación:** Cuotas allauth persistidas con caché de base de datos; límites por IP/clave/usuario y por proceso de verificación.

**Código revisado:** [backend/config/settings/base.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/settings/base.py), [backend/cuentas/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/cuentas/api.py).

**Casos ejecutados:**
- [tests.test_access_integration.AccessIntegrationTests.test_login_failures_are_rate_limited](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L237) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_wrong_code_exhausts_three_attempts_without_verifying](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L150) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_resend_limited_and_bounded_by_process](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L168) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_local_registration.LocalRegistrationTests.test_library_signup_rate_limit_still_applies](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_local_registration.py#L213) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** Autenticación y verificación legítimas funcionan antes de alcanzar límites.

**Esperado negativo:** Los intentos repetidos de login, código y reenvío alcanzan los límites configurados; abuso distribuido pendiente.

**Resultado observado:** Se observaron límites del servidor en login, tres intentos de código y reenvíos/alta. No se cambió la política para facilitar la presentación.

**Límite que justifica el estado:** Faltan pruebas de credential stuffing distribuido, efectividad bajo concurrencia/varias cuentas, recuperación tras ventanas y monitoreo operativo; la cuota por IP en loopback no representa una red pública.

**Siguiente verificación:** Completar pruebas acotadas de las ventanas y varias cuentas; definir vigilancia y límites en el despliegue público.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-06 · v5.0.0-6.4.3 · Verificado local

**Requisito del hito:** Recuperar una contraseña mediante un proceso seguro sin eludir factores habilitados. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** El usuario necesita recuperar acceso sin que conocer su correo conceda sesión.

**Implementación:** Recuperación de allauth con enlace efímero, respuesta neutral, uso único y sin inicio de sesión automático; correo verificado para acceso al huerto.

**Código revisado:** [backend/config/urls.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/urls.py), [backend/config/settings/base.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/settings/base.py), [backend/cuentas/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/cuentas/api.py), [backend/cuentas/inputs.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/cuentas/inputs.py).

**Casos ejecutados:**
- [tests.test_access_integration.AccessIntegrationTests.test_reset_link_is_local_single_use_and_does_not_log_in](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L198) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_expired_reset_link_rejected](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L212) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_unknown_reset_uses_neutral_response](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L218) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_final_review.FinalAccessReviewTests.test_recovery_invalidates_previous_authenticated_session](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_final_review.py#L41) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_password_guidance.PasswordGuidanceTests.test_direct_recovery_rejects_short_and_excess_then_accepts_unicode](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_password_guidance.py#L76) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** Un enlace válido permite cambiar la contraseña sin conceder sesión automática.

**Esperado negativo:** Enlace vencido o reutilizado se rechaza y sesión anterior pierde acceso.

**Resultado observado:** Enlace válido cambia la contraseña; vencido o reutilizado se rechaza. No crea sesión de acceso y la sesión autenticada anterior pierde acceso tras la recuperación.

**Límite que justifica el estado:** No hay MFA ni passkeys habilitados; no se ha demostrado recuperación para esos factores. El correo del CI es en memoria y no acredita entrega Gmail.

**Siguiente verificación:** Reevaluar recuperación antes de incorporar un segundo factor y comprobar entrega real por separado.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-07 · v5.0.0-7.2.1 · Verificado local

**Requisito del hito:** Validar la sesión mediante el servicio confiable del backend. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** Un fragmento de URL o estado JavaScript no debe autorizar datos privados.

**Implementación:** SessionMiddleware y AuthenticationMiddleware de Django; perfil y consultas verifican request.user, verificación de correo y membresía.

**Código revisado:** [backend/config/settings/base.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/settings/base.py), [backend/cuentas/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/cuentas/api.py), [backend/huerto/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/huerto/api.py), [backend/huerto/services.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/huerto/services.py).

**Casos ejecutados:**
- [tests.test_access_integration.AccessIntegrationTests.test_login_requires_correct_credentials_and_no_email_each_login](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L85) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_session_restores_in_another_client_and_logout_revokes_it](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L92) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_profile_denies_missing_session_or_revoked_verification](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L113) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_garden_integration.GardenIntegrationTests.test_anonymous_endpoints_denied](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L38) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** La sesión válida se reconoce y permite consultar el perfil propio.

**Esperado negativo:** Sin sesión o con verificación revocada se rechazan datos privados.

**Resultado observado:** Credenciales válidas permiten sesión; sin sesión no se obtiene perfil/huerto/avisos. Revocar verificación bloquea las operaciones privadas correspondientes.

**Límite que justifica el estado:** La estructura genérica del dashboard visible sin membresía no es información privada ni un permiso de consulta.

**Siguiente verificación:** Mantener este criterio en cualquier API nueva y al agregar el dispositivo.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-08 · v5.0.0-7.2.4 · Parcial

**Requisito del hito:** Renovar el identificador de sesión al autenticar y terminar el identificador anterior. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** Evitar conservar un identificador anónimo al adquirir identidad autenticada.

**Implementación:** Flujo de autenticación Django/allauth; existe prueba explícita de rotación desde una sesión anónima persistida.

**Código revisado:** [backend/config/settings/base.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/settings/base.py), [backend/cuentas/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/cuentas/api.py).

**Casos ejecutados:**
- [tests.test_final_review.FinalAccessReviewTests.test_authenticated_session_is_rotated_from_anonymous_session](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_final_review.py#L61) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_change_password_checks_current_and_invalidates_other_session](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L223) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** El login crea un identificador distinto del anónimo anterior.

**Esperado negativo:** El identificador previo desaparece del servidor; reautenticación específica pendiente.

**Resultado observado:** Tras login el identificador cambia y la fila de sesión previa ya no existe. El cambio de contraseña invalida la otra sesión comprobada.

**Límite que justifica el estado:** El requisito incluye reautenticación. No se ha demostrado un recorrido específico de reautenticación y rotación para todos los cambios de privilegio/factor.

**Siguiente verificación:** Definir recorridos de reautenticación y agregar prueba explícita antes de declarar todo el requisito verificado.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-09 · v5.0.0-7.4.1 · Parcial

**Requisito del hito:** Impedir reutilizar una sesión una vez terminada por cierre o vencimiento. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** Cerrar sesión debe revocar el acceso del identificador que el navegador conservaba.

**Implementación:** DELETE de sesión allauth y sesiones de servidor; duración local de ocho horas/cierre de navegador configurada.

**Código revisado:** [backend/config/settings/base.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/settings/base.py), [backend/config/urls.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/urls.py).

**Casos ejecutados:**
- [tests.test_access_integration.AccessIntegrationTests.test_session_restores_in_another_client_and_logout_revokes_it](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L92) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_final_review.FinalAccessReviewTests.test_recovery_invalidates_previous_authenticated_session](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_final_review.py#L41) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** Antes de cerrar, una copia de la cookie conserva el acceso autorizado.

**Esperado negativo:** Después de cerrar, esa copia recibe 401; vencimiento explícito pendiente.

**Resultado observado:** Una copia de la cookie funciona antes del logout y recibe 401 después. También se prueba pérdida de acceso tras recuperación.

**Límite que justifica el estado:** El cierre se demostró. Falta prueba explícita de vencimiento de la sesión en servidor; cerrar un navegador no acredita por sí solo caducidad ni revocación.

**Siguiente verificación:** Ejecutar un caso de sesión vencida con reloj/fecha controlados en la base aislada.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-10 · v5.0.0-8.2.1 · Verificado local

**Requisito del hito:** Restringir funciones a cuentas con permisos explícitos. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** Verificar correo no debe conceder acceso automático al único huerto.

**Implementación:** Membresía explícita activa, cuenta activa/verificada y autorización en todas las consultas y mutaciones del huerto.

**Código revisado:** [backend/huerto/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/huerto/api.py), [backend/huerto/services.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/huerto/services.py), [backend/huerto/management/commands/asignar_huerto.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/huerto/management/commands/asignar_huerto.py).

**Casos ejecutados:**
- [tests.test_garden_integration.GardenIntegrationTests.test_no_membership_discloses_neither_garden_nor_notices](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L54) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_garden_integration.GardenIntegrationTests.test_revoked_membership_denies_existing_session_and_mutation](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L63) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_garden_integration.GardenIntegrationTests.test_unverified_account_denied_even_with_membership](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L45) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_foundation.FoundationTests.test_staff_has_no_automatic_garden_permission](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_foundation.py#L150) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_local_registration.LocalRegistrationTests.test_membership_requires_separate_explicit_assignment](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_local_registration.py#L224) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** Miembro activo y verificado consulta las funciones de su huerto.

**Esperado negativo:** Cuenta sin permiso, sin verificación o con membresía revocada recibe rechazo.

**Resultado observado:** Miembro autorizado consulta; cuenta sin membresía/verificación o con membresía revocada recibe rechazo sin lectura ni mutación. Staff no obtiene permiso automático.

**Límite que justifica el estado:** No se evalúan funciones inexistentes de mando de bombas, IA, ARCO ni vinculación real.

**Siguiente verificación:** Mantener comprobación por función en cada nueva ruta. Los comandos administrativos locales requieren autorización del operador.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-11 · v5.0.0-8.2.2 · Verificado local

**Requisito del hito:** Restringir cada dato u objeto a la identidad y permisos correspondientes. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** Cambiar un ID o enviar otro usuario no debe revelar avisos ni modificar lecturas ajenas.

**Implementación:** Consultas de avisos filtradas por huerto autorizado y lectura por request.user; perfil ligado a la sesión.

**Código revisado:** [backend/huerto/services.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/huerto/services.py), [backend/huerto/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/huerto/api.py), [backend/cuentas/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/cuentas/api.py).

**Casos ejecutados:**
- [tests.test_garden_integration.GardenIntegrationTests.test_foreign_notice_is_neutral_not_found_and_never_marked](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L137) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_garden_integration.GardenIntegrationTests.test_read_state_is_per_user_and_profile_stays_own](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L169) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_garden_integration.GardenIntegrationTests.test_read_cannot_choose_another_user](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L180) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_profile_uses_session_identity_ignores_requested_user](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L103) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_garden_integration.GardenIntegrationTests.test_mark_read_is_persisted_idempotent_and_does_not_resolve_notice](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_garden_integration.py#L155) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** Consultar y marcar un aviso propio conserva estado de lectura por usuario.

**Esperado negativo:** ID ajeno o usuario impuesto no revela ni modifica el objeto de otra identidad.

**Resultado observado:** Aviso de otro registro lógico y aviso inexistente dan la misma respuesta neutral 404; no se crea lectura ajena. Lectura y perfil conservan identidad propia.

**Límite que justifica el estado:** Los registros lógicos adicionales solo son fixtures transaccionales de pruebas; no implican construir otro dispositivo físico.

**Siguiente verificación:** Revisar aislamiento por objeto al agregar solicitudes ARCO, historial e identidad del dispositivo.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-12 · v5.0.0-13.3.1 · Parcial

**Requisito del hito:** Gestionar creación, almacenamiento, acceso y retirada de secretos fuera de código y artefactos. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** Django, PostgreSQL y Gmail necesitan secretos que no deben llegar al navegador o GitHub.

**Implementación:** Archivos privados fuera del repositorio, generación aleatoria, ACL de Windows/modo 0600 y credenciales efímeras para CI; scripts no sobrescriben claves existentes.

**Código revisado:** [backend/config/private.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/private.py), [backend/tools/private_files.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tools/private_files.py), [infra/configurar_correo_local.ps1](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/infra/configurar_correo_local.ps1), [.gitignore](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/.gitignore), [.github/workflows/ci.yml](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/.github/workflows/ci.yml).

**Casos ejecutados:**
- [tests.test_foundation.FrontendPreservationTests.test_no_backend_files_or_traversal_exposed](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_foundation.py#L192) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** Preparación crea secretos propios fuera de Git y conserva los existentes.

**Esperado negativo:** Archivos de backend no son accesibles por HTTP y claves locales no aparecen en candidatos publicados; ciclo completo pendiente.

**Resultado observado:** Rutas de backend/configuración no se sirven al navegador. La preparación aislada y revisión de publicación registraron preservación de secretos y cero coincidencias con claves privadas en los candidatos a Git.

**Límite que justifica el estado:** No hay ciclo completo documentado y ensayado de rotación, revocación y destrucción; tampoco se verificó la historia completa de Git ni todas las copias/respaldos.

**Siguiente verificación:** Definir responsables, inventario, renovación y eliminación; evaluar una solución de secretos adecuada al hosting.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

### AS-13 · v5.0.0-16.2.5 · Parcial

**Requisito del hito:** Excluir, enmascarar o limitar datos sensibles de acuerdo con su nivel de protección al registrar eventos. Síntesis propia; consultar el catálogo para el texto normativo.

**Aplicabilidad:** Contraseñas, códigos, cookies y enlaces de recuperación no deben aparecer en registros.

**Implementación:** DEBUG=False; loggers de request/server/CSRF con NullHandler y errores SMTP sanitizados; informes de pruebas sin secretos vigentes.

**Código revisado:** [backend/config/settings/base.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/config/settings/base.py), [backend/cuentas/email.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/cuentas/email.py), [backend/cuentas/api.py](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/cuentas/api.py).

**Casos ejecutados:**
- [tests.test_access_integration.AccessIntegrationTests.test_smtp_failure_does_not_claim_delivery_or_expose_exception](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L191) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_email_policy.LocalEmailPolicyTests.test_smtp_failure_stays_sanitized](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_email_policy.py#L83) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_code_metadata_does_not_consume_attempts_or_expose_code](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L128) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).
- [tests.test_access_integration.AccessIntegrationTests.test_reset_link_is_local_single_use_and_does_not_log_in](https://github.com/rafael56cetz/ProyectoWEBCHILITO/blob/fab3193075b7b3ac5c1fded558a636d2cd43a5fb/backend/tests/test_access_integration.py#L198) — aprobado; [ejecución](https://github.com/rafael56cetz/ProyectoWEBCHILITO/actions/runs/39151447698).

**Esperado positivo:** Los fallos se traducen a respuestas sanitizadas útiles.

**Esperado negativo:** Errores y respuestas no revelan excepción SMTP/código/enlace; captura integral de logs pendiente.

**Resultado observado:** Los errores y respuestas comprobados no revelan excepción SMTP, código o clave de recuperación. La supresión de loggers se verificó por lectura de configuración.

**Límite que justifica el estado:** Las pruebas de respuesta no prueban por sí mismas el contenido de todos los logs. Falta capturar y revisar registros de proceso/proxy/dependencias y documentar clasificación/retención. Silenciar logs tampoco demuestra auditoría de seguridad.

**Siguiente verificación:** Ensayar captura saneada de logs y definir qué eventos registrar, quién accede y cuánto tiempo se conservan.

**Responsabilidad:** Rafael/equipo, implementación; Carolina, persistencia. La revisión humana prevista para E19-02 corresponde a Kevin y Carolina y sigue pendiente de su confirmación.

## Decisiones y pendientes

**Contraseñas:** de 15 a 256 caracteres; se conservan espacios y Unicode. El contador visual ayuda y Django valida. test_password_guidance.py prueba límites y conservación sin depender del navegador. ASVS v5.0.0-6.2.1 establece al menos 8 y recomienda 15. El mínimo de 15 es la decisión adoptada. No se sumaron requisitos a los 13 ni se declara toda la sección 6.2 verificada. Los validadores de contraseñas comunes, similares y totalmente numéricas deben contrastarse con cada requisito de composición al revisar esa sección completa.

**Correo:** el código verifica el registro; el acceso habitual usa correo/contraseña. No concede membresía ni representa un segundo factor obligatorio en cada login. Se prueban proceso, caducidad, intentos y reenvío; la entrega Gmail se comprueba por separado.

**Legales:** por decisión de Rafael, el perfil local permite registro con casilla y confirmación técnica. Las pruebas impiden que el navegador apruebe documentos o invente versiones efectivas. La excepción local no aprueba los textos legales ni habilita publicación pública. Ver [decisiones y pruebas](MEJORAS-DE-ACCESO.md).

**Transporte:** HTTP exclusivamente en loopback, cookies locales sin Secure y PostgreSQL local sin TLS. Este entorno no demuestra transporte cifrado entre navegador, servidor y base. HTTPS, cookies Secure y transporte entre servicios quedan para despliegue. SMTP tiene su configuración TLS; el CI no verifica entrega real.

**MASVS:** el hito entrega web; adaptarse al teléfono no crea un cliente móvil instalado. La evaluación MASVS se aplaza para el futuro encapsulado, cuando se fijarán versión y arquitectura y se evaluarán almacenamiento, red, plataforma, permisos y autenticación. No se declara todo MASVS cumplido ni no aplicable al producto futuro. [Fuente oficial](https://mas.owasp.org/MASVS/).

**SQL y XSS:** ORM, validación y escape son controles; no sustituyen pruebas adversarias. Esta tarea no ejecutó una batería de inyección SQL ni auditoría XSS, que siguen pendientes.

## Reproducción y fuentes

Para repetir las pruebas en la base aislada, seguir [backend/README.md](../backend/README.md#pruebas-aisladas); no usar la base principal ni correo real. Los casos citados se contrastaron con los 127 resultados aprobados. No se copiaron claves, cookies ni códigos vigentes.

[Catálogo ASVS 5.0.0](https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.csv). SHA-256: 98c8fe911b9edb403af8ee05d3ce8201ecac2659e313b053890a62847cdcf680. Se contrastaron los 345 IDs y niveles. Las síntesis y correspondencias son interpretación del proyecto.

Este documento cierra la actualización de evidencias de la selección, sujeto a revisión humana del equipo. Los 6 parciales y 332 pendientes siguen abiertos; no se declara certificación ASVS/SSDF ni seguridad integral por tener CI.
