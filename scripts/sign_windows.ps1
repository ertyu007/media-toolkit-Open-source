<#
.SYNOPSIS
Signs a Windows PE file (or installer) with Authenticode.

.DESCRIPTION
Uses signtool.exe to sign a single file with SHA-256 and an RFC 3161
timestamp. Two signing backends are supported:

  1. Traditional .pfx certificate (CLIPORA_CERT_PATH + CLIPORA_CERT_PASSWORD)
  2. Azure Trusted Signing (CLIPORA_AZURE_ACCOUNT_URI + CLIPORA_AZURE_CLIENT_SECRET + ...)

If no signing backend is configured, the script exits 0 without modifying
the file so unsigned builds still succeed.

Environment variables:
  CLIPORA_SIGNTOOL             Path to signtool.exe (searched automatically if unset)
  CLIPORA_CERT_PATH            Path to a .pfx file
  CLIPORA_CERT_PASSWORD        Password for the .pfx file
  CLIPORA_AZURE_ACCOUNT_URI    Trusted Signing account endpoint URI
  CLIPORA_AZURE_CLIENT_ID      Application (client) id for Azure AD (optional)
  CLIPORA_AZURE_CLIENT_SECRET  Client secret for Azure AD
  CLIPORA_AZURE_TENANT         Tenant id for Azure AD (optional)
  CLIPORA_AZURE_CERT_PROFILE   Certificate profile name
  CLIPORA_AZURE_CERT_NAME      Certificate name
  CLIPORA_TIMESTAMP_URL        RFC 3161 timestamp server (default http://timestamp.digicert.com)

.EXAMPLE
  & scripts/sign_windows.ps1 -Path "dist\Clipora\Clipora.exe" -Description "Clipora" -Url "https://github.com/ertyu007/media-toolkit-Open-source"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Path,

    [string]$Description = 'Clipora',

    [string]$Url = 'https://github.com/ertyu007/media-toolkit-Open-source'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Path)) {
    throw "File to sign not found: $Path"
}

function Find-Signtool {
    if ($env:CLIPORA_SIGNTOOL -and (Test-Path -LiteralPath $env:CLIPORA_SIGNTOOL)) {
        return $env:CLIPORA_SIGNTOOL
    }
    $candidates = @(
        (Get-Command signtool.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
    )
    $kitsRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
    if (Test-Path -LiteralPath $kitsRoot) {
        $candidates += Get-ChildItem -LiteralPath $kitsRoot -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -ExpandProperty FullName
    }
    return ($candidates | Where-Object { $_ } | Select-Object -First 1)
}

$certPath = $env:CLIPORA_CERT_PATH
$azureAccountUri = $env:CLIPORA_AZURE_ACCOUNT_URI

if (-not $certPath -and -not $azureAccountUri) {
    Write-Host "Signing not configured for $Path - skipping (set CLIPORA_CERT_PATH or CLIPORA_AZURE_ACCOUNT_URI to enable)."
    exit 0
}

$signtool = Find-Signtool
if (-not $signtool) {
    throw 'signtool.exe not found. Install the Windows SDK or set CLIPORA_SIGNTOOL.'
}

$timestampUrl = if ($env:CLIPORA_TIMESTAMP_URL) { $env:CLIPORA_TIMESTAMP_URL } else { 'http://timestamp.digicert.com' }

$common = @(
    '/fd', 'SHA256',
    '/tr', $timestampUrl,
    '/td', 'SHA256',
    '/d', $Description,
    '/du', $Url,
    '/v'
)

if ($certPath) {
    if (-not (Test-Path -LiteralPath $certPath)) {
        throw "Signing certificate not found: $certPath"
    }
    $arguments = @(
        'sign',
        '/f', (Resolve-Path -LiteralPath $certPath).Path
    ) + $common
    if ($env:CLIPORA_CERT_PASSWORD) {
        $arguments += @('/p', $env:CLIPORA_CERT_PASSWORD)
    }
}
else {
    if (-not $env:CLIPORA_AZURE_CLIENT_SECRET) {
        throw 'CLIPORA_AZURE_CLIENT_SECRET is required for Azure Trusted Signing.'
    }
    if (-not $env:CLIPORA_AZURE_CERT_PROFILE) {
        throw 'CLIPORA_AZURE_CERT_PROFILE is required for Azure Trusted Signing.'
    }
    $arguments = @(
        'sign'
    ) + $common + @(
        '/kvu', $azureAccountUri,
        '/kvs', $env:CLIPORA_AZURE_CLIENT_SECRET,
        '/kvp', $env:CLIPORA_AZURE_CERT_PROFILE
    )
    if ($env:CLIPORA_AZURE_CLIENT_ID) {
        $arguments += @('/kvc', $env:CLIPORA_AZURE_CLIENT_ID)
    }
    if ($env:CLIPORA_AZURE_TENANT) {
        $arguments += @('/kvt', $env:CLIPORA_AZURE_TENANT)
    }
    if ($env:CLIPORA_AZURE_CERT_NAME) {
        $arguments += @('/kc', $env:CLIPORA_AZURE_CERT_NAME)
    }
}

$targetPath = (Resolve-Path -LiteralPath $Path).Path
$arguments += $targetPath

Write-Host "Signing $Path with $signtool"
& $signtool $arguments
if ($LASTEXITCODE -ne 0) {
    throw "signtool failed with exit code $LASTEXITCODE"
}

$signature = Get-AuthenticodeSignature -LiteralPath $Path
if ($signature.Status -ne 'Valid') {
    throw "Signature verification failed for $Path (status: $($signature.Status))."
}
Write-Host "Signed and verified: $Path (status: $($signature.Status))"
