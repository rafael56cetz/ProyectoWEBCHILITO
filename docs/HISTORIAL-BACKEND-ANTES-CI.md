# Backend local · Etapa 4

> **Etapa B vigente — registro local con cualquier correo válido.** Ya no se autoriza cada destinatario manualmente. Se mantienen casilla, verificación por código, límites y acceso únicamente desde esta computadora. Rafael confirmó su registro y código reales. Los documentos continúan pendientes y no se asigna un huerto automáticamente. 57 pruebas Django y 48 comprobaciones de navegador aprobadas para esta actualización. Ver [cambio, configuración y comprobaciones](../docs/MEJORAS-DE-ACCESO.md). C no iniciada; las notas posteriores conservan la historia de las entregas anteriores.

> **Etapa A verificada:** ayuda de contraseña y entrada exacta sin recorte de espacios, manteniendo allauth/validadores/versiones. Ver [entrega acumulativa y pruebas](../docs/MEJORAS-DE-ACCESO.md). 93 casos de servidor actuales y 69 comprobaciones enfocadas de navegador. Registro cerrado; sin cambios de base o nuevas rutas. Los resultados de Etapa 4 siguientes son históricos.

> **Etapa 4 verificada localmente — 17-10-2026.** Consultar [entrega vigente, arquitectura, contratos y arranque](../docs/ETAPA-4-VERIFICACION-Y-ENTREGA.md) y [evidencia actual](../docs/EVIDENCIA-ETAPA-4-LOCAL.json). 86 pruebas Django, 64 comprobaciones de acceso, 65 de dashboard, 3 aserciones de concurrencia, 18 de restauración y 15 de reinicio aprobadas. Base principal preservada; sin cambios de frontend/migraciones en esta etapa. Registro cerrado por legales pendientes; IA/ARCO/llaves y hardware real aplazados. Las notas siguientes describen etapas anteriores cuando difieren de este estado. Sin publicación ni push.

Ejecutor vigente desde PowerShell: infra/verificar_entrega.ps1, en la raíz. Instalación y configuración privada se conservan debajo. Las cifras de etapas anteriores son históricas; el resultado actual es 86 pruebas Django, 64 comprobaciones de acceso, 65 de dashboard y 3 aserciones concurrentes.

Para comprobar el dashboard con el mismo ejecutor aislado: python tools/comprobar_frontend.py --etapa 3 (desde el entorno del backend, con las variables Playwright ya indicadas). Sin capturas ni correo SMTP real durante pruebas.

Django/Python en Windows y PostgreSQL 17 en Docker. La sesión y los formularios se conectan al dist original sin copiarlo. Registro cerrado por documentos pendientes; correo Gmail de prueba recibido y confirmado. Ver [contratos, archivos y límites vigentes](../docs/ETAPA-2-ACCESO-Y-CORREO.md).

## Iniciar la aplicación actual

Desde cualquier PowerShell:

```powershell
& 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\infra\iniciar_aplicacion.ps1'
```

