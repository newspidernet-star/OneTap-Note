# Smart Scribe - build portable exe (bypasses electron-builder winCodeSign issue)
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File desktop\build-exe.ps1

$ErrorActionPreference = "Stop"
$DesktopDir = Split-Path $PSScriptRoot -Parent
$ProjectRoot = Split-Path $DesktopDir -Parent

$ElectronDist = Join-Path $DesktopDir "node_modules\electron\dist"
$OutDir = Join-Path $DesktopDir "dist\Smart-Scribe"

if (-not (Test-Path $ElectronDist)) {
    Write-Host "Electron not installed. Run: cd desktop; npm install" -ForegroundColor Red
    exit 1
}

Write-Host "Building Smart Scribe.exe..." -ForegroundColor Cyan

# Clean old build
if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }

# Copy electron binary
Copy-Item $ElectronDist $OutDir -Recurse

# Create app directory with our code
$AppDir = Join-Path $OutDir "resources\app"
New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
Copy-Item (Join-Path $DesktopDir "main.cjs") $AppDir
Copy-Item (Join-Path $DesktopDir "preload.cjs") $AppDir
Copy-Item (Join-Path $DesktopDir "package.json") $AppDir

# Rename exe
$oldExe = Join-Path $OutDir "electron.exe"
$newExe = Join-Path $OutDir "Smart Scribe.exe"
Rename-Item $oldExe $newExe

Write-Host ""
Write-Host "  Build complete!" -ForegroundColor Green
Write-Host "  Exe: $newExe" -ForegroundColor Green
Write-Host ""
Write-Host "  You can create a desktop shortcut to this exe." -ForegroundColor DarkGray