# One Tap Note - package Windows Setup.exe
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package-windows-setup.ps1

$ErrorActionPreference = "Stop"

$ScriptsDir = $PSScriptRoot
$ProjectRoot = Split-Path $ScriptsDir -Parent
$FrontendDir = Join-Path $ProjectRoot "frontend"
$DesktopDir = Join-Path $ProjectRoot "desktop"
$DistDir = Join-Path $DesktopDir "dist-installer"
$BuilderCacheDir = Join-Path $ProjectRoot ".cache\electron-builder"

Write-Host "== One Tap Note Setup.exe build ==" -ForegroundColor Cyan

$commit = git -C $ProjectRoot rev-parse --short HEAD
Write-Host "Commit: $commit" -ForegroundColor DarkGray

Write-Host "Checking required project files..." -ForegroundColor Cyan
$required = @(
    "backend\app\main.py",
    "backend\requirements-windows.txt",
    "frontend\package.json",
    "scripts\setup-windows.ps1",
    "scripts\start-windows.ps1",
    "desktop\main.cjs",
    "desktop\preload.cjs",
    "desktop\loading.html",
    "desktop\assets\icon.ico",
    "desktop\assets\icon.png"
)

foreach ($item in $required) {
    $path = Join-Path $ProjectRoot $item
    if (-not (Test-Path $path)) {
        throw "Missing required file: $item"
    }
}

Write-Host "Building frontend..." -ForegroundColor Cyan
Push-Location $FrontendDir
npm run build
Pop-Location

$index = Join-Path $FrontendDir "dist\index.html"
if (-not (Test-Path $index)) {
    throw "Frontend build failed: frontend\dist\index.html not found."
}

Write-Host "Checking desktop package dependencies..." -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $DesktopDir "node_modules"))) {
    Push-Location $DesktopDir
    npm install
    Pop-Location
}

if (Test-Path $DistDir) {
    $resolvedDist = (Resolve-Path $DistDir).Path
    $resolvedDesktop = (Resolve-Path $DesktopDir).Path
    if (-not $resolvedDist.StartsWith($resolvedDesktop)) {
        throw "Refusing to remove unexpected installer output path: $resolvedDist"
    }
    Remove-Item -LiteralPath $DistDir -Recurse -Force
}

Write-Host "Building Setup.exe..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $BuilderCacheDir -Force | Out-Null
$env:ELECTRON_BUILDER_CACHE = $BuilderCacheDir
$env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
$builderProxy = $env:HTTPS_PROXY
if (-not $builderProxy) { $builderProxy = $env:HTTP_PROXY }
if (-not $builderProxy) { $builderProxy = "http://127.0.0.1:7897" }
$env:HTTPS_PROXY = $builderProxy
$env:HTTP_PROXY = $builderProxy
$env:https_proxy = $builderProxy
$env:http_proxy = $builderProxy
$env:NO_PROXY = "localhost,127.0.0.1,::1"
$env:no_proxy = $env:NO_PROXY
Write-Host "Builder download proxy: $builderProxy" -ForegroundColor Green
Push-Location $DesktopDir
npm run dist
Pop-Location

$setup = Get-ChildItem $DistDir -Filter "One-Tap-Note-Setup-*.exe" -File | Select-Object -First 1
if (-not $setup) {
    throw "Setup.exe was not created."
}

$hash = Get-FileHash $setup.FullName -Algorithm SHA256

Write-Host ""
Write-Host "Setup.exe created:" -ForegroundColor Green
Write-Host "  $($setup.FullName)" -ForegroundColor Green
Write-Host "SHA256:" -ForegroundColor Green
Write-Host "  $($hash.Hash)" -ForegroundColor Green