Una URL: [El Chilito](http://127.0.0.1:8766/index.html). El script inicia/espera Docker, selecciona rol app, evita duplicados y ejecuta Django en loopback. Ctrl+C detiene el arranque de esa terminal. No utilizar http.server para autenticación.

## Correo local

Una cuenta Gmail de pruebas como remitente; el perfil local admite cualquier destinatario válido para los flujos de cuenta. Configuración privada fuera del proyecto, en %LOCALAPPDATA%/ElChilito/secrets: correo_local.json y gmail_app_password.txt. El asistente infra/configurar_correo_local.ps1 solicita la contraseña de aplicación de Google sin mostrarla y no sobrescribe archivos existentes. No usa la contraseña habitual de Gmail. Requiere verificación en dos pasos según Google.

Desde backend, para enviar **un mensaje real** únicamente al destinatario privado autorizado:

```powershell
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" manage.py comprobar_correo_local
```

El mensaje administrativo no crea/verifica cuentas. El registro local está habilitado y ya no requiere una lista de destinatarios: ELCHILITO_LOCAL_EMAIL_ANY_RECIPIENT toma 1 por defecto en local. En base y testing está desactivado; 0 restaura el modo restringido tras reiniciar. La integración informa los fallos de SMTP y conserva verificación y límites. No introducir secretos en comandos, Git o chat. La cuenta remitente definitiva sigue pendiente.

## Pruebas de Etapa 2 (histórico)

```powershell
Set-Location 'C:\Users\rafae\OneDrive\Documentos\El-Chilito-Aplicacion-Web\backend'
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" manage.py test --verbosity 1
$env:NODE_PATH='C:\Users\rafae\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
$env:PLAYWRIGHT_BROWSERS_PATH='C:\Users\rafae\AppData\Local\ms-playwright'
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" tools/comprobar_frontend.py
```

57 pruebas Django y 64 comprobaciones Chromium; fixtures solo en base aislada. La batería no envía SMTP real. Sin pruebas simultáneas sobre la misma base. El puerto de pruebas se retira al terminar y no corresponde a una segunda aplicación para el usuario.

La migración cuentas.0002_cuotas_acceso añade almacenamiento para límites de allauth con DatabaseCache; se aplicó con migrador en ambas bases, sin borrar datos. Total actual: 28 migraciones. El servidor utiliza rol app. Las cuentas/verificaciones/sesiones siguen bajo Django/allauth.

## Documentación de preparación conservada

Las secciones siguientes provienen de Etapa 1. Las afirmaciones sobre API no montada, SMTP bloqueado, 27 migraciones y frontend pendiente corresponden a ese momento y quedan sustituidas por el estado vigente anterior.

## Entorno y dependencias

Python usado: 3.13.7. Entorno fuera de OneDrive:

`C:\Users\rafae\AppData\Local\ElChilito\venvs\backend`

Versiones: Django 5.2.18, django-allauth[headless] 65.20.0, psycopg[binary] 3.3.6. requirements.txt fija dependencias directas; requirements-lock.txt registra las 11 distribuciones resueltas. No se sustituyeron paquetes globales.

Para reproducir desde PowerShell, solo si no existe ya el entorno:

```powershell
python -m venv "$env:LOCALAPPDATA\ElChilito\venvs\backend"
& "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe" -m pip install -r backend/requirements-lock.txt
```

## Configuración privada

Los archivos viven en `%LOCALAPPDATA%\ElChilito\secrets\`, fuera de dist y Git. Nunca pegar valores en chat, comandos o documentación.

- el_chilito_migrador.txt: contraseña existente del rol de migraciones.
- el_chilito_app.txt: contraseña existente del rol de ejecución.
- django_secret_key.txt: clave local estable generada criptográficamente.
- el_chilito_test_migrador.txt / el_chilito_test_app.txt: claves independientes de pruebas.

`infra/guardar_credenciales_backend.ps1` pide las dos contraseñas de roles sin mostrarlas. No cambia PostgreSQL y no sobrescribe archivos existentes; limita sus ACL al usuario/SYSTEM. La clave Django se genera si falta. La herramienta de pruebas también puede inicializar esa clave si aún no existe.

El proceso admite DB_PASSWORD/DB_PASSWORD_FILE y DJANGO_SECRET_KEY/DJANGO_SECRET_KEY_FILE como alternativas privadas; para pruebas DB_TEST_PASSWORD/DB_TEST_PASSWORD_FILE. No se cargan .env automáticamente ni se imprimen valores. No se deben apuntar archivos privados dentro del repositorio.

## Migraciones y preparación

Desde backend/:

```powershell
$backendPython = "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe"
$env:ELCHILITO_DB_SCOPE = 'local'
$env:ELCHILITO_DB_ROLE = 'migrador'
& $backendPython manage.py check
& $backendPython manage.py migrate --plan
& $backendPython manage.py migrate
$env:ELCHILITO_DB_ROLE = 'app'
& $backendPython manage.py preparar_huerto
```

**Ya ejecutado en esta entrega.** El SQL infra/00_preparar_postgresql_local.sql no se repite: la base y roles preexistían. migrate es la autoridad de estructura; no ejecutar el SQL de sqlmigrate por separado.

preparar_huerto es transaccional e idempotente: conserva nombres existentes, crea solo lo que falta y no concede acceso a cuentas. Resultado local: un huerto y tres zonas. No hay sensores, fechas de comunicación, lecturas o alertas inventadas.

Asignación explícita por operador local autorizado, cuando exista una cuenta real:

```powershell
& $backendPython manage.py asignar_huerto --email 'correo-de-la-cuenta' --huerto 1
```

La asignación no verifica el correo. La consulta necesita cuenta activa, correo verificado en allauth y membresía activa. Staff/superusuario no tiene un bypass implícito en el servicio de huertos. No se creó una cuenta ni membresía real en esta etapa.

## Pruebas aisladas

Desde backend/:

```powershell
& $backendPython -m tools.preparar_pruebas
$env:ELCHILITO_DB_SCOPE = 'test'
$env:ELCHILITO_DB_ROLE = 'migrador'
& $backendPython manage.py migrate
& $backendPython manage.py test --verbosity 2
```

tools.preparar_pruebas administra únicamente la base el_chilito_test y sus roles, usando PostgreSQL administrativo dentro del contenedor para provisionarlos. No resetea contraseñas existentes, ni borra/recrea bases. Las claves nuevas se generan y guardan privadamente sin salida.

manage.py test selecciona settings.testing por defecto. El runner exige el_chilito_test + el_chilito_test_app sin privilegios administrativos, no crea/destruye DB ni usa flush. Las pruebas TestCase revierten sus cambios; no conceder CREATEDB/TRUNCATE al rol app para hacerlas pasar. Ejecutar sin paralelismo.

Resultado de esta revisión: **34 pruebas actuales aprobadas**, independientes de las antiguas pruebas visuales. Comprueban restricciones SQL, rollback/idempotencia, permisos por huerto, compatibilidad headless, CSRF y recursos frontend compartidos.

## Configuración y límites

config/settings/base.py prepara sesión servidor/HttpOnly, CSRF y allauth. local.py fija loopback 127.0.0.1:5433, base/rol explícitos y excepciones Secure solo para HTTP local. No hay configuración de despliegue productivo ni autorización para publicar. runserver/WSGI/ASGI rechazan rol migrador. migrate exige rol migrador.

El backend puede servir directamente el dist existente, comprobado con Django TestClient, sin copiarlo. No se arrancó otro servidor ni se reemplazó el servidor visual activo en 8766. No ejecutar un segundo servidor en ese puerto. La sustitución del arranque y la conexión real de los formularios pertenecen a Etapa 2.

Las rutas headless se montan solo en el URLconf de pruebas para verificar compatibilidad; no se exponen en config/urls.py. Registro cerrado por ClosedRegistrationAdapter y correo bloqueado por DisabledEmailBackend, sin consola como sustituto de entrega. No se activa WebAuthn, MFA, proveedores externos, ARCO o IA.

La base local no se reinició durante estas pruebas. Se verificó persistencia desde procesos/conexiones independientes; respaldo/restauración y persistencia tras reinicio de servicios corresponden a Etapa 4.

Detalles/evidencia: [entrega de Etapa 1](../docs/ETAPA-1-DJANGO-Y-PERSISTENCIA.md).
