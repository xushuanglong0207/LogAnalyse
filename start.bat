@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

rem 日志分析平台 - Windows启动脚本
echo 🚀 日志分析平台启动器 (Windows)
echo ============================

rem 获取脚本所在目录，确保使用相对路径
set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

echo 📁 项目根目录: %PROJECT_ROOT%

rem 切换到项目根目录
cd /d "%PROJECT_ROOT%"

rem 设置颜色代码
set "GREEN=[32m"
set "RED=[31m"
set "YELLOW=[33m"
set "BLUE=[34m"
set "RESET=[0m"

rem 主菜单函数
:show_menu
echo.
echo 请选择操作:
echo 1) 🚀 启动平台 (推荐)
echo 2) 🛑 停止所有服务
echo 3) 🔧 仅安装依赖
echo 4) 📊 检查服务状态
echo 5) 🆘 帮助信息
echo 6) 🔧 重置环境
echo 0) 退出
echo.
set /p "choice=请输入选择 [1]: "
if "%choice%"=="" set choice=1
goto handle_choice

:handle_choice
if "%choice%"=="1" goto start_platform
if "%choice%"=="2" goto stop_services
if "%choice%"=="3" goto install_deps_only
if "%choice%"=="4" goto check_status
if "%choice%"=="5" goto show_help
if "%choice%"=="6" goto reset_environment
if "%choice%"=="0" goto exit_script
echo ❌ 无效选择，请重新输入
goto show_menu

:start_platform
echo 🚀 开始启动平台...
call :install_system_deps
call :setup_python_env
call :install_backend_deps
call :install_frontend_deps
call :start_backend
call :start_frontend
call :show_info
goto keep_running

:install_system_deps
echo 🔍 检查系统依赖...

rem 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

rem 检查Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到Node.js，请先安装Node.js 16+
    pause
    exit /b 1
)

echo ✅ 系统依赖检查完成
exit /b 0

:setup_python_env
echo 🐍 设置Python环境...

rem 删除旧的虚拟环境（如果存在且有问题）
if exist venv (
    if not exist venv\Scripts\activate.bat (
        echo 删除损坏的虚拟环境...
        rmdir /s /q venv
    )
)

rem 创建虚拟环境
if not exist venv (
    echo 创建Python虚拟环境...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo ❌ 错误: 创建虚拟环境失败
        pause
        exit /b 1
    )
)

rem 检查虚拟环境是否正确创建
if not exist venv\Scripts\activate.bat (
    echo ❌ 错误: 虚拟环境创建不完整，请删除venv目录后重试
    pause
    exit /b 1
)

rem 激活虚拟环境
call venv\Scripts\activate.bat
if !errorlevel! neq 0 (
    echo ❌ 错误: 激活虚拟环境失败
    pause
    exit /b 1
)

rem 升级pip
echo 升级pip...
python -m pip install --upgrade pip

echo ✅ Python环境设置完成
exit /b 0

:install_backend_deps
echo 📦 安装后端依赖...

rem 激活虚拟环境
call venv\Scripts\activate.bat

rem 检查backend目录是否存在
if not exist backend (
    echo ❌ 错误: backend目录不存在
    pause
    exit /b 1
)

cd backend

rem 安装依赖
echo 安装 fastapi uvicorn python-multipart...
pip install fastapi uvicorn python-multipart
if !errorlevel! neq 0 (
    cd "%PROJECT_ROOT%"
    echo ❌ 错误: 后端依赖安装失败
    pause
    exit /b 1
)

cd "%PROJECT_ROOT%"
echo ✅ 后端依赖安装完成
exit /b 0

:install_frontend_deps
echo 🎨 安装客户端依赖...

rem 检查client目录是否存在
if not exist client (
    echo ❌ 错误: client目录不存在
    pause
    exit /b 1
)

cd client

rem 检查是否需要安装依赖
if not exist node_modules (
    echo 安装Node.js依赖...
    npm install --legacy-peer-deps
    if !errorlevel! neq 0 (
        cd "%PROJECT_ROOT%"
        echo ❌ 错误: 客户端依赖安装失败
        pause
        exit /b 1
    )
)

cd "%PROJECT_ROOT%"
echo ✅ 客户端依赖安装完成
exit /b 0

:start_backend
echo 🚀 启动后端服务...

rem 激活虚拟环境
call venv\Scripts\activate.bat

rem 检查backend目录是否存在
if not exist backend (
    echo ❌ 错误: backend目录不存在
    pause
    exit /b 1
)

cd backend

rem 启动FastAPI服务
echo 启动FastAPI服务在端口8001...
start /b python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

