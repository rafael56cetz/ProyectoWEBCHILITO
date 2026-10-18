# Interactive private configuration. Does not send mail or change Google settings.
$ErrorActionPreference = 'Stop'
$chilitoPrivate = Join-Path $env:LOCALAPPDATA 'ElChilito\secrets'
$chilitoPasswordPath = Join-Path $chilitoPrivate 'gmail_app_password.txt'
$chilitoConfigurationPath = Join-Path $chilitoPrivate 'correo_local.json'
if ((Test-Path -LiteralPath $chilitoPasswordPath) -or (Test-Path -LiteralPath $chilitoConfigurationPath)) {
    throw 'Ya existe configuracion de correo. No se reemplazo; revisa los archivos privados antes de actualizarla.'
}
$chilitoSender = (Read-Host 'Gmail autorizado como remitente Y destinatario de pruebas').Trim().ToLowerInvariant()
try { $chilitoParsed = [System.Net.Mail.MailAddress]::new($chilitoSender) }
catch { throw 'Introduce una direccion Gmail valida que controles.' }
if ($chilitoParsed.Address -cne $chilitoSender -or $chilitoParsed.Host -ne 'gmail.com') {
    throw 'Esta configuracion admite una cuenta @gmail.com propia.'
}
$chilitoPassword = Read-Host 'Contrasena DE APLICACION de Google (no la contrasena normal de Gmail)' -AsSecureString
$chilitoPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($chilitoPassword)
try {
    $chilitoPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($chilitoPointer).Replace(' ', '')
    if ($chilitoPlain -notmatch '^[a-zA-Z0-9]{16}$') { throw 'Se esperan los 16 caracteres de una contrasena de aplicacion de Google.' }
    New-Item -ItemType Directory -Force -Path $chilitoPrivate | Out-Null
    $chilitoIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    & icacls.exe $chilitoPrivate /inheritance:r /grant:r "${chilitoIdentity}:(OI)(CI)F" 'SYSTEM:(OI)(CI)F' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron limitar los permisos privados.' }
    $chilitoBytes = [Text.Encoding]::UTF8.GetBytes($chilitoPlain)
    $chilitoStream = [IO.File]::Open($chilitoPasswordPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $chilitoStream.Write($chilitoBytes, 0, $chilitoBytes.Length) } finally { $chilitoStream.Dispose() }
    $chilitoConfig = @{sender=$chilitoSender; authorized_recipients=@($chilitoSender)} | ConvertTo-Json
    $chilitoConfigStream = [IO.File]::Open($chilitoConfigurationPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $chilitoConfigBytes = [Text.Encoding]::UTF8.GetBytes($chilitoConfig)
        $chilitoConfigStream.Write($chilitoConfigBytes, 0, $chilitoConfigBytes.Length)
    } finally { $chilitoConfigStream.Dispose() }
    Write-Host 'Configuracion privada guardada. No se envio ningun correo.'
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($chilitoPointer)
    if ($chilitoBytes) { [Array]::Clear($chilitoBytes, 0, $chilitoBytes.Length) }
    $chilitoPlain = $null
    $chilitoPassword.Dispose()
}
