@echo off
chcp 65001 >nul
echo Starting Log Analyzer Client...
echo.

echo Step 1: Kill existing processes...
taskkill /f /im electron.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
timeout /t 3 /nobreak >nul

echo Step 2: Start React dev server...
start "React Dev Server" cmd /c "npx react-scripts start"

echo Step 3: Wait for React server...
timeout /t 15 /nobreak >nul

echo Step 4: Start Electron...
if exist "node_modules\.bin\electron.cmd" (
    echo Using local Electron...
    "node_modules\.bin\electron.cmd" .
) else (
    echo Using global Electron...
    npx electron .
)

pause
