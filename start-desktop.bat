@echo off
title One Tap Note Desktop
cd /d "%~dp0"

REM Priority 1: use root exe if it exists
if exist "One Tap Note.exe" (
    start "" "One Tap Note.exe"
    exit
)

REM Priority 2: use desktop/dist exe if it exists
if exist "desktop\dist\One-Tap-Note\One Tap Note.exe" (
    start "" "desktop\dist\One-Tap-Note\One Tap Note.exe"
    exit
)

REM Priority 3: no exe found, build one automatically
echo One Tap Note.exe not found, building it now (first time only)...
echo.

REM Ensure Electron is installed
cd desktop
if not exist node_modules (
    echo Installing Electron dependencies...
    set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
    call npm install
    if errorlevel 1 (
        echo.
        echo Failed to install Electron dependencies.
        echo Please check your network or proxy settings.
        pause
        exit /b 1
    )
)
cd ..

REM Build the exe
powershell -NoProfile -ExecutionPolicy Bypass -File desktop\build-exe.ps1
if errorlevel 1 (
    echo.
    echo Failed to build One Tap Note.exe.
    pause
    exit /b 1
)

REM Launch the freshly built exe
echo.
echo Starting One Tap Note...
start "" "One Tap Note.exe"
