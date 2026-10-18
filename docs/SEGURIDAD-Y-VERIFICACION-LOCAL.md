# Seguridad y plan de verificación local

> **Revisión del 18/10/2026:** la selección ASVS se concilió con código y CI aprobado: 7 verificados en alcance local, 6 parciales y 332 pendientes. Ver [matriz y evidencia actuales](MATRIZ-REQUISITOS-Y-EVIDENCIAS-2026-10-18.md). Las cifras de 0/13 y notas de backend/CI pendientes que aparecen abajo son históricas.

Etapa 0 · 17-10-2026. Marcos fijados por Rafael: **NIST SSDF 1.1, requisitos seleccionados OWASP ASVS 5.0.0 y procedimientos OWASP WSTG 4.2**. No se declara certificación o cumplimiento total por usar Django. Esta etapa combina revisión pasiva y planificación; no es un pentest de backend inexistente.

Skills utilizadas por solicitud: sdlc-seguro (descubrimiento/diseño), asvs-requisitos (selección trazable), ssdf-practicas (actividades), wstg-pruebas (plan futuro) e iot-seguro (límites del contrato del dispositivo). No se aplicaron habilidades de rediseño visual.

## 1. Activos y límites

Activos: cuentas, contraseñas derivadas, códigos/enlaces efímeros, sesiones, evidencia legal, membresías, futuras lecturas/avisos y disponibilidad del cultivo. ARCO/IA/llaves reales aplazadas no se consideran implementadas.

Límites: navegador no confiable → Django; Django → PostgreSQL con rol limitado; Django → correo autorizado; futuro dispositivo → ingesta autenticada aún no diseñada. La sesión de una cuenta no equivale a autorización al huerto. El administrador PostgreSQL es una función distinta de administrador web/miembro del huerto.

La revisión actual no inspecciona hardware, firmware o proveedor SMTP. Las superficies externas y otros usuarios/equipos están fuera de las pruebas de este turno.

## 2. Amenazas y requisitos internos propuestos

| ID propio | Escenario / consecuencia | Respuesta y prueba futura |
| --- | --- | --- |
| R-01 | Abrir #huerto o activar previewNavigation omite autenticación | Arranque real sin desarrollo, sesión servidor y permisos en cada API; ruta directa sin sesión/tras logout no da datos |
| R-02 | Cuenta nueva/verificada accede al huerto único por defecto | Membresía explícita; comparar usuario autorizado con cuenta verificada sin membresía, sin crear otro dispositivo ficticio |
| R-03 | ID de aviso/solicitud permite leer datos ajenos | Consultas acotadas por identidad/huerto; prueba negativa de ID ajeno y pertenencia en DB; ARCO no se integra aún |
| R-04 | Formulario desde otro origen ejecuta mutaciones de sesión/contraseña | CSRF también en login/logout, token/Origin según Django, sin exenciones propias; probar rechazo sin token o con token de otra sesión |
| R-05 | Código fijo, reuso, fuerza bruta/reenvío o enlace falso toma cuenta | Biblioteca con expiración, proceso/uso y límites servidor; código nunca en respuesta/log; recuperación sin atajos ni login-by-code obligatorio |
| R-06 | Click/animación o JSON incompleto produce éxito aparente | Validar contrato por operación; solo commit/sesión confirmados; timeout/red no equivalen a éxito, lista vacía o rollback |
| R-07 | Datos relacionados de distintos huertos o reasignación invalidan historial | Escrituras validadas/transaccionales, restricciones aplicables y relaciones estables; pruebas que evitan full_clean y concurrencia |
| R-08 | Secretos o datos de usuario salen por dist, logs, URL o almacenamiento | Claves fuera del frontend/Git; cuerpos sensibles excluidos de logs; cookie HttpOnly, no JWT storage; comprobar artefactos antes de entrega |
| R-09 | Sensor sin lecturas aparece como 0, offline, fecha reciente o alarma | waiting/null/unknown sin fecha inventada; diferenciar fallo de servicio de ausencia válida |
| R-10 | Mensaje IoT falso/repetido o comando remoto causa riego inseguro | Ingesta/comandos aplazados, identidad/procedencia/replay pendientes; ningún cambio de interfaz habilita actuadores |
| R-11 | Registro sobre borrador legal se presenta como consentimiento aprobado | Servidor cierra alta hasta versiones efectivas y prueba de aceptación; rechazo antes de cuenta/correo, incluso endpoint directo |
| R-12 | Funciones aplazadas siguen dando acuses o llaves ficticios con éxito real | Resolver navegación con Rafael antes de Etapa 3; excluir adaptadores sintéticos y rechazar demonstration como autenticación |

