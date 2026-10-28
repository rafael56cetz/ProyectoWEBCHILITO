# Seguridad de la capa de datos de El Chilito

Fecha: 27 de octubre de 2026. Alcance: paquete independiente de persistencia web, preparado para su integración posterior con Django. Este documento relaciona controles concretos, archivos y pruebas; no acredita cumplimiento integral de ASVS ni una integración operativa del frontend.

## Estado de la evidencia

- **Comprobado sin base:** nueve pruebas aprobadas: dos de política/hash de contraseña cuatro de formato/verificador/estado del permiso de soporte y tres del contrato de migraciones. El comando y su salida se conservan en [resultado-pruebas.md][resultados].
- **Comprobado en PostgreSQL 17.11 sintético:** 42 pruebas de integridad/servicios aprobadas, incluidas dos intercalaciones concurrentes; también aprobaron instalación, actualización SQL, privilegios del runtime y respaldo/restauración con el alcance limitado descrito en [resultados][resultados]. La suite final incluye además las nueve pruebas sin base: 51 aprobadas.
- **Entorno habilitado:** Docker ya fue accesible. Los ensayos usaron únicamente un contenedor propio efímero y datos sintéticos; no se cambiaron permisos del sistema ni se utilizó una base real.
- No se enviaron correos, crearon cuentas reales ni ejecutaron órdenes físicas. La entrega tampoco comprueba una API HTTP, la conexión del frontend, TLS, respaldos de producción o configuración de una máquina virtual.

## Límites y separación de controles

| Capa | Control incorporado | Límite que debe conservarse al integrar |
| --- | --- | --- |
| PostgreSQL | Tipos, claves, unicidad, `CHECK`, coherencia entre recursos, historial protegido y roles SQL separados. | Una FK no demuestra que el actor tenga permiso. Los privilegios se aplicaron y probaron en PostgreSQL sintético; deben revisarse y comprobarse de nuevo al desplegar. |
| Django | Cuenta activa/verificada, membresía vigente, cuatro capacidades explícitas, parámetros permitidos, transacciones y verificación del permiso temporal. | El actor debe proceder de `request.user`; nunca de identificadores o roles enviados por el navegador. No se añaden endpoints en este paquete. |
| Servidor / VM | Se documentan los requisitos de red, secretos, transporte, respaldo y operación. | Los archivos de este paquete no configuran ni prueban una VM de producción. |

**No hay RLS.** El runtime puede leer las tablas concedidas; el aislamiento entre cuentas y recursos se aplica en los servicios Django. Las credenciales PostgreSQL no deben entregarse al usuario final. Esta decisión no protege frente a un proceso de aplicación comprometido que opere directamente con esas credenciales.

## Matriz de controles y evidencia

Las referencias ASVS están fijadas a **5.0.0** y SSDF a **1.1**. Los identificadores remiten a las fuentes oficiales del final. “Esperado” describe el objetivo de cada comprobación; “actual” expresa la evidencia de la suite sintética final. No acredita integración HTTP ni cumplimiento integral.

