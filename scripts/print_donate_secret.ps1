param(
    [string]$QrPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'assets\donate-qr.png')
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $QrPath)) {
    throw "QR file not found: $QrPath"
}

$bytes = [IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $QrPath).Path)
$base64 = [Convert]::ToBase64String($bytes)

Write-Host "QR file: $QrPath ($($bytes.Length) bytes)"
Write-Host ""
Write-Host "Run this to set the GitHub secret (one line):"
Write-Host ""
Write-Host "gh secret set CLIPORA_DONATE_QR_BASE64 --repo ertyu007/media-toolkit-Open-source --body `"$base64`""
