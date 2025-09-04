@echo off
echo 正在启动日志分析工具客户端...
echo.

echo 步骤 1: 检查依赖包...
if not exist node_modules (
    echo 安装依赖包...
    npm install
    if errorlevel 1 (
        echo 依赖包安装失败！
        pause
        exit /b 1
    )
)

echo 步骤 2: 启动 React 开发服务器...
start "React Dev Server" cmd /k "npx react-scripts start"

echo 等待 React 服务器启动...
timeout /t 15 /nobreak > nul

echo 步骤 3: 启动 Electron 应用...
npm run electron

pause 