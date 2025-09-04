@echo off
chcp 65001 >nul
echo 启动日志分析工具...
echo.

echo 正在终止旧进程...
taskkill /f /im electron.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo 启动日志分析工具客户端...
electron public/electron.js

pause
