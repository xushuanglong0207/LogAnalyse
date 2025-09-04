@echo off
chcp 65001 >nul
echo Starting React App Manually...
echo.

echo Step 1: Kill existing processes...
taskkill /f /im electron.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
timeout /t 3 /nobreak >nul

echo Step 2: Start React dev server manually...
echo Starting on port 3000...
npx --yes create-react-app@latest temp-react-server --template typescript >nul 2>&1
if exist temp-react-server (
    cd temp-react-server
    npm start
) else (
    echo Failed to create temp server, trying direct approach...
    node -e "
    const express = require('express');
    const path = require('path');
    const app = express();
    app.use(express.static(path.join(__dirname, 'src')));
    app.get('/', (req, res) => {
        res.sendFile(path.join(__dirname, 'standalone.html'));
    });
    app.listen(3000, () => {
        console.log('Server running on http://localhost:3000');
    });
    "
)

pause
