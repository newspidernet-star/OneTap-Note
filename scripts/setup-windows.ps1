# Smart Scribe - Windows one-click setup
# Entry: start-windows.bat (calls this on first run); or run manually:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup-windows.ps1

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Write-Host "== Smart Scribe Windows Setup ==" -ForegroundColor Cyan

# --- Auto-detect proxy (clash default port 7897) ---
$proxy = $env:HTTPS_PROXY
if (-not $proxy) {
    try { if (Get-NetTCPConnection -LocalPort 7897 -State Listen -ErrorAction SilentlyContinue) { $proxy = 'http://127.0.0.1:7897' } } catch {}
}
if ($proxy) {
    $env:HTTPS_PROXY = $proxy; $env:HTTP_PROXY = $proxy; $env:NO_PROXY = 'localhost,127.0.0.1,::1'
    Write-Host "Proxy detected: $proxy" -ForegroundColor Green
} else {
    Write-Host "No proxy detected. If download is slow/fails, set `$env:HTTPS_PROXY='http://127.0.0.1:7897' and rerun" -ForegroundColor Yellow
}

function Update-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
}
function Ensure-Winget($PackageId, $TestCmd) {
    if (Get-Command $TestCmd -ErrorAction SilentlyContinue) { return }
    Write-Host "Installing $PackageId ..." -ForegroundColor Yellow
    winget install $PackageId --accept-source-agreements --accept-package-agreements --silent --disable-interactivity
    Update-Path
}

# --- 1. System dependencies ---
# Python 3.11: handle separately since `py` may exist but 3.11 not installed
$needPy31 = $true
try { $null = py -3.11 --version 2>$null; if ($?) { $needPy31 = $false } } catch {}
if ($needPy31) {
    Write-Host "Installing Python.Python.3.11 ..." -ForegroundColor Yellow
    winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements --silent --disable-interactivity
    Update-Path
}
try { Write-Host "Python: $(py -3.11 --version)" -ForegroundColor Green } catch { throw 'Python 3.11 install failed, try manually: winget install Python.Python.3.11' }

Ensure-Winget 'OpenJS.NodeJS.LTS' 'node'
Ensure-Winget 'Gyan.FFmpeg' 'ffmpeg'
Ensure-Winget 'Cloudflare.cloudflared' 'cloudflared'

# --- 2. Backend venv ---
$venv = Join-Path $Root 'backend\.venv'
$pyExe = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $pyExe)) {
    Write-Host "Creating venv backend\.venv ..." -ForegroundColor Yellow
    py -3.11 -m venv $venv
}
& $pyExe -m pip install --upgrade pip wheel | Out-Null
Write-Host "Installing backend deps (Windows cloud-OCR subset)..." -ForegroundColor Yellow
& $pyExe -m pip install -r (Join-Path $Root 'backend\requirements-windows.txt')
Write-Host "Installing Playwright Chromium ..." -ForegroundColor Yellow
& $pyExe -m playwright install chromium

# --- 3. Frontend build ---
$frontend = Join-Path $Root 'frontend'
$dist = Join-Path $frontend 'dist'
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host "npm install (frontend) ..." -ForegroundColor Yellow
    Push-Location $frontend; npm install; Pop-Location
}
Write-Host "Building frontend (npm run build) ..." -ForegroundColor Yellow
Push-Location $frontend; npm run build; Pop-Location
if (-not (Test-Path (Join-Path $dist 'index.html'))) { throw 'Frontend build failed: frontend\dist\index.html not found' }

# --- 4. .env ---
$envFile = Join-Path $Root 'backend\.env'
if (-not (Test-Path $envFile)) {
    Write-Host "Generating backend\.env (cloud OCR + auto tunnel) ..." -ForegroundColor Yellow
    @"
SMART_SCRIBE_OCR_MODE=cloud
SMART_SCRIBE_PUBLIC_BASE_URL=
SMART_SCRIBE_TUNNEL=auto
"@ | Set-Content -Path $envFile -Encoding UTF8
}

Write-Host ""
Write-Host "== Setup Complete ==" -ForegroundColor Cyan
Write-Host "Start: double-click start-windows.bat, or run scripts\start-windows.ps1" -ForegroundColor Green
Write-Host "Then open http://localhost:8000 -> Settings page -> fill 3 API keys" -ForegroundColor Green
