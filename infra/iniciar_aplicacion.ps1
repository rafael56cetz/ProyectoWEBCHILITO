[CmdletBinding()]
param(
    [switch]$NoAbrirNavegador,
    [switch]$Detener
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$chilitoRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$chilitoPython = Join-Path $env:LOCALAPPDATA 'ElChilito\venvs\backend\Scripts\python.exe'
$chilitoUrl = 'http://127.0.0.1:8766/index.html'
$chilitoData = Join-Path $env:LOCALAPPDATA 'ElChilito'
$chilitoLog = Join-Path $chilitoData 'logs\inicio-local.log'
$chilitoStateFile = Join-Path $chilitoData 'runtime\inicio-local.json'
$chilitoFailure = $null
$chilitoStarted = $null
$chilitoState = $null
$chilitoPreviousEnvironment = @{}
foreach ($key in @('DJANGO_SETTINGS_MODULE','ELCHILITO_DB_SCOPE','ELCHILITO_DB_ROLE')) {
    $chilitoPreviousEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
}

function Write-ChilitoStatus([string]$Message) {
    Write-Host $Message
    Add-Content -LiteralPath $chilitoLog -Encoding UTF8 -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + $Message)
}
function Stop-ChilitoStart([string]$Message) {
    $script:chilitoFailure = $Message
    throw 'Inicio local incompleto.'
}
function Invoke-ChilitoCommand([string]$Executable, [string[]]$Arguments, [int]$TimeoutSeconds = 15, [string]$Directory = $chilitoRoot) {
    # Arguments contain only fixed commands/paths and encoded source, never secret values.
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $Executable
    $info.Arguments = (($Arguments | ForEach-Object { '"' + $_.Replace('"','\"') + '"' }) -join ' ')
    $info.WorkingDirectory = $Directory
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $info
    try {
        [void]$process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            # Only the temporary command created here; never an existing service.
            if (-not $process.HasExited) {
                $killer = Start-Process -FilePath "$env:SystemRoot\System32\taskkill.exe" -ArgumentList @('/PID',[string]$process.Id,'/T','/F') -WindowStyle Hidden -PassThru
                [void]$killer.WaitForExit(5000)
                $killer.Dispose()
            }
            return [pscustomobject]@{ Code = -1; Output = ''; TimedOut = $true }
        }
        $process.WaitForExit()
        [void]$stderr.GetAwaiter().GetResult() # Do not log raw diagnostics or private configuration.
        return [pscustomobject]@{ Code = $process.ExitCode; Output = $stdout.GetAwaiter().GetResult().Trim(); TimedOut = $false }
    } finally { $process.Dispose() }
}
function Get-ChilitoListeners {
    @(Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue)
}
function Test-ChilitoPython($Process) {
    $Process -and $Process.CommandLine -and
        $Process.CommandLine -match [regex]::Escape($chilitoPython) -and
        $Process.CommandLine -match 'manage\.py"?\s+runserver\s+127\.0\.0\.1:8766\s+--noreload'
}
function Get-ChilitoRecordedProcess {
    if (-not $script:chilitoState -or $script:chilitoState.ProjectRoot -cne $chilitoRoot) { return $null }
    $recorded = Get-CimInstance Win32_Process -Filter ("ProcessId = " + [int]$script:chilitoState.ProcessId) -ErrorAction SilentlyContinue
    if ((Test-ChilitoPython $recorded) -and
        $recorded.CreationDate.ToUniversalTime().ToString('o') -ceq $script:chilitoState.CreatedUtc) { return $recorded }
    return $null
}
function Test-ChilitoListener($Listener) {
    if ($Listener.LocalAddress -ne '127.0.0.1') { return $false }
    $current = Get-CimInstance Win32_Process -Filter ("ProcessId = " + [int]$Listener.OwningProcess) -ErrorAction SilentlyContinue
    if (-not (Test-ChilitoPython $current)) { return $false }
    $recorded = Get-ChilitoRecordedProcess
    for ($level = 0; $current -and $level -lt 6; $level++) {
        if ($recorded -and $current.ProcessId -eq $recorded.ProcessId) { return $true }
        if ($current.CommandLine -and $current.Name -match '^(powershell|pwsh)\.exe$' -and
            $current.CommandLine -match [regex]::Escape((Join-Path $chilitoRoot 'infra\iniciar_aplicacion.ps1'))) { return $true }
        $current = Get-CimInstance Win32_Process -Filter ("ProcessId = " + [int]$current.ParentProcessId) -ErrorAction SilentlyContinue
    }
    return $false
}
function Test-ChilitoWeb {
    try {
        $response = Invoke-WebRequest -Uri $chilitoUrl -UseBasicParsing -TimeoutSec 3
        $expected = [IO.File]::ReadAllText((Join-Path $chilitoRoot 'dist\index.html'))
        if ($response.StatusCode -ne 200 -or $response.Content -cne $expected) { return $false }
        $config = Invoke-RestMethod -Uri 'http://127.0.0.1:8766/api/acceso/configuracion' -TimeoutSec 3
        return ($config.registrationAllowed -is [bool] -and $config.password.minLength -eq 15 -and
            $config.password.maxLength -eq 256 -and $config.code.length -eq 6)
    } catch { return $false }
}

