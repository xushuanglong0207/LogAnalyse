#!/bin/bash

# 日志分析平台 - 统一启动脚本
echo "🚀 日志分析平台启动器"
echo "===================="

# 获取脚本所在目录，确保使用相对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "📁 项目根目录: $PROJECT_ROOT"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    SUDO_CMD=""
else
    SUDO_CMD="sudo"
fi

# 错误处理函数
handle_error() {
    echo "❌ 错误: $1"
    echo "💡 请查看错误信息并重试"
    exit 1
}

# 成功信息函数
success_msg() {
    echo "✅ $1"
}

# 检查并安装系统依赖
install_system_deps() {
    echo "🔍 检查系统依赖..."

    # 首先修复系统包依赖问题
    echo "🔧 修复系统包依赖..."
    $SUDO_CMD apt --fix-broken install -y || true
    $SUDO_CMD apt update || true

    # 检查Python3
    if ! command -v python3 &> /dev/null; then
        echo "📦 安装Python3..."
        $SUDO_CMD apt install -y python3 python3-pip python3-venv python3-full
    else
        # 确保安装了venv模块
        echo "📦 确保Python虚拟环境支持..."
        $SUDO_CMD apt install -y python3-venv python3-full || true
    fi

    # 检查Node.js
    if ! command -v node &> /dev/null; then
        echo "📦 安装Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | $SUDO_CMD -E bash -
        $SUDO_CMD apt-get install -y nodejs
    fi

    success_msg "系统依赖检查完成"
}

# 设置Python虚拟环境
setup_python_env() {
    echo "🐍 设置Python环境..."
    
    # 删除旧的虚拟环境（如果存在且有问题）
    if [ -d "venv" ] && [ ! -f "venv/bin/activate" ]; then
        echo "删除损坏的虚拟环境..."
        rm -rf venv
    fi
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        echo "创建Python虚拟环境..."
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            handle_error "创建虚拟环境失败，请检查Python3-venv是否安装"
        fi
    fi
    
    # 检查虚拟环境是否正确创建
    if [ ! -f "venv/bin/activate" ]; then
        handle_error "虚拟环境创建不完整，请删除venv目录后重试"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        handle_error "激活虚拟环境失败"
    fi
    
    # 升级pip（在虚拟环境中）
    echo "升级pip..."
    pip install --upgrade pip || echo "⚠️  pip升级失败，继续安装依赖..."

    # 验证虚拟环境
    echo "验证虚拟环境..."
    echo "Python路径: $(which python)"
    echo "Pip路径: $(which pip)"
    echo "虚拟环境: $VIRTUAL_ENV"
    
    success_msg "Python环境设置完成"
}

# 安装后端依赖
install_backend_deps() {
    echo "📦 安装后端依赖..."
    
    # 确保在虚拟环境中
    if [ -z "$VIRTUAL_ENV" ]; then
        source venv/bin/activate
    fi

    # 检查backend目录是否存在
    if [ ! -d "backend" ]; then
        handle_error "backend目录不存在"
    fi

    cd backend
    
    # 在虚拟环境中安装依赖
    echo "安装 fastapi uvicorn python-multipart..."
    pip install fastapi uvicorn python-multipart python-dotenv
    if [ $? -ne 0 ]; then
        echo "⚠️  尝试单独安装依赖..."
        pip install fastapi || echo "fastapi安装失败"
        pip install uvicorn || echo "uvicorn安装失败"
        pip install python-multipart || echo "python-multipart安装失败"
        pip install python-dotenv || echo "python-dotenv安装失败"

        # 检查关键依赖是否安装成功
        python -c "import fastapi, uvicorn" 2>/dev/null
        if [ $? -ne 0 ]; then
            cd "$PROJECT_ROOT"
            handle_error "关键后端依赖安装失败"
        fi
        echo "✅ 基础依赖安装完成（部分可选依赖可能失败）"
    fi

    cd "$PROJECT_ROOT"
    success_msg "后端依赖安装完成"
}

