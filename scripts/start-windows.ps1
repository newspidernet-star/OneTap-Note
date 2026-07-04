# Smart Scribe - Windows one-click start
# Entry: start-windows.bat (calls this); or run manually:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-windows.ps1

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$pyExe = Join-Path $Root 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $pyExe)) {
    throw 'Not installed. Double-click start-windows.bat first (auto-installs), or run scripts\setup-windows.ps1'
}

# Proxy (for yt-dlp / cloudflared to reach the internet; does not affect localhost)
$proxy = $env:HTTPS_PROXY
if (-not $proxy) {
    try { if (Get-NetTCPConnection -LocalPort 7897 -State Listen -ErrorAction SilentlyContinue) { $proxy = 'http://127.0.0.1:7897' } } catch {}
}
if ($proxy) { $env:HTTPS_PROXY = $proxy; $env:HTTP_PROXY = $proxy }
$env:NO_PROXY = 'localhost,127.0.0.1,::1'

# Backend starts from backend/ dir (.env and app package live here)
Set-Location (Join-Path $Root 'backend')

Write-Host "Starting Smart Scribe ...  browser will open http://localhost:8000" -ForegroundColor Cyan
Write-Host "(Ctrl+C to stop)" -ForegroundColor DarkGray
Start-Process 'http://localhost:8000'
& $pyExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
