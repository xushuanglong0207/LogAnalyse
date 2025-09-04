@echo off
chcp 65001 >nul
echo 修复客户端依赖问题...
echo.

echo 步骤 1: 终止所有相关进程...
taskkill /f /im electron.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
taskkill /f /im npm.exe >nul 2>&1
timeout /t 3 /nobreak >nul

echo 步骤 2: 清理 npm 缓存...
npm cache clean --force

echo 步骤 3: 删除 package-lock.json...
if exist package-lock.json del package-lock.json

echo 步骤 4: 尝试删除 node_modules...
if exist node_modules (
    echo 正在删除 node_modules...
    rmdir /s /q node_modules >nul 2>&1
    if exist node_modules (
        echo 某些文件被锁定，请手动重启计算机后再运行此脚本
        echo 或者等待几分钟后重试
        pause
        exit /b 1
    )
)

echo 步骤 5: 重新安装依赖...
npm install

echo 步骤 6: 验证安装...
npm list react-scripts

echo.
echo 修复完成！现在可以运行 start-dev.bat 启动应用
pause
