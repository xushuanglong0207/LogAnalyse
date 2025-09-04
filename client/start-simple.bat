@echo off
chcp 65001 >nul
echo 启动日志分析工具客户端（简化版）...
echo.

echo 步骤 1: 终止可能的冲突进程...
taskkill /f /im electron.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo 步骤 2: 检查并安装缺失的依赖...
if not exist "node_modules\react-scripts" (
    echo 安装 react-scripts...
    npm install --no-package-lock react-scripts@5.0.1
)

if not exist "node_modules\concurrently" (
    echo 安装 concurrently...
    npm install --no-package-lock concurrently@8.2.2
)

if not exist "node_modules\wait-on" (
    echo 安装 wait-on...
    npm install --no-package-lock wait-on@7.2.0
)

echo 步骤 3: 启动应用...
echo 正在启动 React 开发服务器和 Electron...
npm run electron-dev

pause
