@echo off
echo 正在启动日志分析工具客户端...
echo.

REM 检查是否安装了Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Node.js，请先安装Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

REM 检查是否安装了依赖
if not exist "node_modules" (
    echo 正在安装依赖...
    npm install
    if errorlevel 1 (
        echo 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
)

REM 启动应用
echo 正在启动应用...
start "React Dev Server" cmd /k "npm start"

REM 等待React服务器启动
timeout /t 5 /nobreak >nul

REM 启动Electron
echo 正在启动Electron...
npm run electron

pause 