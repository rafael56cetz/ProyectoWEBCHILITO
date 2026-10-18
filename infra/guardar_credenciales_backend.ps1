# Introduce existing role passwords privately; this script never changes PostgreSQL.
$ErrorActionPreference = 'Stop'
$privateDir = Join-Path $env:LOCALAPPDATA 'ElChilito\secrets'
[IO.Directory]::CreateDirectory($privateDir) | Out-Null
$currentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value

function Write-PrivateFile([string]$path, [string]$value) {
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes($value)
    $stream = [IO.File]::Open($path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try { $stream.Write($bytes, 0, $bytes.Length) }
    finally { $stream.Dispose(); [Array]::Clear($bytes, 0, $bytes.Length) }
    $userGrant = '*' + $currentSid + ':(F)'
    & icacls.exe $path /inheritance:r /grant:r $userGrant '*S-1-5-18:(F)' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron restringir los permisos del archivo privado.' }
}

foreach ($roleName in @('el_chilito_migrador', 'el_chilito_app')) {
    $secretPath = Join-Path $privateDir ($roleName + '.txt')
    if (Test-Path -LiteralPath $secretPath) {
        Write-Host "$roleName ya tiene archivo privado; no se modifica."
        continue
    }
    $secureValue = Read-Host "Contrasena EXISTENTE de $roleName (no se mostrara)" -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
    try {
        $plainValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        if (-not $plainValue) { throw 'No se admite una contrasena vacia.' }
        Write-PrivateFile $secretPath $plainValue
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        $plainValue = $null
        $secureValue.Dispose()
    }
}
$keyPath = Join-Path $privateDir 'django_secret_key.txt'
if (-not (Test-Path -LiteralPath $keyPath)) {
    $randomBytes = New-Object byte[] 64
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($randomBytes)
        Write-PrivateFile $keyPath ([Convert]::ToBase64String($randomBytes))
    } finally {
        $generator.Dispose()
        [Array]::Clear($randomBytes, 0, $randomBytes.Length)
    }
}
Write-Host 'Archivos privados preparados. No compartas su contenido.'
