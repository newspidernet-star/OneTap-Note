# One Tap Note - Windows one-click setup
# Entry: start-windows.bat (calls this on first run); or run manually:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup-windows.ps1

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$LogDir = Join-Path $Root 'logs'
$LogFile = Join-Path $LogDir 'setup-windows.log'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
try { Start-Transcript -Path $LogFile -Force | Out-Null } catch {}

trap {
    Write-Host ""
    Write-Host "Setup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Log saved to: $LogFile" -ForegroundColor Yellow
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
}

Write-Host "== One Tap Note Windows Setup ==" -ForegroundColor Cyan

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
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget not found. Please install/update App Installer from Microsoft Store, then rerun setup."
    }
    Write-Host "Installing $PackageId ..." -ForegroundColor Yellow
    winget install $PackageId --accept-source-agreements --accept-package-agreements --silent --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw "winget install failed for $PackageId (exit code $LASTEXITCODE)" }
    Update-Path
    if (-not (Get-Command $TestCmd -ErrorAction SilentlyContinue)) {
        throw "$PackageId installed but command '$TestCmd' is still unavailable. Restart Windows or install it manually, then rerun setup."
    }
}

# --- 1. System dependencies ---
# Python 3.11: handle separately since `py` may exist but 3.11 not installed
$needPy31 = $true
try { $null = py -3.11 --version 2>$null; if ($?) { $needPy31 = $false } } catch {}
if ($needPy31) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget not found. Please install/update App Installer from Microsoft Store, then rerun setup."
    }
    Write-Host "Installing Python.Python.3.11 ..." -ForegroundColor Yellow
    winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements --silent --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw "winget install failed for Python.Python.3.11 (exit code $LASTEXITCODE)" }
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
    if ($LASTEXITCODE -ne 0) { throw "Failed to create backend virtual environment (exit code $LASTEXITCODE)" }
}
& $pyExe -m pip install --upgrade pip wheel | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip/wheel (exit code $LASTEXITCODE)" }
Write-Host "Installing backend deps (Windows cloud-OCR subset)..." -ForegroundColor Yellow
& $pyExe -m pip install -r (Join-Path $Root 'backend\requirements-windows.txt')
if ($LASTEXITCODE -ne 0) { throw "Failed to install backend dependencies (exit code $LASTEXITCODE)" }
Write-Host "Installing Playwright Chromium ..." -ForegroundColor Yellow
& $pyExe -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "Failed to install Playwright Chromium (exit code $LASTEXITCODE)" }

# --- 3. Frontend build ---
$frontend = Join-Path $Root 'frontend'
$dist = Join-Path $frontend 'dist'
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host "npm install (frontend) ..." -ForegroundColor Yellow
    Push-Location $frontend; npm install; Pop-Location
    if ($LASTEXITCODE -ne 0) { throw "npm install failed for frontend (exit code $LASTEXITCODE)" }
}
Write-Host "Building frontend (npm run build) ..." -ForegroundColor Yellow
Push-Location $frontend; npm run build; Pop-Location
if ($LASTEXITCODE -ne 0) { throw "npm run build failed for frontend (exit code $LASTEXITCODE)" }
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
try { Stop-Transcript | Out-Null } catch {}
