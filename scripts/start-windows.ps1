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

# 启动前清理：如果端口 8000 被占用（上次没关干净），自动杀掉旧进程
try {
    $oldConns = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($oldConns) {
        Write-Host "Port 8000 in use, stopping previous instance..." -ForegroundColor Yellow
        $oldConns | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
            try { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } catch {}
        }
        Start-Sleep -Seconds 2
    }
} catch {}

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "    Smart Scribe  -  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Browser will open automatically." -ForegroundColor Green
Write-Host "  Processing logs will appear below." -ForegroundColor Green
Write-Host ""
Write-Host "  (Close this window or Ctrl+C to stop server + browser)" -ForegroundColor DarkGray
Write-Host ""

# 用 Edge/Chrome 的 --app 模式打开独立窗口（关掉只关这个窗口，不影响用户其他标签页）
$url = "http://localhost:8000"
$browserProc = $null
$edgePath = @(
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

$chromePath = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($edgePath) {
    $browserProc = Start-Process $edgePath "--app=$url" -PassThru
} elseif ($chromePath) {
    $browserProc = Start-Process $chromePath "--app=$url --new-window" -PassThru
} else {
    $browserProc = Start-Process $url -PassThru
}

# 关闭 cmd 窗口 / Ctrl+C / 脚本退出时，关掉浏览器窗口
$procId = if ($browserProc) { $browserProc.Id } else { 0 }
Register-EngineEvent PowerShell.Exiting -Action {
    if ($procId -gt 0) { try { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue } catch {} }
} | Out-Null

try {
    & $pyExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
    if ($procId -gt 0) { try { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue } catch {} }
}
