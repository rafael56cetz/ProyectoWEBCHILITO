# Resultados y límites de la integración

27 de octubre de 2026. Ejecución vigente de 114 pruebas, identificada mediante [revision-codigo-verificado.json](../evidencias/revision-codigo-verificado.json). Las revisiones anteriores de 105 y 110 pruebas son antecedentes. Datos de prueba exclusivamente sintéticos; originales conservados. El correo real, el diseño reciente y algunos recorridos de navegador siguen pendientes: véase [cierre-entrega.md](cierre-entrega.md). No certifica seguridad integral ni despliegue.

## Resultados comprobados

| Nivel | Ejecutado | Resultado y evidencia |
|---|---|---|
| PostgreSQL | Instalación por migraciones y consistencia modelos/migraciones | PostgreSQL 17.11, check sin problemas y makemigrations sin cambios; `../evidencias/validacion-integracion.json` |
| Servicios/datos | 42 pruebas PostgreSQL +9 sin base de la capa validada, como regresión de esta integración | 51 aprobadas dentro de la suite actual |
| HTTP cuentas | Registro, código/reenvío/vencimiento/reuso, login/restore/logout, recuperación/cambio, límites, CSRF, neutralidad, sesión8h y limpieza técnica | 25 aprobadas; `../backend/tests/test_auth.py` |
| HTTP usuario/administración | Membresía/capacidades/IDOR, campos protegidos, CSRF, persistencia, soporte/caducidad/revocación/cierre, solicitudespending, idempotencia/replay, paginación y cabeceras | 29 aprobadas; `../backend/tests/test_web.py` |
| Configuración SMTP | Política de destinatarios, rechazo de dirección inválida, archivo externo protegido y configuración inválida | 5 aprobadas sin red; `../backend/tests/test_smtp_config.py`. No envían correo. |
| Arranque local | Resolución del puerto actual, rechazo de contenedor ajeno, bindings no seguros y PostgreSQL no disponible | 4 aprobadas sin Docker; `../backend/tests/test_local_environment.py` |
| Suite total | Django test `datos.tests tests --keepdb --noinput --verbosity2` | **114 pruebas aprobadas**, 56.387 s; [pruebas-integracion.txt](../evidencias/pruebas-integracion.txt) y [validacion-integracion.json](../evidencias/validacion-integracion.json) |
| Reapertura local | Reinicio de la instancia propia con puerto PostgreSQL cambiado | GET de portada 200, sin recrear base ni cambiar credenciales; [reinicio-local.json](../evidencias/reinicio-local.json) |
| Runtime PostgreSQL | Peticiones HTTP usando el rol limitado, no propietario | Cuenta, registro/verificación en memoria, huerto, mantenimiento, solicitud, soporte/consola; denegaciones de DDL/TRUNCATE/auditoría/membresía aprobadas. `../backend/tools/probar_runtime.py` |
| JavaScript | Sintaxis de módulos y adaptadores: CSRF, rechazo, idempotencia, token43, capacidades, bigint/cultivo/null, Unicode y reset sin secreto en URL | Aprobado `node frontend/pruebas-contrato.cjs`; no equivale a navegador |
| Navegador, revisión anterior | Cua, aplicación en 127.0.0.1:8780 con runtime y cuentas sintéticas | Acceso de usuario/administrador; tres plantas; mantenimiento conservado al recargar; solicitud de lámpara sin confirmación; publicación persistida; áreas del administrador; cierre de sesión y menú móvil 390 × 844. [navegador.json](../evidencias/navegador.json) y capturas; no acredita los cambios posteriores del correo. |
| Navegador, cierre actual | Instancia efímera separada en 127.0.0.1:8781, anterior a la indicación de no registrar una cuenta ficticia | Emisión y persistencia del permiso, uso administrativo y cierre técnico; comprobación parcial. [navegador-cierre.json](../evidencias/navegador-cierre.json). Registro ficticio no realizado; servidor efímero detenido. |
| Conservación | Comparación registrada de fuentes originales y del paquete anterior | 213 archivos de procedencia sin cambios y 69 huellas del paquete coincidentes; [conservacion-originales.json](../evidencias/conservacion-originales.json). Su alcance es el indicado en esa evidencia. |

El entorno efímero de la suite se detuvo al terminar. El servidor local utiliza otra instancia propia con volumen conservado. Las pruebas no usaron bases reales ni SMTP externo. La preparación del repositorio es una actividad separada; no se realizó push ni se modificó Notion.

## Correcciones y regresiones

