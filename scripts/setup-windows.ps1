# Smart Scribe — Windows 一键安装脚本
# 入口：仓库根目录的 start-windows.bat（首次运行会调用本脚本）
# 手动：powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup-windows.ps1

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Write-Host "== Smart Scribe Windows 安装 ==" -ForegroundColor Cyan

# --- 代理自动探测（兼容 clash 默认端口 7897）---
$proxy = $env:HTTPS_PROXY
if (-not $proxy) {
    try { if (Get-NetTCPConnection -LocalPort 7897 -State Listen -ErrorAction SilentlyContinue) { $proxy = 'http://127.0.0.1:7897' } } catch {}
}
if ($proxy) {
    $env:HTTPS_PROXY = $proxy; $env:HTTP_PROXY = $proxy; $env:NO_PROXY = 'localhost,127.0.0.1,::1'
    Write-Host "检测到代理：$proxy" -ForegroundColor Green
} else {
    Write-Host "未检测到代理。若下载缓慢/失败，先设 `$env:HTTPS_PROXY='http://127.0.0.1:7897' 再重跑" -ForegroundColor Yellow
}

function Update-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
}
function Ensure-Winget($PackageId, $TestCmd) {
    if (Get-Command $TestCmd -ErrorAction SilentlyContinue) { return }
    Write-Host "安装 $PackageId ..." -ForegroundColor Yellow
    winget install $PackageId --accept-source-agreements --accept-package-agreements --silent --disable-interactivity
    Update-Path
}

# --- 1. 系统依赖 ---
# Python 3.11：单独处理，因为 `py` 可能存在但 3.11 未装
$needPy31 = $true
try { $null = py -3.11 --version 2>$null; if ($?) { $needPy31 = $false } } catch {}
if ($needPy31) {
    Write-Host "安装 Python.Python.3.11 ..." -ForegroundColor Yellow
    winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements --silent --disable-interactivity
    Update-Path
}
try { Write-Host "Python: $(py -3.11 --version)" -ForegroundColor Green } catch { throw 'Python 3.11 安装失败，请手动 winget install Python.Python.3.11' }

Ensure-Winget 'OpenJS.NodeJS.LTS' 'node'
Ensure-Winget 'Gyan.FFmpeg' 'ffmpeg'
Ensure-Winget 'Cloudflare.cloudflared' 'cloudflared'

# --- 2. 后端 venv ---
$venv = Join-Path $Root 'backend\.venv'
$pyExe = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $pyExe)) {
    Write-Host "创建虚拟环境 backend\.venv ..." -ForegroundColor Yellow
    py -3.11 -m venv $venv
}
& $pyExe -m pip install --upgrade pip wheel | Out-Null
Write-Host "安装后端依赖（Windows 云端 OCR 子集）..." -ForegroundColor Yellow
& $pyExe -m pip install -r (Join-Path $Root 'backend\requirements-windows.txt')
Write-Host "安装 Playwright Chromium ..." -ForegroundColor Yellow
& $pyExe -m playwright install chromium

# --- 3. 前端构建 ---
$frontend = Join-Path $Root 'frontend'
$dist = Join-Path $frontend 'dist'
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host "npm install (前端) ..." -ForegroundColor Yellow
    Push-Location $frontend; npm install; Pop-Location
}
Write-Host "构建前端 (npm run build) ..." -ForegroundColor Yellow
Push-Location $frontend; npm run build; Pop-Location
if (-not (Test-Path (Join-Path $dist 'index.html'))) { throw '前端构建失败，未见 frontend\dist\index.html' }

# --- 4. .env ---
$envFile = Join-Path $Root 'backend\.env'
if (-not (Test-Path $envFile)) {
    Write-Host "生成 backend\.env (cloud OCR + auto tunnel) ..." -ForegroundColor Yellow
    @"
SMART_SCRIBE_OCR_MODE=cloud
SMART_SCRIBE_PUBLIC_BASE_URL=
SMART_SCRIBE_TUNNEL=auto
"@ | Set-Content -Path $envFile -Encoding UTF8
}

Write-Host ""
Write-Host "== 安装完成 ==" -ForegroundColor Cyan
Write-Host "启动：双击 start-windows.bat，或运行 scripts\start-windows.ps1" -ForegroundColor Green
Write-Host "然后浏览器打开 http://localhost:8000 -> 设置页填 3 个 API Key" -ForegroundColor Green