# 安装前端依赖
install_frontend_deps() {
    echo "🎨 安装前端依赖..."

    # 安装Web前端依赖 (Next.js)
    if [ -d "frontend" ]; then
        echo "安装Web前端依赖..."
        cd frontend

        if [ ! -d "node_modules" ]; then
            echo "设置npm镜像源..."
            npm config set registry https://registry.npmmirror.com

            echo "安装Next.js依赖..."
            npm install --legacy-peer-deps
            if [ $? -ne 0 ]; then
                echo "⚠️  尝试清理缓存后重新安装..."
                npm cache clean --force
                npm install --legacy-peer-deps
                if [ $? -ne 0 ]; then
                    cd "$PROJECT_ROOT"
                    handle_error "Web前端依赖安装失败"
                fi
            fi
        fi
        cd "$PROJECT_ROOT"
    fi

    # 安装客户端依赖 (Electron)
    if [ -d "client" ]; then
        echo "安装客户端依赖..."
        cd client

        if [ ! -d "node_modules" ]; then
            echo "设置npm镜像源..."
            npm config set registry https://registry.npmmirror.com

            echo "设置Electron镜像源..."
            export ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
            export ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/

            echo "安装Electron依赖..."
            npm install --legacy-peer-deps
            if [ $? -ne 0 ]; then
                echo "⚠️  尝试清理缓存后重新安装..."
                npm cache clean --force
                npm install --legacy-peer-deps
                if [ $? -ne 0 ]; then
                    cd "$PROJECT_ROOT"
                    handle_error "客户端依赖安装失败"
                fi
            fi
        fi
        cd "$PROJECT_ROOT"
    fi

    success_msg "前端依赖安装完成"
}

# 启动后端服务
start_backend() {
    echo "🚀 启动后端服务..."
    
    # 激活虚拟环境
    source venv/bin/activate

    # 检查backend目录是否存在
    if [ ! -d "backend" ]; then
        handle_error "backend目录不存在"
    fi

    cd backend

    # 启动FastAPI服务
    echo "启动FastAPI服务在端口8001..."
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
    BACKEND_PID=$!

    cd "$PROJECT_ROOT"
    
    # 等待后端启动
    echo "等待后端服务启动..."
    for i in {1..30}; do
        # 尝试多个健康检查端点
        if curl -s http://localhost:8001/ > /dev/null 2>&1 || \
           curl -s http://localhost:8001/health > /dev/null 2>&1 || \
           curl -s http://localhost:8001/docs > /dev/null 2>&1; then
            success_msg "后端服务启动成功 (PID: $BACKEND_PID)"
            echo "🔗 后端API地址: http://localhost:8001"
            echo "📚 API文档: http://localhost:8001/docs"
            return 0
        fi
        sleep 1
        echo -n "."
    done

    echo ""
    echo "⚠️  后端服务启动超时，但进程可能仍在启动中..."
    echo "🔍 请检查进程状态: ps aux | grep uvicorn"
    echo "📋 请检查日志输出以获取更多信息"
}

# 启动Web前端服务
start_web_frontend() {
    echo "🌐 启动Web前端服务..."

    # 检查frontend目录是否存在
    if [ ! -d "frontend" ]; then
        echo "⚠️  frontend目录不存在，跳过Web前端启动"
        return 0
    fi

    cd frontend

    # 启动Next.js开发服务器
    echo "启动Next.js开发服务器在端口3000..."
    npm run dev &
    WEB_FRONTEND_PID=$!

    cd "$PROJECT_ROOT"

    # 等待Web前端启动
    echo "等待Web前端服务启动..."
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            success_msg "Web前端服务启动成功 (PID: $WEB_FRONTEND_PID)"
            return 0
        fi
        sleep 1
        echo -n "."
    done

    echo ""
    echo "⚠️  Web前端服务启动超时，但进程可能仍在启动中..."
}

