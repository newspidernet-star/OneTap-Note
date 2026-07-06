@echo off
title Smart Scribe Desktop
cd /d "%~dp0"
if exist "Smart Scribe.exe" (
    start "" "Smart Scribe.exe"
    exit
)
if exist "desktop\dist\Smart-Scribe\Smart Scribe.exe" (
    start "" "desktop\dist\Smart-Scribe\Smart Scribe.exe"
    exit
)
cd desktop
if not exist node_modules (
    echo First run: installing Electron dependencies...
    set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
    call npm install
)
echo.
echo   Starting Smart Scribe desktop window (dev mode)...
echo   (Close this window to stop)
echo.
npx electron .
