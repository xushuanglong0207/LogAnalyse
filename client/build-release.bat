@echo off
echo ========================================
echo 日志分析工具 v1.0.0 打包脚本
echo 作者: xushuanglong
echo ========================================

echo.
echo 正在检查环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Node.js，请先安装 Node.js
    pause
    exit /b 1
)

npm --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 npm，请先安装 npm
    pause
    exit /b 1
)

echo Node.js 和 npm 环境检查通过

echo.
echo 正在安装依赖...
npm install
if errorlevel 1 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)

echo.
echo 正在构建 React 应用...
npm run build
if errorlevel 1 (
    echo 错误: React 应用构建失败
    pause
    exit /b 1
)

echo.
echo 正在打包 Windows 版本...
npm run dist-win
if errorlevel 1 (
    echo 错误: Windows 版本打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 打包完成！
echo 输出目录: dist/
echo 安装包: 日志分析工具 Setup 1.0.0.exe
echo ========================================
echo.

if exist "dist\日志分析工具 Setup 1.0.0.exe" (
    echo 文件大小:
    dir "dist\日志分析工具 Setup 1.0.0.exe" | find "日志分析工具"
    echo.
    echo 是否打开输出目录？ (Y/N)
    set /p choice=
    if /i "%choice%"=="Y" (
        explorer dist
    )
) else (
    echo 警告: 未找到预期的安装包文件
)

pause
