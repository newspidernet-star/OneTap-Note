@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" goto :setup
if not exist "frontend\dist\index.html" goto :setup
goto :start

:setup
echo [首次运行] 正在安装，需要几分钟（可能需要代理）...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\setup-windows.ps1"
if errorlevel 1 (
    echo.
    echo 安装失败，请检查上方报错。常见：网络问题 - 设代理后重跑：
    echo    set HTTPS_PROXY=http://127.0.0.1:7897
    pause
    exit /b 1
)

:start
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\start-windows.ps1"
pause