| Control | Implementación localizada | Prueba / evidencia: esperado frente a actual | Referencia exacta |
| --- | --- | --- | --- |
| Contraseñas de 15 a 256 caracteres; conservar Unicode y espacios | [Configuración de validadores][config-password], [adaptador reutilizado][adapter]; hash del framework. La longitud del hash almacenado no es la longitud de entrada. | **Actual:** las dos pruebas de [política sin base][password-tests] aprobaron límites y hash exacto. No prueban registro/recuperación HTTP. | ASVS `v5.0.0-6.2.1`, `6.2.8`, `6.2.9`; SSDF `PW.1.3`, `PW.5.1`. |
| Datos separados de instrucciones SQL | [Servicios][servicios] mediante ORM; [prueba de escritura parametrizada][sql-test] usa parámetros para valores e identificadores internos fijos. | **Esperado:** apóstrofes y texto con apariencia SQL se conservan como datos. **Actual:** prueba PostgreSQL aprobada en la suite final. No se usa una lista negra de palabras. | ASVS `v5.0.0-1.2.4`; SSDF `PW.5.1`, `PW.8.2`. |
| Cuenta verificada y activa; acceso por función | [identity, capabilities y require_cap][identidad]; capacidades `ver_flota`, `atender_soporte`, `ver_gobernanza`, `gestionar_cambios`. No hay concesión implícita por `is_staff`/`is_superuser`. | **Esperado:** rechazar cuenta inactiva/no verificada, privilegio retirado y capacidad distinta. **Actual:** [pruebas de servicios][access-tests] aprobadas en PostgreSQL sintético. | ASVS `v5.0.0-8.1.1`, `8.2.1`, `8.3.1`; SSDF `PW.1.2`. |
| Acceso al huerto y al caso concreto | [member][membresia] exige membresía activa; [servicios de soporte][soporte] vinculan solicitante, caso, dispositivo y huerto. | **Esperado:** denegar recurso ajeno y membresía revocada; mantener el historial. **Actual:** pruebas negativas de servicios e [integridad][integridad] aprobadas en PostgreSQL sintético. | ASVS `v5.0.0-8.2.2`, `8.3.2`; SSDF `PW.5.1`. |
| Entrada permitida por operación | Firmas y validación de [servicios][servicios]; actor/propietario/recurso autorizado se resuelven en servidor. Enumeraciones y longitudes también están en [modelos][modelos]. | **Esperado:** rechazar tarea/incidente/tipo no admitido y referencias incompatibles. **Actual:** pruebas correspondientes aprobadas en PostgreSQL sintético. El futuro adaptador HTTP debe mantener esta lista de campos. | ASVS `v5.0.0-15.3.3`; SSDF `PW.5.1`. |
| Tres plantas y coherencia de relaciones | [Huerto 0005][h5] añade restricciones; [0006][h6] completa/crea plantas 1–3 y prohíbe borrarlas; restricciones previas conservan número e identidad. [Datos 0001][d1] y [0002][d2] añaden relaciones y disparadores. | **Esperado:** rechazar cuarta planta, borrado/reasignación, aviso de planta ajena, FK inexistente y campos sin contenido significativo. **Actual:** [integridad][integridad] aprobada en PostgreSQL sintético. | SSDF `PW.1.2`, `PW.5.1`, `PW.8.2`; estas invariantes son reglas propias del producto. |
| Leído y resuelto separados | `AvisoLeido` conserva usuario/fecha; la lectura exige membresía en [Huerto 0006][h6]; resolver pertenece al estado del aviso. | **Esperado:** lectura única por usuario/aviso, sin cambiar `resuelto_en`; impedir lectura ajena. **Actual:** pruebas de integridad aprobadas en PostgreSQL sintético. | ASVS `v5.0.0-8.2.2`; SSDF `PW.5.1`. |
| Permiso de soporte limitado y con consentimiento | [issue_support][soporte] requiere `consent is True`; [PermisoSoporte][permiso-modelo] fija caso, otorgante, alcance y ventana máxima de 24 horas; la fecha de emisión registra el otorgamiento. | **Esperado:** ningún caso parcial por consentimiento/duración inválidos; permiso de otro solicitante rechazado. **Actual:** casos de prueba aprobados en PostgreSQL sintético. No es consentimiento legal ni acceso general al perfil. | ASVS `v5.0.0-8.2.2`, `15.3.3`; SSDF `PW.1.2`, `PW.8.2`. |
| Token de soporte sin guardar su valor original | [Generación y verificación][verificador]: `secrets.token_urlsafe(32)` y HMAC-SHA-256 con clave externa separada; comparación constante; solo se persiste el verificador. El valor completo se devuelve al emitirlo. | **Actual:** cuatro [pruebas sin base][token-tests] aprobaron formato sensible a mayúsculas, fallo sin clave, cambio de clave y estado/fechas. **Actual en PostgreSQL:** la prueba de servicios aprobó que el token original no aparece en las filas/auditoría examinadas. | ASVS `v5.0.0-13.3.1`, `13.3.2`, `16.2.5`; SSDF `PW.5.1`, `PW.9.1`. |
| Vencimiento y revocación al usar soporte | [permission_state y acciones técnicas][soporte]; revocación y cierre irreversible en [Datos 0002][d2]; comprobación por operación, sin depender de borrar la fila al vencer. | **Esperado:** negar token vencido/revocado, token de otro caso y uso posterior al cierre; conservar caso/historial. **Actual:** estado puro y pruebas de persistencia/denegación aprobados en PostgreSQL sintético. | ASVS `v5.0.0-8.3.2`, `15.4.2`; SSDF `PW.5.1`, `PW.8.2`. |
| Operación y revocación coordinadas | [Bloqueos de sujetos ordenados][bloqueos], luego membresía/caso/permiso/sesión cuando corresponde; disparador de solicitud bloquea permiso antes de sesión. [Datos 0003][d3] limita una sesión abierta por administrador. | **Esperado:** las dos intercalaciones [de concurrencia][race-tests] respetan quién confirma primero; no se admiten dos sesiones abiertas por administrador. **Actual:** las dos intercalaciones concurrentes aprobaron en PostgreSQL con conexiones separadas y barreras de eventos. | ASVS `v5.0.0-15.4.2`, `15.4.3`; SSDF `PW.7.2`, `PW.8.2`. |
| Mantenimiento distinto de soporte | [record_maintenance][mantenimiento] guarda tarea, huerto, actor y fecha; caso/permiso/sesión se conservan por separado. Auditoría dentro de la transacción pertinente. | **Esperado:** consultar historia autorizada y registrar mantenimiento sin abrir un caso. **Actual:** prueba de servicios aprobada en PostgreSQL sintético. | ASVS `v5.0.0-16.2.1`; SSDF `PW.1.2`, `PW.8.2`. |
| Auditoría con referencias y sin secretos | [Auditoria][audit-modelo] admite códigos de acción/resultado y FK; [audit][auditar] no recibe texto libre, contraseñas, cookies ni el token completo. | **Esperado:** referencias coherentes y operación aceptada + evento atómicos. **Actual:** pruebas de integridad y de ausencia de token aprobadas en PostgreSQL sintético. No se afirma registro completo de intentos denegados ni un sistema externo de logs. | ASVS `v5.0.0-16.2.1`, `16.2.5`; SSDF `PW.5.1`, `PW.8.2`. |
| Historial protegido frente al runtime | [Datos 0002][d2] rechaza UPDATE/DELETE del historial; permiso solo revocable y sesión solo cerrable. [Privilegios][grants] no conceden TRUNCATE ni modificación de auditoría. | **Esperado:** rechazar cambios/borrados con SQL directo y TRUNCATE con runtime. **Actual:** pruebas de integridad y ensayo de privilegios aprobados en PostgreSQL sintético. El propietario migrador puede alterar objetos y no es el adversario cubierto. | ASVS `v5.0.0-16.4.2`; SSDF `PW.5.1`, `PW.9.1`. |
| Roles separados y privilegios mínimos | [Roles][roles]: owner y runtime sin superusuario, creación de bases/roles, replicación ni bypass RLS. [Concesiones][grants]: sin DDL ni escritura en asignación de privilegios; columnas inmutables habilitan únicamente los bloqueos requeridos. | **Esperado:** verificar rol efectivo, denegar DDL, escalamiento, alteración de pertenencia y auditoría; permitir operaciones válidas. **Actual:** roles y concesiones aplicados; operaciones válidas y denegaciones probadas en PostgreSQL sintético. | ASVS `v5.0.0-13.2.2`; SSDF `PW.9.1`, `PW.9.2`. |
| Actualización controlada del esquema | [Migraciones][d1] como fuente; [SQL derivado][sql] exige baseline e incluye DDL/registros de migración en transacción. No supone que `CREATE TABLE IF NOT EXISTS` actualice una tabla. | **Esperado:** instalación y actualización reales, plan sin pendientes y permisos creados por Django después de ruta SQL. **Actual:** instalación vacía y actualización SQL aprobaron en PostgreSQL sintético, con restricciones equivalentes e historial validado; véase [resultados][resultados]. | SSDF `PW.1.3`, `PW.7.2`, `PW.8.2`, `PS.3.1`. |