cd "%PROJECT_ROOT%"

rem 等待后端启动
echo 等待后端服务启动...
for /l %%i in (1,1,30) do (
    timeout /t 1 /nobreak >nul
    curl -s http://localhost:8001/health >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✅ 后端服务启动成功
        goto backend_started
    )
    echo|set /p="."
)

echo ❌ 错误: 后端服务启动超时
pause
exit /b 1

:backend_started
exit /b 0

:start_frontend
echo 🎨 启动客户端应用...

rem 检查client目录是否存在
if not exist client (
    echo ❌ 错误: client目录不存在
    pause
    exit /b 1
)

cd client

rem 启动Electron应用
echo 启动Electron客户端应用...
start /b npx electron .

cd "%PROJECT_ROOT%"

rem 等待前端启动
echo 等待前端服务启动...
for /l %%i in (1,1,30) do (
    timeout /t 1 /nobreak >nul
    curl -s http://localhost:3000 >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✅ 前端服务启动成功
        goto frontend_started
    )
    echo|set /p="."
)

echo ❌ 错误: 前端服务启动超时
pause
exit /b 1

:frontend_started
exit /b 0

:show_info
echo.
echo 🎉 日志分析平台启动完成！
echo =========================
echo.
echo 📱 前端访问:
echo    http://localhost:3000
echo.
echo 🔗 API文档:
echo    http://localhost:8001/docs
echo.
echo ⏹️  停止: 按 Ctrl+C 或关闭窗口
echo =========================
exit /b 0

:stop_services
echo 🛑 停止所有服务...

rem 停止端口占用的进程
for %%p in (3000 8001) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :%%p') do (
        taskkill /f /pid %%a >nul 2>&1
    )
    echo ✅ 端口 %%p 已释放
)

echo ✅ 所有服务已停止
goto show_menu

:check_status
echo 📊 检查服务状态...
echo.

rem 检查后端
curl -s http://localhost:8001/health >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ 后端服务: 运行正常 (http://localhost:8001)
) else (
    echo ❌ 后端服务: 未运行
)

rem 检查前端
curl -s http://localhost:3000 >nul 2>&1
if !errorlevel! equ 0 (
    echo ✅ 前端服务: 运行正常 (http://localhost:3000)
) else (
    echo ❌ 前端服务: 未运行
)

echo.
echo 📋 端口占用情况:
for %%p in (3000 8001) do (
    netstat -an | findstr :%%p >nul
    if !errorlevel! equ 0 (
        echo    端口 %%p: 占用中
    ) else (
        echo    端口 %%p: 空闲
    )
)

echo.
echo 🐍 Python环境:
if exist venv\Scripts\activate.bat (
    echo    虚拟环境: ✅ 正常
) else (
    echo    虚拟环境: ❌ 需要重新创建
)

pause
goto show_menu

:reset_environment
echo 🔧 重置开发环境...

rem 停止所有服务
call :stop_services

rem 删除虚拟环境
if exist venv (
    echo 删除Python虚拟环境...
    rmdir /s /q venv
)

rem 删除前端node_modules
if exist frontend\node_modules (
    echo 删除前端依赖...
    rmdir /s /q frontend\node_modules
    if exist frontend\package-lock.json del frontend\package-lock.json
)

echo ✅ 环境重置完成！现在可以重新安装依赖
pause
goto show_menu

:install_deps_only
call :install_system_deps
call :setup_python_env
call :install_backend_deps
call :install_frontend_deps
echo ✅ 依赖安装完成！现在可以选择'启动平台'
pause
goto show_menu

:show_help
echo 🆘 日志分析平台帮助 (Windows版)
echo ===============================
echo.
echo 快速启动:
echo   start.bat         # 显示菜单
echo   start.bat 1       # 直接启动
echo   start.bat 2       # 停止服务
echo.
echo 故障排除:
echo   1. 端口被占用 → 选择'停止所有服务'
echo   2. 依赖问题 → 选择'仅安装依赖'
echo   3. 环境问题 → 选择'重置环境'
echo   4. Python环境 → 自动创建虚拟环境
echo.
echo 访问地址:
echo   前端: http://localhost:3000
echo   API:  http://localhost:8001/docs
echo.
echo 环境要求:
echo   - Python 3.8+
echo   - Node.js 16+
echo   - 2GB+ 可用内存
echo   - Windows 10+
pause
goto show_menu

:keep_running
echo.
echo 服务正在运行中... 按任意键查看菜单
pause
goto show_menu

:exit_script
echo 👋 再见！
exit /b 0