Los IDs R-xx son decisiones de producto propias, no identificadores normativos.

## 3. Selección ASVS verificada y alcance explícito

Se consultó el catálogo completo oficial del **tag v5.0.0**, commit `3383877f732ce89a458a1af43288f2f1b1d7db0c`. Archivo:
[OWASP_Application_Security_Verification_Standard_5.0.0_en.csv](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.csv).

SHA-256 del catálogo consultado: `98c8fe911b9edb403af8ee05d3ce8201ecac2659e313b053890a62847cdcf680`.
Contiene **345 requisitos**: 70 L1, 183 L2 y 92 L3 (nivel mínimo del requisito, no coberturas alcanzadas).

[ASVS-5.0.0-ALCANCE-LOCAL.csv](ASVS-5.0.0-ALCANCE-LOCAL.csv) registra todos los IDs, nivel, aplicabilidad/estado y fuente: **13 seleccionados aplicables/planeados; 332 pendientes de evaluación**. No se descartan los demás ni se declaran no aplicables por comodidad. Objetivo propuesto para evaluación posterior: L2 por cuentas/datos personales y autorización entre usuarios, con restricciones IoT independientes. Adoptado ahora: selección del hito, **no un nivel integral**. Evaluar los 253 de nivel mínimo L1/L2 antes de aspirar a demostrar L2 y justificar exclusiones, junto con riesgos que exijan más.

| ID verificado | Nivel mínimo | Objetivo concreto / prueba prevista |
| --- | --- | --- |
| v5.0.0-1.2.1 | L1 | Escape contextual; comprobar textos recibidos en las vistas |
| v5.0.0-2.2.1 | L1 | Validación servidor de entradas y relaciones |
| v5.0.0-3.3.4 | L2 | Sesión HttpOnly, solo Set-Cookie |
| v5.0.0-3.5.1 | L1 | Rechazo de mutaciones CSRF |
| v5.0.0-6.3.1 | L1 | Límites de autenticación según política |
| v5.0.0-6.4.3 | L2 | Recuperación segura sin eludir factores |
| v5.0.0-7.2.1 | L1 | Sesión validada en backend |
| v5.0.0-7.2.4 | L1 | Rotación al autenticar |
| v5.0.0-7.4.1 | L1 | Sesión invalidada al terminar |
| v5.0.0-8.2.1 | L1 | Permiso explícito por función |
| v5.0.0-8.2.2 | L1 | Permiso por objeto |
| v5.0.0-13.3.1 | L2 | Gestión de secretos fuera de código/artefactos |
| v5.0.0-16.2.5 | L2 | Restricción de datos sensibles en logs |

Todas las verificaciones de estos controles en la aplicación **integrada** están pendientes; 0/13 se declaran verificados. El archivo externo de secreto y los grants de DB son evidencia parcial de preparación, no satisfacción completa de los controles. No se calcula un porcentaje global sobre esta selección. Responsable: Rafael; Carolina revisa persistencia, Rafael/Gabriela presentación de estados.

Identificadores/síntesis contrastados con el catálogo fijado. El mapeo a casos locales y WSTG es interpretación del proyecto, no equivalencia oficial uno a uno.

## 4. Prácticas SSDF 1.1 adaptadas a este trabajo

Fuente primaria: [NIST SP 800-218, tabla 1](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf), edición 1.1 final. Se conservan estas tareas; no se migra a borradores posteriores.

| Tarea verificada | Actividad local / responsable | Evidencia y estado |
| --- | --- | --- |
| PO.1.1 | Rafael documenta requisitos de entornos/herramientas y protección de secretos | Contexto y límites en docs; ejecución/configuración completa pendiente |
| PW.1.1 | Rafael/Carolina revisan amenazas del diseño | Tabla R-xx y revisión del modelo realizadas; mitigaciones aún propuestas |
| PW.1.2 | Mantener requisitos, riesgos y decisiones / Rafael | Contratos, bloqueos y alcance registrados; actualizar por revisión |
| PW.7.1 | Elegir revisión/análisis de código adecuados / Rafael y revisión del equipo | Revisión estática de esta etapa; plan de revisión de cambios y dependencias antes de integrar |
| PW.8.1 | Definir pruebas de la aplicación ejecutable / Rafael/Gabriela/Carolina | Casos de integración/permisos/BD planificados; backend no ejecutado |

