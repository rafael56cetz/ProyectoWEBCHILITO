# First installation, explicitly invoked. Never called by the normal startup script.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$chilitoRoot = Split-Path -Parent $PSScriptRoot
$chilitoVenv = Join-Path $env:LOCALAPPDATA 'ElChilito\venvs\backend'
$chilitoPython = Join-Path $chilitoVenv 'Scripts\python.exe'
$chilitoSaved = @{}
foreach ($name in @('DJANGO_SETTINGS_MODULE','ELCHILITO_DB_SCOPE','ELCHILITO_DB_ROLE')) {
    $chilitoSaved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
Push-Location $chilitoRoot
try {
    & docker info --format '{{.OSType}}'
    if ($LASTEXITCODE -ne 0) { throw 'Abre Docker Desktop con contenedores Linux y vuelve a ejecutar.' }
    & docker compose version
    if ($LASTEXITCODE -ne 0) { throw 'Se requiere Docker Compose v2.' }
    if (-not (Test-Path -LiteralPath $chilitoPython)) {
        & py -3.13 -m venv $chilitoVenv
        if ($LASTEXITCODE -ne 0) { throw 'Instala Python 3.13 con el lanzador py.' }
    }
    & $chilitoPython -m pip install -r (Join-Path $chilitoRoot 'backend\requirements-lock.txt')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias fijadas.' }
    Set-Location (Join-Path $chilitoRoot 'backend')
    & $chilitoPython -m tools.preparar_instalacion --solo-secretos
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron preparar los archivos privados.' }
    & docker compose -f (Join-Path $chilitoRoot 'compose.yaml') up -d --wait --wait-timeout 120 db
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL no inicio: revisa Docker, Internet o conflicto en 5433. No borres volumenes.' }
    & $chilitoPython -m tools.preparar_instalacion
    if ($LASTEXITCODE -ne 0) { throw 'Revisa roles y archivos privados; no se sobrescriben contrasenas existentes.' }
    $env:DJANGO_SETTINGS_MODULE = 'config.settings.local'
    $env:ELCHILITO_DB_SCOPE = 'local'
    $env:ELCHILITO_DB_ROLE = 'migrador'
    & $chilitoPython manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Migraciones incompletas; no continues con el arranque.' }
    $env:ELCHILITO_DB_ROLE = 'app'
    & $chilitoPython manage.py check
    if ($LASTEXITCODE -ne 0) { throw 'La configuracion no paso la revision de Django.' }
    & $chilitoPython manage.py preparar_huerto
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar el huerto.' }
    Write-Host 'Instalacion lista: sin cuentas, membresias o mediciones inventadas.'
    Write-Host 'Configura tu Gmail con infra\configurar_correo_local.ps1 y luego ejecuta infra\iniciar_aplicacion.ps1.'
} finally {
    Pop-Location
    foreach ($name in $chilitoSaved.Keys) {
        [Environment]::SetEnvironmentVariable($name, $chilitoSaved[$name], 'Process')
    }
}
