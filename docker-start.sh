#!/bin/bash

# Docker Compose 日志分析平台启动脚本
echo "🐳 Docker 日志分析平台启动器"
echo "============================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 错误处理函数
handle_error() {
    echo -e "${RED}❌ 错误: $1${NC}"
    echo -e "${YELLOW}💡 请查看错误信息并重试${NC}"
    exit 1
}

# 成功信息函数
success_msg() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 信息函数
info_msg() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 警告函数
warn_msg() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 检查Docker和Docker Compose
check_docker() {
    info_msg "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        handle_error "Docker 未安装，请先安装 Docker"
    fi
    
    if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        handle_error "Docker Compose 未安装，请先安装 Docker Compose"
    fi
    
    # 检查Docker服务是否运行
    if ! docker info &> /dev/null; then
        handle_error "Docker 服务未运行，请启动 Docker 服务"
    fi
    
    success_msg "Docker 环境检查通过"
}

# 检查并创建必要目录
setup_directories() {
    info_msg "设置数据目录..."
    
    # 确保数据目录存在
    mkdir -p ./database
    mkdir -p ./database/uploads
    mkdir -p ./database/logs
    mkdir -p ./database/backups
    
    # 设置正确的权限
    chmod 755 ./database
    chmod 755 ./database/uploads
    chmod 755 ./database/logs
    chmod 755 ./database/backups
    
    success_msg "数据目录设置完成"
}

# 清理旧的容器和网络
cleanup_old() {
    info_msg "清理旧的容器..."
    
    # 停止并删除旧容器
    docker compose down -v --remove-orphans 2>/dev/null || docker-compose down -v --remove-orphans 2>/dev/null || true
    
    # 清理无用的镜像和网络
    docker system prune -f --volumes 2>/dev/null || true
    
    success_msg "清理完成"
}

# 构建和启动服务
start_services() {
    info_msg "构建和启动服务..."
    
    # 使用docker compose或docker-compose
    COMPOSE_CMD="docker compose"
    if ! command -v docker compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    fi
    
    # 拉取最新镜像
    info_msg "拉取Docker镜像..."
    $COMPOSE_CMD pull
    
    # 构建并启动服务
    info_msg "启动服务容器..."
    $COMPOSE_CMD up --build -d
    
    if [ $? -ne 0 ]; then
        handle_error "服务启动失败"
    fi
    
    success_msg "服务启动成功"
}

# 等待服务就绪
wait_for_services() {
    info_msg "等待服务启动..."
    
    # 等待数据库
    echo -n "等待数据库启动"
    for i in {1..30}; do
        if docker compose exec -T postgres pg_isready -U admin -d loganalyzer &>/dev/null; then
            echo ""
            success_msg "数据库服务就绪"
            break
        fi
        echo -n "."
        sleep 2
        if [ $i -eq 30 ]; then
            echo ""
            warn_msg "数据库启动超时，但将继续..."
        fi
    done
    
    # 等待Redis
    echo -n "等待Redis启动"
    for i in {1..15}; do
        if docker compose exec -T redis redis-cli ping &>/dev/null; then
            echo ""
            success_msg "Redis服务就绪"
            break
        fi
        echo -n "."
        sleep 1
        if [ $i -eq 15 ]; then
            echo ""
            warn_msg "Redis启动超时，但将继续..."
        fi
    done
    
    # 等待后端API
    echo -n "等待后端API启动"
    for i in {1..60}; do
        if curl -sf http://localhost:8001/health &>/dev/null; then
            echo ""
            success_msg "后端API服务就绪"
            break
        fi
        echo -n "."
        sleep 2
        if [ $i -eq 60 ]; then
            echo ""
            warn_msg "后端API启动超时，但将继续..."
        fi
    done
    
    # 等待前端
    echo -n "等待前端服务启动"
    for i in {1..45}; do
        if curl -sf http://localhost:3000 &>/dev/null; then
            echo ""
            success_msg "前端服务就绪"
            break
        fi
        echo -n "."
        sleep 2
        if [ $i -eq 45 ]; then
            echo ""
            warn_msg "前端服务启动超时，请检查日志"
        fi
    done
}

# 显示服务状态
show_status() {
    info_msg "服务状态检查..."
    echo ""
    
    # 检查容器状态
    echo "📦 容器状态:"
    docker compose ps
    echo ""
    
    # 检查服务健康状态
    echo "🏥 服务健康检查:"
    
    # 检查数据库
    if docker compose exec -T postgres pg_isready -U admin -d loganalyzer &>/dev/null; then
        echo -e "   数据库: ${GREEN}✅ 正常${NC}"
    else
        echo -e "   数据库: ${RED}❌ 异常${NC}"
    fi
    
    # 检查Redis
    if docker compose exec -T redis redis-cli ping &>/dev/null; then
        echo -e "   Redis: ${GREEN}✅ 正常${NC}"
    else
        echo -e "   Redis: ${RED}❌ 异常${NC}"
    fi
    
    # 检查后端API
    if curl -sf http://localhost:8001/health &>/dev/null; then
        echo -e "   后端API: ${GREEN}✅ 正常${NC}"
    else
        echo -e "   后端API: ${RED}❌ 异常${NC}"
    fi
    
    # 检查前端
    if curl -sf http://localhost:3000 &>/dev/null; then
        echo -e "   前端服务: ${GREEN}✅ 正常${NC}"
    else
        echo -e "   前端服务: ${RED}❌ 异常${NC}"
    fi
    
    echo ""
    
    # 显示资源使用情况
    echo "💻 系统资源:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" || true
}

