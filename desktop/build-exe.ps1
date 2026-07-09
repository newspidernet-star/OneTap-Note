# One Tap Note - build portable exe (bypasses electron-builder winCodeSign issue)
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File desktop\build-exe.ps1

$ErrorActionPreference = "Stop"
$DesktopDir = $PSScriptRoot
$ProjectRoot = Split-Path $DesktopDir -Parent

$ElectronDist = Join-Path $DesktopDir "node_modules\electron\dist"
$OutDir = $ProjectRoot

if (-not (Test-Path $ElectronDist)) {
    Write-Host "Electron not installed. Run: cd desktop; npm install" -ForegroundColor Red
    exit 1
}

Write-Host "Building One Tap Note.exe..." -ForegroundColor Cyan

$AppDir = Join-Path $OutDir "resources\app"
$ExePath = Join-Path $OutDir "One Tap Note.exe"
$IconPath = Join-Path $DesktopDir "assets\icon.ico"
$AppBuilder = Join-Path $DesktopDir "node_modules\app-builder-bin\win\x64\app-builder.exe"

function Update-ExeResources {
    param([string]$TargetExePath)

    if (-not (Test-Path $IconPath)) {
        Write-Host "  Icon file not found: $IconPath" -ForegroundColor Yellow
        return
    }

    $cachedRcedit = Get-ChildItem -LiteralPath "$env:LOCALAPPDATA\electron-builder\Cache\winCodeSign" -Recurse -Filter "rcedit-x64.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
    if ($cachedRcedit) {
        & $cachedRcedit (Resolve-Path $TargetExePath).Path `
            --set-version-string FileDescription "One Tap Note" `
            --set-version-string ProductName "One Tap Note" `
            --set-version-string InternalName "One Tap Note" `
            --set-version-string OriginalFilename "One Tap Note.exe" `
            --set-icon (Resolve-Path $IconPath).Path
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to update exe resources."
        }
        Write-Host "  Exe icon updated." -ForegroundColor Green
        return
    }

    if (-not (Test-Path $AppBuilder)) {
        Write-Host "  app-builder not found; exe file icon will stay unchanged." -ForegroundColor Yellow
        return
    }

    $builderCache = Join-Path $ProjectRoot ".cache\electron-builder"
    New-Item -ItemType Directory -Path $builderCache -Force | Out-Null
    $env:ELECTRON_BUILDER_CACHE = $builderCache

    $nodeScriptPath = Join-Path ([System.IO.Path]::GetTempPath()) "one-tap-note-rcedit.cjs"
    $nodeScript = @'
const { spawnSync } = require("child_process");

const [appBuilder, exePath, iconPath] = process.argv.slice(2);
const args = [
  exePath,
  "--set-version-string", "FileDescription", "One Tap Note",
  "--set-version-string", "ProductName", "One Tap Note",
  "--set-version-string", "InternalName", "One Tap Note",
  "--set-version-string", "OriginalFilename", "One Tap Note.exe",
  "--set-icon", iconPath,
];

const result = spawnSync(appBuilder, ["rcedit", "--args", JSON.stringify(args)], {
  stdio: "inherit",
});
process.exit(result.status ?? 1);
'@

    Set-Content -LiteralPath $nodeScriptPath -Value $nodeScript -Encoding UTF8
    & node $nodeScriptPath $AppBuilder (Resolve-Path $TargetExePath).Path (Resolve-Path $IconPath).Path
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to update exe resources."
    }
    Write-Host "  Exe icon updated." -ForegroundColor Green
}

# If exe already exists, just update the app files (avoids locked-DLL issue)
if (Test-Path $ExePath) {
    Write-Host "  Existing build found, updating app files only..." -ForegroundColor DarkGray
    New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
    Copy-Item (Join-Path $DesktopDir "main.cjs") $AppDir -Force
    Copy-Item (Join-Path $DesktopDir "preload.cjs") $AppDir -Force
    Copy-Item (Join-Path $DesktopDir "loading.html") $AppDir -Force
    Copy-Item (Join-Path $DesktopDir "package.json") $AppDir -Force
    Copy-Item (Join-Path $DesktopDir "assets") $AppDir -Recurse -Force
    Update-ExeResources $ExePath
    Write-Host ""
    Write-Host "  Update complete!" -ForegroundColor Green
    Write-Host "  Exe: $ExePath" -ForegroundColor Green
    exit 0
}

# Full build (first time)
# Copy electron binary files, but skip LICENSE (keep our MIT one)
$electronFiles = Get-ChildItem $ElectronDist -Force
foreach ($file in $electronFiles) {
    if ($file.Name -eq "LICENSE") { continue }
    Copy-Item $file.FullName $OutDir -Recurse -Force
}
New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
Copy-Item (Join-Path $DesktopDir "main.cjs") $AppDir -Force
Copy-Item (Join-Path $DesktopDir "preload.cjs") $AppDir -Force
Copy-Item (Join-Path $DesktopDir "loading.html") $AppDir -Force
Copy-Item (Join-Path $DesktopDir "package.json") $AppDir -Force
Copy-Item (Join-Path $DesktopDir "assets") $AppDir -Recurse -Force

# Rename exe
$oldExe = Join-Path $OutDir "electron.exe"
Rename-Item $oldExe $ExePath
Update-ExeResources $ExePath

Write-Host ""
Write-Host "  Build complete!" -ForegroundColor Green
Write-Host "  Exe: $ExePath" -ForegroundColor Green
Write-Host ""
Write-Host "  Release zip can now expose this exe at the archive root." -ForegroundColor DarkGray