No son cinco fases sucesivas ni una declaración de cobertura total SSDF. Brechas prioritarias: versiones bloqueadas/entorno reproducible, revisión de dependencias instaladas antiguas, políticas de acceso/código, protección de logs, pruebas aisladas, respaldos/restauración y comprobaciones reproducibles de entrega. No se crea CI ni se instala un escáner en Etapa 0.

## 5. Plan WSTG 4.2 para etapas autorizadas

**No ejecutado en este turno.** Precondiciones: backend local integrado y revisión exacta identificada; cuentas de prueba de Rafael (asignada/sin membresía), base aislada y destinatario de correo autorizado. Sin ataques de volumen, escaneo externo, datos de terceros o comandos físicos. Parar ante un servicio distinto del local, exposición de datos inesperada, errores de integridad o riesgo de modificar el huerto real.

| Procedimiento oficial versionado | Pasos acotados / resultado esperado | Evidencia futura |
| --- | --- | --- |
| [WSTG-v42-SESS-02](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/06-Session_Management_Testing/02-Testing_for_Cookies_Attributes/) | Autenticar en cuenta de prueba; revisar atributos, sin copiar valor de cookie. HttpOnly/SameSite/host correctos; Secure conforme al entorno | Informe de atributos sin credenciales; limitación HTTP local explícita |
| [WSTG-v42-SESS-05](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/06-Session_Management_Testing/05-Testing_for_Cross_Site_Request_Forgery/) | Mutación sin CSRF/con token ajeno rechazada; legítima aceptada | Método/ruta, estado y ausencia de cambio de datos; sin token en reporte |
| [WSTG-v42-SESS-06](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/06-Session_Management_Testing/06-Testing_for_Logout_Functionality/) | Cerrar; intentar usar sesión anterior y volver/recargar | Denegación servidor y DOM sin datos privados |
| [WSTG-v42-ATHZ-02](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/05-Authorization_Testing/02-Testing_for_Bypassing_Authorization_Schema/) | Repetir consultas con anónimo, cuenta sin membresía y miembro | 401/403 o respuesta neutral acordada; miembro recibe solo su huerto |
| [WSTG-v42-ATHZ-04](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/05-Authorization_Testing/04-Testing_for_Insecure_Direct_Object_References/) | Manipular ID de aviso/usuario de pruebas y operación de lectura | Sin datos ni mutación ajenos; no otro dispositivo físico |
| [WSTG-v42-ATHN-09](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/04-Authentication_Testing/09-Testing_for_Weak_Password_Change_or_Reset_Functionalities/) | Correo autorizado, enlace inválido/vencido/reusado, otra cuenta y contraseña actual errónea | Sin bypass; cambio real solo autorizado; informe sin enlace/código |

Las páginas llevan IDs base WSTG-SESS/ATHZ/ATHN; el prefijo v42 del registro fija la edición. No se reutiliza la guía latest. Estos seis procedimientos no equivalen a toda la guía. Complementar con pruebas propias de reenvíos/caducidad, límites, relaciones DB, no datos, persistencia y entrega, siguiendo los contratos.

Las baterías frontend antiguas se preservan, pero sus éxitos de simulación o su acceso vacío no son criterio de seguridad nuevo. En etapas de integración se actualizarán únicamente las expectativas afectadas y se documentarán ejecución, revisión, resultados y limitaciones actuales.

## 6. Contrato IoT: alcance futuro y precauciones del producto

Requisitos internos propios, sin atribuirlos a ASVS/WSTG como seguridad completa del firmware:

