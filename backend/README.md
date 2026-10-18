# Backend de El Chilito
Estado: integración local real. Primero seguir [instalación del equipo](../docs/INSTALACION-EQUIPO.md). El frontend original se sirve desde Django, no desde un segundo servidor.
Dependencias fijadas en requirements-lock.txt; Python 3.13. PostgreSQL 17 en Docker; base el_chilito, roles separados el_chilito_migrador y el_chilito_app. Archivos privados fuera del proyecto, en %LOCALAPPDATA%/ElChilito/secrets.

## Migraciones y ejecución
La primera instalación usa infra/preparar_equipo.ps1. No repetir el SQL administrativo histórico sobre una base ya existente.
Para migraciones futuras, con respaldo y desde backend:
~~~powershell
$backendPython = "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe"
$env:DJANGO_SETTINGS_MODULE = 'config.settings.local'
$env:ELCHILITO_DB_SCOPE = 'local'
$env:ELCHILITO_DB_ROLE = 'migrador'
& $backendPython manage.py migrate --plan
& $backendPython manage.py migrate
$env:ELCHILITO_DB_ROLE = 'app'
~~~
El servidor exige rol app. El arranque habitual se hace desde infra/iniciar_aplicacion.ps1, no aplica migraciones.

## Asignar acceso autorizado
Con la cuenta ya registrada y correo verificado, desde backend con rol app:
~~~powershell
$backendPython = "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe"
$env:DJANGO_SETTINGS_MODULE = 'config.settings.local'
$env:ELCHILITO_DB_SCOPE = 'local'
$env:ELCHILITO_DB_ROLE = 'app'
& $backendPython manage.py preparar_huerto
& $backendPython manage.py asignar_huerto --email 'correo-de-la-cuenta' --huerto 1
~~~
Sustituir el correo y el ID por los reales de la instalación; preparar_huerto muestra el ID, conserva datos y no crea lecturas. Este comando es administrativo: no verifica correo ni debe ejecutarlo una persona sin autorización.

## Pruebas aisladas
Desde backend, con Docker activo:
~~~powershell
$backendPython = "$env:LOCALAPPDATA\ElChilito\venvs\backend\Scripts\python.exe"
& $backendPython -m tools.preparar_pruebas
$env:DJANGO_SETTINGS_MODULE = 'config.settings.local'
$env:ELCHILITO_DB_SCOPE = 'test'
$env:ELCHILITO_DB_ROLE = 'migrador'
& $backendPython manage.py migrate --noinput
$env:ELCHILITO_DB_ROLE = 'app'
& $backendPython manage.py test tests --verbosity 2 --settings=config.settings.testing
~~~
Usar una terminal separada para pruebas. No ejecutar en paralelo. El runner exige el_chilito_test/el_chilito_test_app sin privilegios administrativos, no destruye la base y revierte las transacciones de cada TestCase. No envía Gmail real.
La revisión visual usa Node/Playwright y herramientas adicionales descritas en la guía de presentación; no es requisito para abrir la aplicación.

## Registro y correo
El perfil local permite registro con confirmación técnica y verificación real. Los documentos legales siguen pendientes. Cada equipo configura Gmail propio con infra/configurar_correo_local.ps1; no compartir contraseñas.
El correo administrativo opcional usa manage.py comprobar_correo_local y solo envía al remitente privado autorizado. Las pruebas usan correo en memoria.

## Referencias
- [CI](../docs/CI-Y-PUBLICACION.md).
- [Contratos](../docs/CONTRATOS-INTEGRACION-LOCAL.md).
- [Presentación actual](../docs/INICIO-LOCAL-PRESENTACION.md).
- [Historial conservado](../docs/HISTORIAL-BACKEND-ANTES-CI.md).
