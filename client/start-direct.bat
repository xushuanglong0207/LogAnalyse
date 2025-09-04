@echo off
chcp 65001 >nul
echo 直接启动日志分析工具客户端...
echo.

echo 步骤 1: 终止所有相关进程...
taskkill /f /im electron.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
timeout /t 3 /nobreak >nul

echo 步骤 2: 直接启动 React 开发服务器...
start "React Dev Server" cmd /c "cd /d %~dp0 && npx react-scripts start"

echo 等待 React 服务器启动...
timeout /t 10 /nobreak >nul

echo 步骤 3: 启动 Electron（使用现有安装）...
if exist "node_modules\.bin\electron.cmd" (
    echo 使用本地 Electron...
    node_modules\.bin\electron.cmd .
) else (
    echo 使用全局 Electron...
    npx electron .
)

pause
