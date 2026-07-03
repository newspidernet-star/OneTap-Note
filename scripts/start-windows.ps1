# Smart Scribe — Windows 一键启动
# 入口：start-windows.bat（会调用本脚本）；或手动：powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-windows.ps1

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$pyExe = Join-Path $Root 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $pyExe)) {
    throw '未安装。请先双击 start-windows.bat（首次会自动安装），或运行 scripts\setup-windows.ps1'
}

# 代理（供 yt-dlp / cloudflared 访问外网；不影响 localhost）
$proxy = $env:HTTPS_PROXY
if (-not $proxy) {
    try { if (Get-NetTCPConnection -LocalPort 7897 -State Listen -ErrorAction SilentlyContinue) { $proxy = 'http://127.0.0.1:7897' } } catch {}
}
if ($proxy) { $env:HTTPS_PROXY = $proxy; $env:HTTP_PROXY = $proxy }
$env:NO_PROXY = 'localhost,127.0.0.1,::1'

# 后端从 backend/ 目录启动（.env 与 app 包均在此）
Set-Location (Join-Path $Root 'backend')

Write-Host "启动 Smart Scribe ...  浏览器将打开 http://localhost:8000" -ForegroundColor Cyan
Write-Host "（Ctrl+C 停止）" -ForegroundColor DarkGray
Start-Process 'http://localhost:8000'
& $pyExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
