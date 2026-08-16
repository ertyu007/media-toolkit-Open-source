# ตรวจสอบว่ามี yt-dlp-android เวอร์ชันใหม่กว่าโปรเจกต์หรือยัง
# รัน:  powershell -ExecutionPolicy Bypass -File tools\check_ytdlp_update.ps1
$ErrorActionPreference = "Stop"

$metadataUrl = "https://repo1.maven.org/maven2/dev/ffmpegkit-maintained/yt-dlp-android/maven-metadata.xml"
$buildFile = Join-Path $PSScriptRoot "..\android\app\build.gradle.kts"

$latestXml = (Invoke-WebRequest $metadataUrl -UseBasicParsing).Content
$latestVersion = [regex]::Match($latestXml, "<latest>(.*?)</latest>").Groups[1].Value

$currentLine = (Get-Content $buildFile | Select-String 'yt-dlp-android:').Line
$currentVersion = [regex]::Match($currentLine, 'yt-dlp-android:(\d+\.\d+\.\d+)').Groups[1].Value

Write-Host "เวอร์ชันในโปรเจกต์ : $currentVersion"
Write-Host "เวอร์ชันล่าสุด (Maven): $latestVersion"

if (-not $latestVersion -or -not $currentVersion) {
    Write-Host "อ่านเวอร์ชันไม่สำเร็จ" -ForegroundColor Red
    exit 1
}

if ([version]$latestVersion -gt [version]$currentVersion) {
    Write-Host ""
    Write-Host "*** มีอัปเดตของ yt-dlp ***" -ForegroundColor Yellow
    Write-Host "แก้เวอร์ชันใน android/app/build.gradle.kts" -ForegroundColor Yellow
    Write-Host "  dev.ffmpegkit-maintained:yt-dlp-android:$currentVersion"
    Write-Host "  เป็น $latestVersion แล้วรัน: flutter build apk --release --split-per-abi" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "ใช้เวอร์ชันล่าสุดแล้ว ไม่ต้องอัปเดต" -ForegroundColor Green
}