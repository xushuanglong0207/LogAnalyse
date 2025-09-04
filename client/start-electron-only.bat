@echo off
chcp 65001 >nul
echo Starting Electron App (Standalone Mode)...
echo.

echo Step 1: Kill existing processes...
taskkill /f /im electron.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo Step 2: Start Electron with standalone HTML...
electron public/electron.js

pause