# 启动客户端应用
start_client() {
    echo "🎨 启动客户端应用..."

    # 检查是否为root用户
    if [ "$EUID" -eq 0 ]; then
        echo "⚠️  检测到root用户，Electron无法以root权限运行"
        echo "🔧 在Linux服务器环境下，建议只启动Web前端"
        echo "📱 Electron客户端请在桌面环境下单独启动"
        echo ""
        echo "💡 客户端启动方法："
        echo "   1. 在有桌面环境的机器上运行"
        echo "   2. 或使用非root用户运行"
        echo ""
        echo "⏭️  跳过Electron客户端启动..."
        return 0
    fi

    # 检查client目录是否存在
    if [ ! -d "client" ]; then
        echo "⚠️  client目录不存在，跳过Electron客户端启动"
        return 0
    fi

    cd client

    # 启动Electron应用
    echo "启动Electron客户端应用..."
    npx electron . &
    CLIENT_PID=$!

    cd "$PROJECT_ROOT"

    # 等待应用启动
    echo "等待客户端应用启动..."
    sleep 3

    if ps -p $CLIENT_PID > /dev/null 2>&1; then
        success_msg "Electron客户端启动成功 (PID: $CLIENT_PID)"
        return 0
    else
        echo "⚠️  Electron客户端启动失败"
        return 1
    fi
}

# 显示访问信息
show_info() {
    echo ""
    echo "🎉 日志分析平台启动完成！"
    echo "========================="

    # 获取IP地址
    LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

    echo "🌐 Web前端界面:"
    echo "   http://localhost:3000"
    [ "$LOCAL_IP" != "localhost" ] && echo "   http://$LOCAL_IP:3000"

    echo ""
    echo "🔗 后端API服务:"
    echo "   http://localhost:8001"
    [ "$LOCAL_IP" != "localhost" ] && echo "   http://$LOCAL_IP:8001"

    echo ""
    echo "📚 API文档:"
    echo "   http://localhost:8001/docs"
    [ "$LOCAL_IP" != "localhost" ] && echo "   http://$LOCAL_IP:8001/docs"

    echo ""
    echo "📱 客户端应用:"
    if [ "$EUID" -eq 0 ]; then
        echo "   ⚠️  Electron需要在桌面环境下单独启动"
        echo "   💻 推荐使用Web界面: http://localhost:3000"
    else
        echo "   🖥️  Electron应用 (如果启动成功)"
        echo "   💻 Web界面: http://localhost:3000"
    fi

    echo ""
    echo "⏹️  停止: 按 Ctrl+C"
    echo "========================="
}

# 清理函数
cleanup() {
    echo ""
    echo "🛑 正在停止服务..."

    # 停止后端
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi

    # 停止Web前端
    if [ ! -z "$WEB_FRONTEND_PID" ]; then
        kill $WEB_FRONTEND_PID 2>/dev/null || true
    fi

    # 停止Electron客户端
    if [ ! -z "$CLIENT_PID" ]; then
        kill $CLIENT_PID 2>/dev/null || true
    fi

    # 强制清理
    pkill -f "uvicorn.*8001" 2>/dev/null || true
    pkill -f "next.*3000" 2>/dev/null || true
    pkill -f "electron" 2>/dev/null || true

    success_msg "服务已停止"
    exit 0
}

# 捕获中断信号
trap cleanup SIGINT SIGTERM

# 主菜单函数
show_menu() {
    echo ""
    echo "请选择操作:"
    echo "1) 🚀 启动平台 (推荐)"
    echo "2) 🛑 停止所有服务"
    echo "3) 🔧 仅安装依赖"
    echo "4) 📊 检查服务状态"
    echo "5) 🆘 帮助信息"
    echo "6) 🔧 重置环境"
    echo "0) 退出"
    echo ""
    read -p "请输入选择 [1]: " choice
    choice=${choice:-1}
}

# 停止所有服务
stop_services() {
    echo "🛑 停止所有服务..."
    
    # 停止端口占用的进程
    for port in 3000 3001 8000 8001; do
        PID=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$PID" ]; then
            kill -TERM $PID 2>/dev/null
            echo "✅ 端口 $port 已释放"
        fi
    done
    
    # 停止相关进程
    pkill -f uvicorn 2>/dev/null || true
    pkill -f "next.*dev" 2>/dev/null || true
    
    success_msg "所有服务已停止"
}