## Mecanismos que no deben confundirse

| Mecanismo | Tratamiento en esta entrega |
| --- | --- |
| Código de correo | Se conservan modelos/antecedentes Django-allauth y parámetros de verificación: 600 segundos y tres intentos. El estado del proceso pertenece al framework; no se inventa una tabla de códigos. No se ejecutó el flujo ni se envió correo. |
| Token de recuperación | Se conserva el mecanismo del framework y `PASSWORD_RESET_TIMEOUT=1800`. No es el token de soporte; el paquete no crea un reemplazo ni demuestra por sí mismo su integración HTTP. |
| Permiso temporal de soporte | Nuevo registro persistente con caso, otorgante, verificador HMAC, fechas, revocación, sesión técnica y auditoría. Su estado efectivo se calcula al usarlo. |
| Credencial WebAuthn | No se implementa ni se declara operativa. No se representa como PIN, contraseña o token de soporte. Su eventual incorporación requiere su propio contrato/verificación. |

Los ajustes anteriores se localizan en [integration_config/settings.py][settings]. Ese perfil tiene registro local deshabilitado, URL de API vacía y correo solo en memoria. No representa un servicio de autenticación publicado.

## Secretos, transporte y operación

- `CHILITO_SUPPORT_KEY`, `CHILITO_DJANGO_KEY` y credenciales de PostgreSQL se suministran externamente. No hay valores reutilizables de producción en los scripts; no se leen secretos originales para preparar este paquete. Los tokens de prueba son transitorios.
- Si falta una clave HMAC de al menos 32 bytes, emitir/validar soporte falla. No existe versionado de esa clave: cambiarla invalida la verificación de permisos anteriores; debe coordinarse con su revocación. No se promete rotación transparente.
- El valor alternativo de `SECRET_KEY` solo permite comprobaciones aisladas; debe sustituirse antes de servir una aplicación. El perfil además limita nombres de bases sintéticas. No debe transformarse en configuración de producción copiándolo sin revisión.
- El runtime debe usar su propio rol, nunca las credenciales del propietario. La asignación de las cuatro capacidades es administrativa y externa al runtime; no se concede mediante un campo del frontend.
- El perfil de base apunta por defecto a loopback y `sslmode=prefer`, adecuado únicamente como punto de partida aislado. No acredita TLS: una conexión remota requiere `verify-full`, CA confiable y validación del nombre, sin degradación a texto claro.
- En VM, restringir `listen_addresses`, reglas `pg_hba.conf` y firewall a los procesos/redes necesarios; no exponer PostgreSQL a Internet. No se modificaron ni probaron esas configuraciones aquí.
- Antes de cualquier actualización real: respaldo consistente y prueba de restauración en un entorno separado; restringir y cifrar copias y discos según el despliegue. El ensayo sintético de respaldo/restauración aprobado no acredita respaldos de producción, cifrado en reposo, alta disponibilidad o recuperación a un punto en el tiempo.
- Conservar registros fuera de la misma instancia si se necesita resistir pérdida o compromiso del propietario. El historial local protegido no sustituye esa copia. Plazos legales de conservación, eliminación y acceso no se definen por este trabajo.