| ID propio | Decisión/requisito y prueba pendiente |
| --- | --- |
| IOT-01 | Tres sondas de sustrato, DHT22 con temperatura/humedad y flotador; no óptico/ventilador. Revisar firmware y unidades contra datos del dispositivo antes de habilitar canales |
| IOT-02 | Identidad y revocación por dispositivo; UUID no es secreto. Resolver provisión/transporte/cifrado/propiedad, sin claves PostgreSQL en ESP32 |
| IOT-03 | Secuencia/deduplicación, reinicio, replay, procedencia y reloj. Hora recibida de servidor distinta de hora medida válida; sin comunicación previa, null |
| IOT-04 | Índice calibrado de sustrato con valor bruto/versión; flotador bajo/no bajo/desconocido. Fallo de sensor no equivale a depósito vacío o dato cero |
| IOT-05 | Autonomía y seguridad física local de bomba ante nivel bajo/desconexión/reinicio. Polaridad del flotador, bombas/energía y límites requieren documento/ensayos, no reglas inferidas desde la web |
| IOT-06 | Un evento de bomba no prueba caudal; lámpara reportada no prueba iluminación física. Sin endpoints de órdenes o éxito visual por anticipación |
| IOT-07 | Inventario/versiones, actualización/retirada y accesos físicos pendientes. No se evaluaron esas capacidades por disponer de ESP32 |

No se ejecutaron comandos físicos ni se simuló telemetría. Lecturas, integración del dispositivo, calibración y órdenes requieren autorización posterior. Se puede implementar identidad web/huerto sin esperar lecturas, manteniendo waiting/null.

## 7. Evidencia y cierre honesto

[Documento de Etapa 0](ETAPA-0-INTEGRACION-REAL-2026-10-17.md) e [inventario textual](EVIDENCIA-ETAPA-0-LOCAL.json) distinguen observado, propuesto y pendiente. Esta etapa verificó rutas/estructura/huellas y metadatos de DB en solo lectura; no verificó autenticación real, entrega de correo, permisos API, restricciones del borrador, respaldo/restauración, hardware o cumplimiento ASVS.

No se aprobaron documentos legales ni se consultó/interpretó normativa jurídica para declararlos válidos. Su estado y responsables siguen pendientes. No se modificó la interfaz para aparentar seguridad real; las simulaciones actuales están localizadas para sustituirlas en las etapas expresamente autorizadas.

## Evidencia incremental de Etapa 2 — 17-10-2026

Ver [entrega y contrato real](ETAPA-2-ACCESO-Y-CORREO.md) y [evidencia](EVIDENCIA-ETAPA-2-LOCAL.json). La etapa no declara conformidad total de ASVS, SSDF o WSTG.

| Riesgo propio | Evidencia actual / límite |
| --- | --- |
| R-01 | Sin módulos desarrollo en arranque/superficie HTTP, guardia de sesión y login inválido/válido/restauración/cierre en navegador. |
| R-02 | Código confirmado no crea membresía; perfil requiere verificación de allauth y gardenAssigned se consulta por usuario. Datos del huerto esperan Etapa 3. |
| R-04 | CSRF y origen ajeno rechazados en mutaciones, incluido login/logout/registro. Cookie de sesión HttpOnly/SameSite. |
| R-05 | Código vencido, tres intentos, reenvío/cuota, límites de acceso y enlace de recuperación vencido/usado comprobados en base aislada. SMTP real confirmado solo con mensaje inocuo; registro público cerrado. |
| R-06 | JSON incompleto no autentica ni confirma verificación. Ninguna respuesta ficticia de ARCO/llaves/avisos en arranque. |
| R-08 | Recursos sensibles fuera de rutas servidas; sin tokens localStorage, códigos en API, enlaces en query de servidor o cuerpos/SMTP en logs. HTTP local no sustituye configuración HTTPS de producción. |
| R-11 | Endpoint de alta cerrado antes de crear cuenta, con independencia del checkbox. Documentos/versiones siguen pendientes. |
| R-12 | Servicios aplazados devuelven indisponibilidad; no crean credenciales, recibos ARCO o respuestas IA. Navegación existente conservada hasta decisión posterior. |

Reparto vigente: Rafael, backend/correo; Carolina, PostgreSQL y logo; Rafael y Gabriela, frontend/revisión. Sin modificaciones de Notion, electrónica, métricas o actuadores. El catálogo ASVS conserva su selección histórica y no se marca globalmente como aprobado por estas pruebas parciales.

## Evidencia incremental de Etapa 3 — 17-10-2026