# 检查服务状态
check_status() {
    echo "📊 检查服务状态..."
    echo ""
    
    # 检查后端
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "✅ 后端服务: 运行正常 (http://localhost:8001)"
    else
        echo "❌ 后端服务: 未运行"
    fi
    
    # 检查前端
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ 前端服务: 运行正常 (http://localhost:3000)"
    else
        echo "❌ 前端服务: 未运行"
    fi
    
    echo ""
    echo "📋 端口占用情况:"
    for port in 3000 8001; do
        if lsof -ti:$port &>/dev/null; then
            echo "   端口 $port: 占用中"
        else
            echo "   端口 $port: 空闲"
        fi
    done
    
    echo ""
    echo "🐍 Python环境:"
    if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
        echo "   虚拟环境: ✅ 正常"
    else
        echo "   虚拟环境: ❌ 需要重新创建"
    fi
}

# 重置环境
reset_environment() {
    echo "🔧 重置开发环境..."
    
    # 停止所有服务
    stop_services
    
    # 删除虚拟环境
    if [ -d "venv" ]; then
        echo "删除Python虚拟环境..."
        rm -rf venv
    fi
    
    # 删除客户端node_modules
    if [ -d "client/node_modules" ]; then
        echo "删除客户端依赖..."
        rm -rf client/node_modules
        rm -f client/package-lock.json
    fi

    # 删除前端node_modules (如果存在)
    if [ -d "frontend/node_modules" ]; then
        echo "删除前端依赖..."
        rm -rf frontend/node_modules
        rm -f frontend/package-lock.json
    fi
    
    success_msg "环境重置完成！现在可以重新安装依赖"
}

# 显示帮助
show_help() {
    echo "🆘 日志分析平台帮助"
    echo "=================="
    echo ""
    echo "快速启动:"
    echo "  ./start.sh         # 显示菜单"
    echo "  ./start.sh 1       # 直接启动"
    echo "  ./start.sh 2       # 停止服务"
    echo ""
    echo "故障排除:"
    echo "  1. 端口被占用 → 选择'停止所有服务'"
    echo "  2. 依赖问题 → 选择'仅安装依赖'"
    echo "  3. 环境问题 → 选择'重置环境'"
    echo "  4. Python环境 → 自动创建虚拟环境"
    echo ""
    echo "访问地址:"
    echo "  前端: http://localhost:3000"
    echo "  API:  http://localhost:8001/docs"
    echo ""
    echo "环境要求:"
    echo "  - Python 3.8+"
    echo "  - Node.js 16+"
    echo "  - 2GB+ 可用内存"
}

# 主程序入口
main() {
    # 如果有参数，直接执行
    if [ ! -z "$1" ]; then
        choice=$1
    else
        show_menu
    fi
    
    case $choice in
        1)
            echo "🚀 开始启动平台..."
            install_system_deps
            setup_python_env
            install_backend_deps
            install_frontend_deps
            start_backend
            start_web_frontend
            start_client
            show_info

            # 保持运行
            while true; do
                sleep 60
                # 检查后端服务
                if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
                    echo "⚠️  后端服务异常，尝试重启..."
                    start_backend
                fi
                # 检查Web前端服务
                if [ -d "frontend" ] && ! curl -s http://localhost:3000 > /dev/null 2>&1; then
                    echo "⚠️  Web前端服务异常，尝试重启..."
                    start_web_frontend
                fi
            done
            ;;
        2)
            stop_services
            ;;
        3)
            install_system_deps
            setup_python_env
            install_backend_deps
            install_frontend_deps
            echo "✅ 依赖安装完成！现在可以选择'启动平台'"
            ;;
        4)
            check_status
            ;;
        5)
            show_help
            ;;
        6)
            reset_environment
            ;;
        0)
            echo "👋 再见！"
            exit 0
            ;;
        *)
            echo "❌ 无效选择，请重新输入"
            main
            ;;
    esac
}

# 执行主程序
main $1 