Referencias de despliegue: ASVS `v5.0.0-12.3.1`, `13.3.1`, `13.3.2`, `14.1.2`, `16.4.3`; SSDF `PW.9.1`, `PW.9.2`.

## Comprobaciones pendientes antes de integrar

Las rutas de instalación/actualización y las pruebas PostgreSQL, incluidas las operaciones y negativas con runtime limitado, ya aprobaron. Se conservan resultados y correcciones en [resultados][resultados]. El respaldo verificó restricciones y cantidades de cuatro tablas; no equivalencia completa de todos los objetos o filas.

1. Integrar después el adaptador HTTP autenticado: revalidar autorización por operación, CSRF/sesión y traducción JSON; sustituir el adaptador local por el proveedor del servidor. Esta entrega no conecta la interfaz.
2. Revisar y comprobar los privilegios con el runtime del despliegue previsto, sin trasladar automáticamente credenciales/configuración de pruebas.
3. Verificar en el despliegue secretos, TLS, red restringida, correo autorizado, respaldo/restauración y registros externos. Son comprobaciones separadas de la integridad del esquema.

Las solicitudes de riego, lámpara, reinicio o cambios de versión solo quedan **pendientes**. No se presentan como ejecución física, validación de un modelo de IA ni despliegue realizado. Flota/diagnóstico devuelven ausencia de datos cuando el servicio externo no existe.