# 显示访问信息
show_access_info() {
    echo ""
    echo -e "${GREEN}🎉 日志分析平台启动完成！${NC}"
    echo "============================"
    
    # 获取IP地址
    LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    
    echo -e "${BLUE}📱 前端访问:${NC}"
    echo "   http://localhost:3000"
    [ "$LOCAL_IP" != "localhost" ] && echo "   http://$LOCAL_IP:3000"
    
    echo ""
    echo -e "${BLUE}🔗 API文档:${NC}"
    echo "   http://localhost:8001/docs"
    [ "$LOCAL_IP" != "localhost" ] && echo "   http://$LOCAL_IP:8001/docs"
    
    echo ""
    echo -e "${BLUE}🗄️  数据库连接:${NC}"
    echo "   Host: localhost:5433"
    echo "   Database: loganalyzer"
    echo "   User: admin"
    
    echo ""
    echo -e "${YELLOW}⚠️  重要说明:${NC}"
    echo "   - 数据持久化在 ./database/ 目录"
    echo "   - 日志文件在 ./database/logs/ 目录"
    echo "   - 上传文件在 ./database/uploads/ 目录"
    
    echo ""
    echo -e "${BLUE}🛠️  管理命令:${NC}"
    echo "   查看日志: ./docker-start.sh logs"
    echo "   查看状态: ./docker-start.sh status"
    echo "   停止服务: ./docker-start.sh stop"
    echo "   重启服务: ./docker-start.sh restart"
    echo "   备份数据: ./docker-start.sh backup"
    echo ""
    echo -e "${GREEN}===========================${NC}"
}

# 显示日志
show_logs() {
    echo -e "${BLUE}📄 实时日志 (Ctrl+C 退出):${NC}"
    docker compose logs -f --tail=100
}

# 停止服务
stop_services() {
    info_msg "停止服务..."
    docker compose down
    success_msg "服务已停止"
}

# 重启服务
restart_services() {
    info_msg "重启服务..."
    stop_services
    start_services
    wait_for_services
    show_access_info
}

# 备份数据
backup_data() {
    info_msg "备份数据..."
    
    BACKUP_DIR="./database/backups"
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    
    # 备份数据库
    docker compose exec -T postgres pg_dump -U admin -d loganalyzer > "$BACKUP_DIR/$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        success_msg "数据库备份完成: $BACKUP_DIR/$BACKUP_FILE"
    else
        handle_error "数据库备份失败"
    fi
    
    # 压缩上传文件
    if [ -d "./database/uploads" ] && [ "$(ls -A ./database/uploads 2>/dev/null)" ]; then
        UPLOADS_BACKUP="$BACKUP_DIR/uploads_$(date +%Y%m%d_%H%M%S).tar.gz"
        tar -czf "$UPLOADS_BACKUP" -C ./database uploads/
        success_msg "上传文件备份完成: $UPLOADS_BACKUP"
    fi
}

# 恢复数据
restore_data() {
    echo -e "${YELLOW}⚠️  数据恢复功能${NC}"
    echo "请手动执行以下命令:"
    echo ""
    echo "1. 恢复数据库:"
    echo "   docker compose exec -T postgres psql -U admin -d loganalyzer < ./database/backups/your_backup.sql"
    echo ""
    echo "2. 恢复上传文件:"
    echo "   tar -xzf ./database/backups/uploads_backup.tar.gz -C ./database/"
}

# 清理系统
clean_system() {
    warn_msg "这将删除所有容器、镜像和数据！"
    read -p "确定要继续吗？(输入 'yes' 确认): " confirm
    
    if [ "$confirm" = "yes" ]; then
        info_msg "清理Docker系统..."
        docker compose down -v --rmi all --remove-orphans
        docker system prune -af --volumes
        success_msg "系统清理完成"
    else
        info_msg "已取消清理操作"
    fi
}

# 显示帮助
show_help() {
    echo -e "${BLUE}🆘 Docker日志分析平台帮助${NC}"
    echo "=========================="
    echo ""
    echo "使用方法:"
    echo "  ./docker-start.sh [命令]"
    echo ""
    echo "可用命令:"
    echo "  start    - 启动平台 (默认)"
    echo "  stop     - 停止服务"
    echo "  restart  - 重启服务"
    echo "  status   - 查看状态"
    echo "  logs     - 查看日志"
    echo "  backup   - 备份数据"
    echo "  restore  - 恢复数据说明"
    echo "  clean    - 清理系统"
    echo "  help     - 显示帮助"
    echo ""
    echo "故障排除:"
    echo "  1. 服务异常 → 查看日志: ./docker-start.sh logs"
    echo "  2. 端口占用 → 停止服务: ./docker-start.sh stop"
    echo "  3. 数据丢失 → 恢复备份: ./docker-start.sh restore"
    echo "  4. 彻底重置 → 清理系统: ./docker-start.sh clean"
    echo ""
    echo "数据目录:"
    echo "  ./database/        - 主数据目录"
    echo "  ./database/uploads - 上传文件"
    echo "  ./database/logs    - 系统日志"
    echo "  ./database/backups - 备份文件"
}

# 主程序
main() {
    # 检查是否在项目根目录
    if [ ! -f "docker-compose.yml" ]; then
        handle_error "请在项目根目录（包含docker-compose.yml的目录）运行此脚本"
    fi
    
    # 获取命令参数
    COMMAND=${1:-start}
    
    case $COMMAND in
        start)
            check_docker
            setup_directories
            cleanup_old
            start_services
            wait_for_services
            show_access_info
            ;;
        stop)
            stop_services
            ;;
        restart)
            check_docker
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        backup)
            backup_data
            ;;
        restore)
            restore_data
            ;;
        clean)
            clean_system
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}❌ 未知命令: $COMMAND${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主程序
main $@