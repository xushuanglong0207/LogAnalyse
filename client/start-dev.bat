@echo off
chcp 65001 >nul
echo 正在启动日志分析工具客户端...
echo.

echo 步骤 1: 清理可能的锁定文件...
taskkill /f /im electron.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo 步骤 2: 检查依赖包...
if not exist node_modules (
    echo 安装依赖包...
    npm install
    if errorlevel 1 (
        echo 依赖包安装失败！
        pause
        exit /b 1
    )
)

echo 步骤 3: 检查 react-scripts...
npm list react-scripts >nul 2>&1
if errorlevel 1 (
    echo 修复 react-scripts 依赖...
    npm install react-scripts@5.0.1
)

echo 步骤 4: 启动开发环境...
npm run electron-dev

pause