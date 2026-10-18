param([switch]$Infraestructura)
$ErrorActionPreference='Stop'
$chilitoRoot=Split-Path -Parent $PSScriptRoot
$chilitoPython=Join-Path $env:LOCALAPPDATA 'ElChilito\venvs\backend\Scripts\python.exe'
$chilitoNode='C:\Program Files\nodejs\node.exe'
if(-not (Test-Path -LiteralPath $chilitoPython)) { throw 'Falta el entorno del backend.' }
if(-not (Test-Path -LiteralPath $chilitoNode)) { throw 'Falta Node para las comprobaciones del navegador.' }
$chilitoDependencies='C:\Users\rafae\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
if(-not $env:NODE_PATH -and (Test-Path -LiteralPath $chilitoDependencies)) { $env:NODE_PATH=$chilitoDependencies }
if(-not $env:PLAYWRIGHT_BROWSERS_PATH) { $env:PLAYWRIGHT_BROWSERS_PATH=Join-Path $env:LOCALAPPDATA 'ms-playwright' }
$env:ELCHILITO_DB_SCOPE='local'
$env:ELCHILITO_DB_ROLE='app'
$env:DJANGO_SETTINGS_MODULE='config.settings.local'
Push-Location (Join-Path $chilitoRoot 'backend')
try {
    & $chilitoPython -m pip check
    if($LASTEXITCODE -ne 0) { throw 'Dependencias inconsistentes.' }
    & $chilitoPython manage.py check
    if($LASTEXITCODE -ne 0) { throw 'Fallo la comprobacion de Django.' }
    & $chilitoPython manage.py makemigrations --check --dry-run
    if($LASTEXITCODE -ne 0) { throw 'Hay cambios de modelos sin migracion.' }
    Get-ChildItem -LiteralPath (Join-Path $chilitoRoot 'dist') -Filter '*.js' -Recurse |
        Where-Object { $_.FullName -notlike '*\desarrollo\*' } |
        ForEach-Object {
            & $chilitoNode --check $_.FullName
            if($LASTEXITCODE -ne 0) { throw ('JavaScript no valido: '+$_.Name) }
        }
    & $chilitoPython manage.py test --verbosity 1
    if($LASTEXITCODE -ne 0) { throw 'Fallaron pruebas del servidor.' }
    & $chilitoPython tools/comprobar_frontend.py --etapa 2
    if($LASTEXITCODE -ne 0) { throw 'Fallo el recorrido de acceso.' }
    & $chilitoPython tools/comprobar_frontend.py --contrasenas
    if($LASTEXITCODE -ne 0) { throw 'Fallo la ayuda visual de contrasenas.' }
    & $chilitoPython tools/comprobar_registro_local.py
    if($LASTEXITCODE -ne 0) { throw 'Fallo el registro local aislado.' }
    & $chilitoPython tools/comprobar_frontend.py --etapa 3
    if($LASTEXITCODE -ne 0) { throw 'Fallo el recorrido del huerto.' }
    & $chilitoPython tools/comprobar_frontend.py --etapa 3 --responsive
    if($LASTEXITCODE -ne 0) { throw 'Fallo la adaptacion a telefono, tablet y escritorio.' }
    & $chilitoPython tools/comprobar_frontend.py --etapa 3 --vinculacion
    if($LASTEXITCODE -ne 0) { throw 'Fallo el huerto sin membresia o la vinculacion visual.' }
    if($Infraestructura) {
        Write-Host 'Se creara un respaldo privado y una NUEVA base aislada; luego se reiniciaran PostgreSQL y Django.'
        & $chilitoPython tools/verificar_respaldo_local.py
        if($LASTEXITCODE -ne 0) { throw 'Fallo la verificacion del respaldo.' }
        & $chilitoPython tools/verificar_reinicio_local.py
        if($LASTEXITCODE -ne 0) { throw 'Fallo la verificacion de reinicio.' }
    }
    Write-Host 'Verificacion local completada. No se enviaron correos reales ni se publico el proyecto.'
} finally { Pop-Location }
