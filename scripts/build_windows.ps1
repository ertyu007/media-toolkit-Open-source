param(
    [switch]$SkipTools
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'
if ($LASTEXITCODE -ne 0) {
    throw 'Clipora release build requires Python 3.10 or newer.'
}

python scripts/generate_icon.py
python -m PyInstaller --noconfirm --clean packaging/clipora.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

if (-not $SkipTools) {
    Write-Host 'Staging bundled tools (FFmpeg, yt-dlp, Deno) into the installer...'
    python scripts/stage_bundled_tools.py --dest (Join-Path $projectRoot 'dist\Clipora\tools')
    if ($LASTEXITCODE -ne 0) {
        throw "Tool staging failed with exit code $LASTEXITCODE"
    }
}

& $PSScriptRoot\sign_windows.ps1 `
    -Path (Join-Path $projectRoot 'dist\Clipora\Clipora.exe') `
    -Description 'Clipora desktop media toolkit' `
    -Url 'https://github.com/ertyu007/media-toolkit-Open-source'
if ($LASTEXITCODE -ne 0) {
    throw "Signing Clipora.exe failed with exit code $LASTEXITCODE"
}

$isccCandidates = @(
    (Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
$iscc = $isccCandidates | Select-Object -First 1
if (-not $iscc) {
    throw 'ไม่พบ Inno Setup 6: https://jrsoftware.org/isdl.php'
}

$version = python -c 'from clipora import __version__; print(__version__)'
& $iscc "/DAppVersion=$version" packaging/clipora.iss
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE"
}

$installer = Join-Path $projectRoot "dist\installer\Clipora-Setup-$version-x64.exe"

& $PSScriptRoot\sign_windows.ps1 `
    -Path $installer `
    -Description 'Clipora Setup' `
    -Url 'https://github.com/ertyu007/media-toolkit-Open-source'
if ($LASTEXITCODE -ne 0) {
    throw "Signing installer failed with exit code $LASTEXITCODE"
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash.ToLowerInvariant()
$checksumPath = "$installer.sha256"
Set-Content -LiteralPath $checksumPath -Value "$hash  $(Split-Path -Leaf $installer)" -Encoding ascii

Write-Host "Built: $installer"
Write-Host "SHA256: $hash"