## Fuentes y trazabilidad

- [OWASP ASVS 5.0.0, publicación oficial](https://github.com/OWASP/ASVS/releases/tag/v5.0.0_release) y [catálogo oficial fijado a esa versión](https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.csv). Cada referencia abreviada de la matriz comparte el prefijo `v5.0.0-`.
- [NIST SSDF 1.1, SP 800-218 final](https://csrc.nist.gov/pubs/sp/800/218/final) y [PDF oficial](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf): `PW.1.2/PW.1.3` p.11; `PW.5.1` p.13; `PW.7.2` p.14; `PW.8.2` p.15; `PW.9.1/PW.9.2` p.16; `PS.3.1` p.10, según numeración impresa.
- [Referencias verificadas y criterios seleccionados][referencias]. No se añaden otros marcos ni se atribuyen resultados a controles fuera del alcance.

[resultados]: <resultado-pruebas.md>
[config-password]: <../../backend/integration_config/settings.py>
[adapter]: <../../backend/cuentas/adapters.py>
[password-tests]: <../../backend/datos/tests/test_integridad.py>
[servicios]: <../../backend/datos/services.py>
[sql-test]: <../../backend/datos/tests/test_integridad.py>
[identidad]: <../../backend/datos/services.py>
[access-tests]: <../../backend/datos/tests/test_servicios.py>
[membresia]: <../../backend/datos/services.py>
[soporte]: <../../backend/datos/services.py>
[integridad]: <../../backend/datos/tests/test_integridad.py>
[modelos]: <../../backend/datos/models.py>
[h5]: <../../backend/huerto/migrations/0005_aviso_aviso_titulo_significativo_and_more.py>
[h6]: <../../backend/huerto/migrations/0006_tres_zonas_y_lecturas.py>
[d1]: <../../backend/datos/migrations/0001_initial.py>
[d2]: <../../backend/datos/migrations/0002_integridad_historial.py>
[d3]: <../../backend/datos/migrations/0003_sesiontecnica_tecnica_admin_una_abierta.py>
[permiso-modelo]: <../../backend/datos/models.py>
[verificador]: <../../backend/datos/services.py>
[token-tests]: <../../backend/datos/tests/test_servicios.py>
[bloqueos]: <../../backend/datos/services.py>
[race-tests]: <../../backend/datos/tests/test_servicios.py>
[mantenimiento]: <../../backend/datos/services.py>
[audit-modelo]: <../../backend/datos/models.py>
[auditar]: <../../backend/datos/services.py>
[grants]: <privilegios.sql>
[roles]: <roles.sql>
[sql]: <el_chilito.sql>
[settings]: <../../backend/integration_config/settings.py>
[referencias]: <evidencias/referencias-seguridad.md>
