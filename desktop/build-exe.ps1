# Smart Scribe - build portable exe (bypasses electron-builder winCodeSign issue)
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File desktop\build-exe.ps1

$ErrorActionPreference = "Stop"
$DesktopDir = $PSScriptRoot
$ProjectRoot = Split-Path $DesktopDir -Parent

$ElectronDist = Join-Path $DesktopDir "node_modules\electron\dist"
$OutDir = Join-Path $DesktopDir "dist\Smart-Scribe"

if (-not (Test-Path $ElectronDist)) {
    Write-Host "Electron not installed. Run: cd desktop; npm install" -ForegroundColor Red
    exit 1
}

Write-Host "Building Smart Scribe.exe..." -ForegroundColor Cyan

$AppDir = Join-Path $OutDir "resources\app"
$ExePath = Join-Path $OutDir "Smart Scribe.exe"

# If exe already exists, just update the app files (avoids locked-DLL issue)
if (Test-Path $ExePath) {
    Write-Host "  Existing build found, updating app files only..." -ForegroundColor DarkGray
    New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
    Copy-Item (Join-Path $DesktopDir "main.cjs") $AppDir -Force
    Copy-Item (Join-Path $DesktopDir "preload.cjs") $AppDir -Force
    Copy-Item (Join-Path $DesktopDir "loading.html") $AppDir -Force
    Copy-Item (Join-Path $DesktopDir "package.json") $AppDir -Force
    Write-Host ""
    Write-Host "  Update complete!" -ForegroundColor Green
    Write-Host "  Exe: $ExePath" -ForegroundColor Green
    exit 0
}

# Full build (first time)
Copy-Item $ElectronDist $OutDir -Recurse
New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
Copy-Item (Join-Path $DesktopDir "main.cjs") $AppDir -Force
Copy-Item (Join-Path $DesktopDir "preload.cjs") $AppDir -Force
Copy-Item (Join-Path $DesktopDir "loading.html") $AppDir -Force
Copy-Item (Join-Path $DesktopDir "package.json") $AppDir -Force

# Rename exe
$oldExe = Join-Path $OutDir "electron.exe"
Rename-Item $oldExe $ExePath

Write-Host ""
Write-Host "  Build complete!" -ForegroundColor Green
Write-Host "  Exe: $ExePath" -ForegroundColor Green
Write-Host ""
Write-Host "  You can create a desktop shortcut to this exe." -ForegroundColor DarkGray