Alcance autorizado: únicamente aplicación local y base aislada el_chilito_test para casos activos; datos sintéticos, dos conexiones para concurrencia de una lectura y navegadores efímeros. Sin escáner, terceros, correo externo, comandos de hardware o cambios de autenticación. Parada ante base/rol/puerto inesperado; no se borran ni recrean bases. Evidencia: [entrega](ETAPA-3-DASHBOARD-Y-CUENTA.md) y [registro actual](EVIDENCIA-ETAPA-3-LOCAL.json).

| Riesgo propio | Implementación y evidencia | Límite |
| --- | --- | --- |
| R-01/R-02 | Cada endpoint exige sesión/verificación y membresía al principal; no sesión, cuenta sin asignar, revocada e inactiva denegadas. Perfil no depende de tener huerto. | No alta pública mientras falten legales. |
| R-03 | Aviso se consulta por huerto autorizado; ID ajeno/inexistente devuelven el mismo 404. Estado leído por usuario, no por ID declarado en cuerpo. | Sin ARCO o datos de IA reales. |
| R-04 | PUT de lectura requiere CSRF; GET no muta. | Secure=false solo loopback; producción HTTPS pendiente. |
| R-06/R-09 | Sin lecturas: null/missing/unknown y sin fechas de comunicación. Vacío real distinto de DB/API fallida o respuesta incompleta. No se quitan filas malformadas para fingir vacío. | Contrato definitivo de electrónica/ingesta/calibración pendiente. |
| R-07 | CHECK/FK/unique y triggers migrados protegen zona/huerto y relaciones estables. Pruebas evitan clean y buscan reasignación. | Retención/borrado y firma de eventos futuros pendientes. |
| R-08 | Escape del texto persistido comprobado; no perfiles/avisos en DOM al perder sesión. APIs no-store, datos sensibles fuera de logs/storage. | Lectores de pantalla/teléfono físico pendientes. |
| R-12 | Accesos conservados por decisión de Rafael; controles ARCO/llaves deshabilitados y disponibilidad, sin éxito sintético. | Integraciones requieren otra entrega explícita. |

81 pruebas de servidor; 65 comprobaciones dashboard; 64 acceso; 3 aserciones de lectura concurrente con dos conexiones. Fixtures fuera de base principal y retiradas. SSDF: cambio acotado/documentado, revisión de transacciones/roles y regresión reproducible; Rafael backend/correo, Carolina PostgreSQL, Rafael/Gabriela frontend. ASVS 5.0.0/WSTG 4.2 permanecen una selección parcial según la matriz existente; esta evidencia no marca el catálogo completo como aprobado ni extiende cobertura al firmware. Etapa 4 no iniciada.

## Etapa 4 · Evidencia parcial de verificación local

Fecha 17-10-2026. Sustituye las cifras y el pendiente «Etapa 4 no iniciada» de las notas anteriores. Alcance autorizado: aplicación local propia, PostgreSQL principal conservado, fixtures solo en el_chilito_test o nueva restauración aislada. Sin pruebas a terceros/producción/SMTP real/hardware. Sin capturas. Parada ante base, rol, carpeta o proceso inesperado.

Resultados: 86 casos Django, 64 comprobaciones de acceso, 65 del dashboard, 3 aserciones concurrentes; 18 comprobaciones sobre restauración y 15 después de reinicios. [Entrega y limitaciones](ETAPA-4-VERIFICACION-Y-ENTREGA.md), [evidencia saneada](EVIDENCIA-ETAPA-4-LOCAL.json). Las clases test_final_review añaden cinco regresiones sin heredar/contar de nuevo la batería anterior.

### Trazabilidad ASVS seleccionada

La [matriz de Etapa 0](ASVS-5.0.0-ALCANCE-LOCAL.csv) conserva su clasificación/plan original; no se reescribe como si el catálogo entero hubiese pasado. Los trece identificadores seleccionados de ASVS 5.0.0 tienen la siguiente evidencia **parcial local**, no una declaración de conformidad integral ni de un nivel completo.

