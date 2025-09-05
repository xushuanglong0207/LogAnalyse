@echo off
chcp 65001 >nul 2>&1
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

REM 直接启动Electron（使用full-app.html）
echo 正在启动Electron...
npx electron .

echo.
echo 应用已启动完成！
pause