try {
    [void][IO.Directory]::CreateDirectory((Join-Path $chilitoData 'logs'))
    [void][IO.Directory]::CreateDirectory((Join-Path $chilitoData 'runtime'))
    if (Test-Path -LiteralPath $chilitoStateFile) {
        try { $chilitoState = Get-Content -LiteralPath $chilitoStateFile -Raw | ConvertFrom-Json } catch { $chilitoState = $null }
    }
    if ($Detener) {
        $owned = Get-ChilitoRecordedProcess
        $stoppingExisting = $false
        if (-not $owned) {
            $listeners = @(Get-ChilitoListeners)
            if (-not $listeners.Count) {
                Write-ChilitoStatus 'No hay un servidor escuchando en 8766. No se detuvo ningun servicio.'
                return
            }
            if ($listeners.Count -ne 1 -or -not (Test-ChilitoListener $listeners[0]) -or -not (Test-ChilitoWeb)) {
                Stop-ChilitoStart 'Parada: no se pudo verificar que el servicio sea este proyecto. Usa su terminal de origen; no se detuvo ningun proceso.'
            }
            $owned = Get-CimInstance Win32_Process -Filter ("ProcessId = " + [int]$listeners[0].OwningProcess)
            # Include the venv redirector, but never stop its PowerShell parent.
            for ($level = 0; $level -lt 4; $level++) {
                $parent = Get-CimInstance Win32_Process -Filter ("ProcessId = " + [int]$owned.ParentProcessId) -ErrorAction SilentlyContinue
                if (-not (Test-ChilitoPython $parent)) { break }
                $owned = $parent
            }
            $stoppingExisting = $true
        }
        $stop = Invoke-ChilitoCommand "$env:SystemRoot\System32\taskkill.exe" @('/PID',[string]$owned.ProcessId,'/T','/F')
        if ($stop.Code -ne 0) { Stop-ChilitoStart 'Django: no se pudo detener el proceso propio. Revisa la terminal que lo inicio.' }
        if (-not $stoppingExisting) {
            $chilitoState | Add-Member -NotePropertyName StoppedUtc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
            $chilitoState | ConvertTo-Json | Set-Content -LiteralPath $chilitoStateFile -Encoding UTF8
            Write-ChilitoStatus 'Django propio detenido. PostgreSQL y Docker Desktop siguen activos; los datos se conservan.'
        } else {
            Write-ChilitoStatus 'Django existente del proyecto detenido por solicitud explicita. PostgreSQL y Docker Desktop siguen activos.'
        }
        return
    }

    if (-not (Test-Path -LiteralPath $chilitoPython)) { Stop-ChilitoStart 'Python: falta el entorno existente. Consulta backend/README.md; este inicio no instala dependencias.' }
    $listeners = @(Get-ChilitoListeners)
    foreach ($listener in $listeners) {
        if (-not (Test-ChilitoListener $listener)) { Stop-ChilitoStart 'Puerto 8766: hay un proceso que no se pudo identificar como este proyecto. No se cerro ni se cambio la URL.' }
    }

    $desktopCandidates = @(
        (Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'),
        (Join-Path $env:LOCALAPPDATA 'Docker\Docker Desktop.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\Docker Desktop.exe')
    )
    $desktop = $desktopCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    $dockerCommand = Get-Command docker.exe -ErrorAction SilentlyContinue
    $docker = if ($dockerCommand) { $dockerCommand.Source } elseif ($desktop) {
        Join-Path (Split-Path -Parent $desktop) 'resources\bin\docker.exe'
    } else { $null }
    if (-not $docker -or -not (Test-Path -LiteralPath $docker)) { Stop-ChilitoStart 'Docker: no se encontro Docker Desktop/CLI. Instala o revisa Docker Desktop antes de presentar.' }
    if ($env:DOCKER_HOST -and $env:DOCKER_HOST -notlike 'npipe://*') {
        Stop-ChilitoStart 'Docker: DOCKER_HOST no apunta a un motor local de Windows. Revisa el contexto antes de iniciar.'
    }
    $context = Invoke-ChilitoCommand $docker @('context','inspect','--format','{{.Endpoints.docker.Host}}') 10
    if ($context.Code -ne 0 -or $context.Output -notlike 'npipe://*') {
        Stop-ChilitoStart 'Docker: selecciona un contexto local de Docker Desktop. No se iniciaran servicios en un motor remoto.'
    }
    $engine = Invoke-ChilitoCommand $docker @('info','--format','{{.ServerVersion}}') 15
    if ($engine.Code -ne 0) {
        if (-not $desktop) { Stop-ChilitoStart 'Docker: el motor no responde y no se encontro Docker Desktop. Abre Desktop manualmente y repite el comando.' }
        Write-ChilitoStatus 'Docker Desktop: iniciando y esperando al motor (hasta 120 segundos)...'
        Start-Process -FilePath $desktop -WindowStyle Hidden | Out-Null
        $deadline = [DateTime]::UtcNow.AddSeconds(120)
        do {
            Start-Sleep -Seconds 2
            $engine = Invoke-ChilitoCommand $docker @('info','--format','{{.ServerVersion}}') 5
        } while ($engine.Code -ne 0 -and [DateTime]::UtcNow -lt $deadline)
        if ($engine.Code -ne 0) { Stop-ChilitoStart 'Docker: el motor no estuvo listo a tiempo. Revisa Desktop, WSL y cualquier aviso inicial; despues repite el comando.' }
    }
    Write-ChilitoStatus 'Docker: motor disponible.'
    $composeVersion = Invoke-ChilitoCommand $docker @('compose','version') 10
    if ($composeVersion.Code -ne 0) { Stop-ChilitoStart 'Docker Compose: no esta disponible. Revisa la instalacion de Docker Desktop.' }
    $volume = Invoke-ChilitoCommand $docker @('volume','inspect','el-chilito_pgdata') 10
    if ($volume.Code -ne 0) { Stop-ChilitoStart 'PostgreSQL: falta el volumen existente el-chilito_pgdata. No se creo ni se restauro una base. Revisa su preparacion o el contexto Docker.' }
    $composeArgs = @('compose','--project-directory',$chilitoRoot,'-f',(Join-Path $chilitoRoot 'compose.yaml'))
    $before = Invoke-ChilitoCommand $docker ($composeArgs + @('ps','-q','db')) 10
    if ($before.Code -ne 0) { Stop-ChilitoStart 'PostgreSQL: no se pudo consultar el servicio db del proyecto. Revisa Docker Compose.' }
    $databaseWasRunning = -not [string]::IsNullOrWhiteSpace($before.Output)
    $up = Invoke-ChilitoCommand $docker ($composeArgs + @('up','-d','--no-recreate','--no-deps','--pull','never','--wait','--wait-timeout','45','db')) 60
    if ($up.Code -ne 0) { Stop-ChilitoStart 'PostgreSQL: db no alcanzo un estado saludable. Revisa docker compose ps y las credenciales privadas; no borres el volumen.' }
    if ($databaseWasRunning) { Write-ChilitoStatus 'PostgreSQL: saludable; servicio existente reutilizado.' }
    else { Write-ChilitoStatus 'PostgreSQL: servicio db iniciado y saludable; volumen existente conservado.' }

    $env:DJANGO_SETTINGS_MODULE = 'config.settings.local'
    $env:ELCHILITO_DB_SCOPE = 'local'
    $env:ELCHILITO_DB_ROLE = 'app'
    # Read-only preflight: no migrate, user/session/cache writes, or email delivery.
    $code = @'
import json,sys
try:
    import django
    django.setup()
    from django.core.checks import run_checks, ERROR
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    errors=[item.id for item in run_checks() if item.level >= ERROR]
    if errors:
        print(json.dumps({"status":"configuration-error"}));sys.exit(2)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(),current_user")
        identity=cursor.fetchone()
    if identity != ("el_chilito","el_chilito_app"):
        print(json.dumps({"status":"database-identity-error"}));sys.exit(2)
    executor=MigrationExecutor(connection)
    pending=len(executor.migration_plan(executor.loader.graph.leaf_nodes()))
    if pending:
        print(json.dumps({"status":"pending-migrations","count":pending}));sys.exit(3)
    from cuentas.email import mail_configuration
    try:
        mail_configuration()
        mail=True
    except Exception:
        mail=False
    print(json.dumps({"status":"ready","mailConfigured":mail}))
except Exception:
    print(json.dumps({"status":"configuration-or-database-error"}));sys.exit(2)
'@
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($code))
    $preflight = Invoke-ChilitoCommand $chilitoPython @('-c',("import base64;exec(base64.b64decode('" + $encoded + "'))")) 30 (Join-Path $chilitoRoot 'backend')
    if ($preflight.Code -eq 3) { Stop-ChilitoStart 'Django: hay migraciones pendientes. No se aplicaron. Solicita revisar/aplicar las migraciones antes de presentar.' }
    if ($preflight.Code -ne 0) { Stop-ChilitoStart 'Django/PostgreSQL: fallo la comprobacion de configuracion, rol o conexion. Revisa los archivos privados y ejecuta manage.py check con el perfil local.' }
    $readiness = $preflight.Output | ConvertFrom-Json
    if ($readiness.status -ne 'ready') { Stop-ChilitoStart 'Django: la comprobacion previa no confirmo el estado esperado. Revisa la configuracion local.' }
    Write-ChilitoStatus 'Django: configuracion y conexion verificadas; sin migraciones pendientes.'
    if (-not $readiness.mailConfigured) { Write-ChilitoStatus 'Correo: configuracion privada no disponible. La web puede abrir; el envio necesita revision. No se envio ningun mensaje.' }
    else { Write-ChilitoStatus 'Correo: configuracion privada disponible. El inicio no envia mensajes ni garantiza su recepcion.' }

    $listeners = @(Get-ChilitoListeners)
    if (-not $listeners.Count) {
        $chilitoStarted = Start-Process -FilePath $chilitoPython -ArgumentList @('manage.py','runserver','127.0.0.1:8766','--noreload') -WorkingDirectory (Join-Path $chilitoRoot 'backend') -WindowStyle Hidden -PassThru
        $owned = Get-CimInstance Win32_Process -Filter ("ProcessId = " + $chilitoStarted.Id)
        $chilitoState = [pscustomobject]@{
            ProjectRoot = $chilitoRoot
            ProcessId = $owned.ProcessId
            CreatedUtc = $owned.CreationDate.ToUniversalTime().ToString('o')
            DatabaseStartedThisRun = (-not $databaseWasRunning)
        }
        $chilitoState | ConvertTo-Json | Set-Content -LiteralPath $chilitoStateFile -Encoding UTF8
        Write-ChilitoStatus 'Django: iniciando servidor propio en 127.0.0.1:8766...'
    } else {
        Write-ChilitoStatus 'Django: comprobando el servidor existente del proyecto...'
    }
    $ready = $false
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        $listeners = @(Get-ChilitoListeners)
        $identified = $listeners.Count -eq 1 -and (Test-ChilitoListener $listeners[0])
        if ($identified -and (Test-ChilitoWeb)) { $ready = $true; break }
        if ($listeners.Count -and -not $identified) { Stop-ChilitoStart 'Puerto 8766: la identidad del servicio no coincide. No se detuvo ningun proceso ajeno.' }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    if (-not $ready) { Stop-ChilitoStart 'Django: la web y su endpoint no estuvieron listos a tiempo. Consulta el registro de inicio y revisa manage.py check.' }
    Write-ChilitoStatus ('El Chilito listo: ' + $chilitoUrl)
    if (-not $NoAbrirNavegador) {
        try { Start-Process -FilePath $chilitoUrl | Out-Null }
        catch { Write-ChilitoStatus ('Navegador: abre manualmente ' + $chilitoUrl) }
    }
} catch {
    if ($chilitoStarted) {
        $owned = Get-ChilitoRecordedProcess
        if ($owned -and $owned.ProcessId -eq $chilitoStarted.Id) {
            [void](Invoke-ChilitoCommand "$env:SystemRoot\System32\taskkill.exe" @('/PID',[string]$owned.ProcessId,'/T','/F'))
        }
    }
    if (-not $chilitoFailure) {
        Write-ChilitoStatus ('Diagnostico del inicio: ' + $_.Exception.GetType().Name + '; linea ' + $_.InvocationInfo.ScriptLineNumber + '. No se registran valores privados.')
        $chilitoFailure = 'Inicio local: no se completo una comprobacion. Revisa requisitos, permisos del usuario y el registro de inicio; no se cambiaron datos.'
    }
    Write-ChilitoStatus $chilitoFailure
    throw $chilitoFailure
} finally {
    foreach ($key in $chilitoPreviousEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($key, $chilitoPreviousEnvironment[$key], 'Process')
    }
}
