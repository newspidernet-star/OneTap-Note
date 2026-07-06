# Smart Scribe - package Windows release zip
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package-windows-release.ps1

$ErrorActionPreference = "Stop"

$ScriptsDir = $PSScriptRoot
$ProjectRoot = Split-Path $ScriptsDir -Parent
$ReleaseDir = Join-Path $ProjectRoot "release"
$PackageDir = Join-Path $ReleaseDir "Smart-Scribe-Windows"
$ZipPath = Join-Path $ReleaseDir "Smart-Scribe-Windows.zip"

function Copy-Tree($Source, $Destination, $ExcludeDirs, $ExcludeFiles) {
    if (-not (Test-Path $Source)) { return }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null

    $items = Get-ChildItem -LiteralPath $Source -Force
    foreach ($item in $items) {
        if ($item.PSIsContainer) {
            if ($ExcludeDirs -contains $item.Name) { continue }
            Copy-Tree $item.FullName (Join-Path $Destination $item.Name) $ExcludeDirs $ExcludeFiles
        } else {
            $skipFile = $false
            foreach ($pattern in $ExcludeFiles) {
                if ($item.Name -like $pattern) {
                    $skipFile = $true
                    break
                }
            }
            if ($skipFile) { continue }
            Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $Destination $item.Name) -Force
        }
    }
}

Write-Host "Building root desktop exe..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "desktop\build-exe.ps1")

if (-not (Test-Path (Join-Path $ProjectRoot "Smart Scribe.exe"))) {
    throw "Smart Scribe.exe was not created."
}

if (Test-Path $PackageDir) {
    $resolvedPackage = (Resolve-Path $PackageDir).Path
    $resolvedRelease = (Resolve-Path $ReleaseDir).Path
    if (-not $resolvedPackage.StartsWith($resolvedRelease)) {
        throw "Refusing to remove unexpected package path: $resolvedPackage"
    }
    Remove-Item -LiteralPath $PackageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $PackageDir -Force | Out-Null

Write-Host "Copying desktop runtime..." -ForegroundColor Cyan
$runtimeItems = @(
    "Smart Scribe.exe",
    "locales",
    "resources",
    "chrome_100_percent.pak",
    "chrome_200_percent.pak",
    "d3dcompiler_47.dll",
    "ffmpeg.dll",
    "icudtl.dat",
    "libEGL.dll",
    "libGLESv2.dll",
    "LICENSE",
    "LICENSES.chromium.html",
    "resources.pak",
    "snapshot_blob.bin",
    "v8_context_snapshot.bin",
    "version",
    "vk_swiftshader.dll",
    "vk_swiftshader_icd.json",
    "vulkan-1.dll"
)

foreach ($name in $runtimeItems) {
    $source = Join-Path $ProjectRoot $name
    if (Test-Path $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $PackageDir $name) -Recurse -Force
    }
}

Write-Host "Copying project files..." -ForegroundColor Cyan
Copy-Item -LiteralPath (Join-Path $ProjectRoot "start-desktop.bat") -Destination $PackageDir -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "start-windows.bat") -Destination $PackageDir -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "README.md") -Destination $PackageDir -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "PRODUCT.md") -Destination $PackageDir -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "docker-compose.yml") -Destination $PackageDir -Force

Copy-Tree (Join-Path $ProjectRoot "backend") (Join-Path $PackageDir "backend") `
    @(".venv", "__pycache__", "storage", ".pytest_cache") `
    @(".env", "backend.log", "err.log", "*.db", "*.sqlite3")

Copy-Tree (Join-Path $ProjectRoot "frontend") (Join-Path $PackageDir "frontend") `
    @("node_modules", ".vite") `
    @("frontend.log", "frontend-err.log", ".tsbuildinfo")

Copy-Tree (Join-Path $ProjectRoot "scripts") (Join-Path $PackageDir "scripts") @() @()
Copy-Tree (Join-Path $ProjectRoot "docs") (Join-Path $PackageDir "docs") @() @()

if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

Write-Host "Compressing release zip..." -ForegroundColor Cyan
Compress-Archive -Path $PackageDir -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "Release zip created:" -ForegroundColor Green
Write-Host "  $ZipPath" -ForegroundColor Green
