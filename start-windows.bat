@echo off
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" goto :setup
if not exist "frontend\dist\index.html" goto :setup
goto :start

:setup
echo [First run] Installing... this may take a few minutes (proxy may be needed).
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\setup-windows.ps1"
if errorlevel 1 (
    echo.
    echo Setup failed. If it's a network issue, set proxy and retry:
    echo    set HTTPS_PROXY=http://127.0.0.1:7897
    pause
    exit /b 1
)

:start
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\start-windows.ps1"
pause