| Referencias seleccionadas | Evidencia local | Límites de la conclusión |
| --- | --- | --- |
| v5.0.0-1.2.1; v5.0.0-2.2.1 | Salida persistida escapada en navegador, validación y relaciones en servidor/DB; pruebas negativas de restricciones. | Solo campos/recorridos cubiertos; no todos los contextos del catálogo. |
| v5.0.0-3.3.4; v5.0.0-3.5.1 | Cookie de sesión HttpOnly y CSRF exigido en mutaciones incluidas autenticación/lectura. | HTTP loopback usa Secure=false; HTTPS y cookies de producción pendientes. |
| v5.0.0-6.3.1; v5.0.0-6.4.3 | Límites de acceso, verificación/reenvío; enlaces de recuperación inválidos/vencidos/reutilizados rechazados y sesión anterior invalidada. | Alta pública cerrada. Correos de pruebas en memoria; prueba SMTP real previa no acredita alta real completa. |
| v5.0.0-7.2.1; v5.0.0-7.2.4; v5.0.0-7.4.1 | Sesión de servidor, rotación al autenticar, persistencia tras reinicio, cierre y rechazo posterior/reutilización. | Duración/configuración local; no pruebas de operación distribuida o producción. |
| v5.0.0-8.2.1; v5.0.0-8.2.2 | Usuario activo/verificado, membresía explícita, denegación sin asignación y 404 neutral para aviso ajeno/inexistente. | API de cuenta/huerto/avisos; ARCO, IA e ingesta no implementadas. |
| v5.0.0-13.3.1; v5.0.0-16.2.5 | Configuración fuera de frontend/Git; respuestas y evidencias no incluyen credenciales/cookies/códigos/tokens; errores saneados y APIs no-store. | Sin lectura de secretos ni auditoría completa de acceso/retención de logs de producción. Dump privado sin cifrar, ACL local; no distribuir. |

Fuente de identificadores: [catálogo oficial ASVS 5.0.0](https://github.com/OWASP/ASVS/tree/v5.0.0/5.0). No se computa un porcentaje de cumplimiento a partir de aserciones.

### Procedimientos WSTG 4.2 seleccionados

| Procedimiento | Ejecución local | Resultado y pendiente |
| --- | --- | --- |
| WSTG-SESS-02 | Atributos de cookie de sesión en cliente/batería, HttpOnly; configuración local separada. | Comprobación parcial; transporte HTTPS/producción pendiente. |
| WSTG-SESS-05 | Peticiones de mutación sin CSRF válido y con cliente aislado. | Rechazadas en rutas cubiertas; no revisión de todas las superficies posibles. |
| WSTG-SESS-06 | Logout, consulta posterior y reutilización de sesión; navegación/recarga protegida. | No recupera perfil/datos privados con sesión cerrada. |
| WSTG-ATHZ-02 | Anónimo, usuario sin membresía/revocado/inactivo frente a funciones protegidas. | Denegados; perfil propio no otorga permiso al huerto. |
| WSTG-ATHZ-04 | Consulta/marcado de aviso ajeno y manipulación de ID. | Sin exposición del huerto ajeno; 404 neutral. |
| WSTG-ATHN-09 | Cambio/recuperación, enlaces inválidos/vencidos/usados, contraseña y sesión antiguas. | Rechazados; nueva contraseña permite acceso sin auto-login por recuperación. Registro público no probado de extremo a extremo. |

Referencias: [sesiones WSTG 4.2](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/06-Session_Management_Testing/), [autorización WSTG 4.2](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/05-Authorization_Testing/), [cambio/recuperación WSTG 4.2](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/04-Authentication_Testing/09-Testing_for_Weak_Password_Change_or_Reset_Functionalities/).

### Actividades SSDF y límite IoT

Aplicación acotada de SSDF 1.1: inventario/roles y requisitos documentados, dependencias fijadas, preservación de cambios manuales, cinco casos adicionales de regresión, revisión de permisos, pruebas reproducibles, respaldo/restauración y pendientes registrados. No existe pipeline remoto; infra/verificar_entrega.ps1 es la puerta local. pip check no sustituye análisis de vulnerabilidades. No se declara una evaluación completa de todas las prácticas SSDF.

No se modificaron métricas ni el modelo físico. Sin ingesta, bombeo o firmware, la seguridad del dispositivo sigue pendiente y no se deduce de estas pruebas web.

Responsables: Rafael backend/operación/correo; Carolina PostgreSQL/logo; Rafael y Gabriela frontend. Legales, cuenta de presentación explícita, membresía, remitente definitivo, ARCO/IA/llaves, ingesta, HTTPS, accesibilidad completa y producción permanecen pendientes según la entrega.