La primera suite de98 pruebas encontró2 fallos de expectativas y1error: el formulario con content-type incorrecto podía lanzar RawPostDataException después de CSRF; la recuperación exitosa de allauth devolvía401 al quedar sin autenticar (no200); el reloj simulado del permiso también adelantaba la sesión Django. Se corrigió el manejo de entrada, se verificó el hash/nologin real y se aisló el reloj de la prueba sin debilitar la aserción de permiso vencido.

Una ejecución posterior de 101 pruebas aprobó. La revisión añadió controles y regresiones concretos: cuotas de negocio serializadas en PostgreSQL, autorización de replays al revocar membresía, paginación antes de serializar y cierre técnico al perder actividad/verificación durante logout, además de JSON profundo/tamaño. La suite de 105 aprobó. Véase `../evidencias/historial-correcciones.json`; los antecedentes no son fallos vigentes.

Después se incorporaron el modo explícito de destinatarios válidos para registro público y la carga de credenciales SMTP desde un archivo externo protegido. Las cinco pruebas nuevas y las 105 regresiones anteriores aprobaron juntas en la ejecución de 110. No se han suministrado las credenciales reales ni se han comprobado envíos o recepción en buzón.

Al reabrir el entorno local, Docker había cambiado el puerto publicado y la conexión conservaba el anterior; Django falló con conexión rechazada. Se corrigió la resolución del puerto tanto en el arranque como en la herramienta de operador, validando contenedor propio, loopback y disponibilidad, sin recrear la base ni cambiar credenciales. Se añadieron cuatro pruebas de ese mecanismo; la suite completa vigente aprobó 114 y la portada respondió 200 después de la corrección. Este GET no equivale a un recorrido de cuenta o a una prueba SMTP.

El arranque local con runtime requería leer `django_migrations`; se concedió SELECT de ese historial, sin permisos de migración/escritura. La imagen PostgreSQL usada se fijó por digest, correspondiente al 17.11 comprobado.

## Navegador: alcance concreto

Se comprobó login de usuario y administrador, restauración tras recargar, logout desde diálogo, mantenimiento duradero y solicitudes web sin afirmar ejecución. Se recorrieron flota, gobernanza, soporte vacío y cambios. La solicitud administrativa permaneció sin confirmación tras recargar y no cambió la versión en servicio. En390x844 el menú se mantiene arriba y no se observó desbordamiento horizontal (scrollWidth 375, innerWidth 390). No es una certificación responsive de todos los tamaños/dispositivos.

Registro/verificación/recuperación y ciclo completo de token/consola se comprobaron por HTTP/servicios. La comprobación de navegador de la revisión anterior no los cubrió de extremo a extremo. Las cuentas de aquella revisión se desactivaron y recibieron contraseña inutilizable tras cerrar sesión; se conservó su historia. No se publican credenciales de acceso.

En el cierre actual se comprobó por navegador una parte adicional del soporte: emisión, persistencia tras recargar sin recuperar el token, consulta del mismo caso por el administrador, validación del token, diagnóstico sin hardware y cierre de sesión técnica. Siguen pendientes la revocación/caducidad y los cambios de identificadores desde navegador, además del registro, verificación, reenvío y recuperación con correo real. El propietario rechazó el registro ficticio propuesto; no se creó esa cuenta y se detuvo la instancia efímera. No confundir este ensayo parcial con la comprobación completa del recorrido real.

## Correo y pendientes externos

Correo de pruebas en memoria en la suite, buzón de archivos protegido en ejecución local. El transporte SMTP queda preparado y apagado; su envío real requiere configuración externa segura y destinatario autorizado. No se verificó entrega real a Gmail.

El compañero preparará la dockerización. Quedarán por comprobar allí origen HTTPS, certificado/proxy, servidor WSGI/ASGI de producción, restricciones de red, secretos externos, respaldo/restauración y registros. No se prepara una VM en este trabajo. El perfil de configuración no demuestra esas propiedades desplegadas. El diseño v1 es antecedente: se espera la redacción posterior anunciada por el propietario y los documentos de requisitos y amenazas. La propuesta de inactividad de 30 minutos no se activa.

## Respaldo y exclusiones

No se repitió el ensayo de respaldo/restauración anterior para presentarlo como nuevo. Su evidencia se conserva en `../referencias/capa-datos/evidencias/ejecucion-postgres.json`. Comprobó restricciones/validación y cantidades de cuatro tablas en una base sintética. No comparó todos los objetos ni contenido fila por fila y **no demuestra el respaldo/restauración de esta nueva aplicación ni de producción**. La nueva tabla `web_idempotencia` queda fuera de aquel ensayo.

No se implementaron WebAuthn, ARCO operativo/políticas legales, sensores/MQTT, IA, actuación física ni ejecución de reinicios/despliegues. Sus solicitudes web se conservan pending. No hay porcentajes de cumplimiento ni declaración de certificación ASVS.
