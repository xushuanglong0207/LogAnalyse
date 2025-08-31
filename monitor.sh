#!/bin/bash

# 系统监控和自动恢复脚本
echo "🔍 日志分析平台监控器"
echo "===================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
CHECK_INTERVAL=30           # 检查间隔（秒）
MAX_MEMORY_USAGE=85        # 内存使用警告阈值（%）
MAX_CPU_USAGE=80           # CPU使用警告阈值（%）
LOG_FILE="./database/logs/monitor.log"
RESTART_THRESHOLD=3        # 连续失败次数后重启

# 计数器
BACKEND_FAIL_COUNT=0
FRONTEND_FAIL_COUNT=0
DB_FAIL_COUNT=0

# 日志函数
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo -e "$1"
}

log_error() {
    log_message "${RED}[ERROR] $1${NC}"
}

log_warn() {
    log_message "${YELLOW}[WARN] $1${NC}"
}

log_info() {
    log_message "${BLUE}[INFO] $1${NC}"
}

log_success() {
    log_message "${GREEN}[SUCCESS] $1${NC}"
}

# 确保日志目录存在
mkdir -p ./database/logs

# 检查服务健康状态
check_service_health() {
    local service_name=$1
    local health_check=$2
    local fail_count_var=$3
    
    if eval "$health_check" >/dev/null 2>&1; then
        eval "${fail_count_var}=0"
        return 0
    else
        eval "((${fail_count_var}++))"
        local current_count
        eval "current_count=\$${fail_count_var}"
        log_warn "$service_name 健康检查失败 (失败次数: $current_count)"
        return 1
    fi
}

# 重启服务
restart_service() {
    local service_name=$1
    log_warn "重启服务: $service_name"
    
    if docker compose restart "$service_name"; then
        log_success "$service_name 重启成功"
        sleep 30  # 等待服务启动
        return 0
    else
        log_error "$service_name 重启失败"
        return 1
    fi
}

# 获取容器资源使用情况
get_container_stats() {
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null | grep -E "(backend|frontend|postgres|redis)" || echo "无法获取容器统计信息"
}

# 检查磁盘空间
check_disk_space() {
    local usage=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$usage" -gt 90 ]; then
        log_error "磁盘空间不足: ${usage}%"
        return 1
    elif [ "$usage" -gt 80 ]; then
        log_warn "磁盘空间警告: ${usage}%"
    fi
    return 0
}

# 清理旧日志
cleanup_logs() {
    log_info "清理旧日志文件..."
    
    # 清理超过7天的日志文件
    find ./database/logs -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    # 限制监控日志大小
    if [ -f "$LOG_FILE" ] && [ $(wc -l < "$LOG_FILE") -gt 10000 ]; then
        tail -n 5000 "$LOG_FILE" > "${LOG_FILE}.tmp"
        mv "${LOG_FILE}.tmp" "$LOG_FILE"
        log_info "监控日志已轮转"
    fi
}

# 自动备份
auto_backup() {
    local hour=$(date +%H)
    # 每天凌晨2点自动备份
    if [ "$hour" = "02" ] && [ ! -f "/tmp/backup_done_$(date +%Y%m%d)" ]; then
        log_info "开始自动备份..."
        ./docker-start.sh backup
        touch "/tmp/backup_done_$(date +%Y%m%d)"
        log_success "自动备份完成"
    fi
}

# 主监控循环
monitor_loop() {
    log_info "监控器启动，检查间隔: ${CHECK_INTERVAL}秒"
    
    while true; do
        # 检查后端API
        if check_service_health "Backend API" "curl -sf http://localhost:8001/health" "BACKEND_FAIL_COUNT"; then
            log_info "后端服务正常"
        else
            if [ $BACKEND_FAIL_COUNT -ge $RESTART_THRESHOLD ]; then
                restart_service "backend"
                BACKEND_FAIL_COUNT=0
            fi
        fi
        
        # 检查前端
        if check_service_health "Frontend" "curl -sf http://localhost:3000" "FRONTEND_FAIL_COUNT"; then
            log_info "前端服务正常"
        else
            if [ $FRONTEND_FAIL_COUNT -ge $RESTART_THRESHOLD ]; then
                restart_service "frontend"
                FRONTEND_FAIL_COUNT=0
            fi
        fi
        
        # 检查数据库
        if check_service_health "Database" "docker compose exec -T postgres pg_isready -U admin -d loganalyzer" "DB_FAIL_COUNT"; then
            log_info "数据库服务正常"
        else
            if [ $DB_FAIL_COUNT -ge $RESTART_THRESHOLD ]; then
                restart_service "postgres"
                DB_FAIL_COUNT=0
            fi
        fi
        
        # 检查系统资源
        log_info "系统资源状况:"
        get_container_stats
        
        # 检查磁盘空间
        check_disk_space
        
        # 清理旧日志（每小时执行一次）
        local minute=$(date +%M)
        if [ "$minute" = "00" ]; then
            cleanup_logs
        fi
        
        # 自动备份
        auto_backup
        
        log_info "监控检查完成，等待 ${CHECK_INTERVAL} 秒..."
        sleep $CHECK_INTERVAL
    done
}

# 显示实时状态
show_realtime_status() {
    while true; do
        clear
        echo -e "${BLUE}🔍 日志分析平台实时状态${NC}"
        echo "================================"
        echo "时间: $(date)"
        echo ""
        
        # 服务状态
        echo "📊 服务状态:"
        if curl -sf http://localhost:8001/health >/dev/null 2>&1; then
            echo -e "   后端API: ${GREEN}✅ 正常${NC}"
        else
            echo -e "   后端API: ${RED}❌ 异常${NC}"
        fi
        
        if curl -sf http://localhost:3000 >/dev/null 2>&1; then
            echo -e "   前端: ${GREEN}✅ 正常${NC}"
        else
            echo -e "   前端: ${RED}❌ 异常${NC}"
        fi
        
        if docker compose exec -T postgres pg_isready -U admin -d loganalyzer >/dev/null 2>&1; then
            echo -e "   数据库: ${GREEN}✅ 正常${NC}"
        else
            echo -e "   数据库: ${RED}❌ 异常${NC}"
        fi
        
        echo ""
        
        # 容器资源使用
        echo "💻 容器资源使用:"
        get_container_stats
        echo ""
        
        # 磁盘使用
        echo "💾 磁盘使用:"
        df -h . | tail -1
        echo ""
        
        # 最近日志
        echo "📄 最近日志 (最新10条):"
        if [ -f "$LOG_FILE" ]; then
            tail -10 "$LOG_FILE" | while read line; do
                if [[ "$line" == *"ERROR"* ]]; then
                    echo -e "${RED}$line${NC}"
                elif [[ "$line" == *"WARN"* ]]; then
                    echo -e "${YELLOW}$line${NC}"
                elif [[ "$line" == *"SUCCESS"* ]]; then
                    echo -e "${GREEN}$line${NC}"
                else
                    echo -e "${BLUE}$line${NC}"
                fi
            done
        else
            echo "暂无日志记录"
        fi
        
        echo ""
        echo -e "${YELLOW}按 Ctrl+C 退出实时监控${NC}"
        
        sleep 5
    done
}

# 显示帮助
show_help() {
    echo -e "${BLUE}🆘 监控脚本帮助${NC}"
    echo "==============="
    echo ""
    echo "使用方法:"
    echo "  ./monitor.sh [命令]"
    echo ""
    echo "可用命令:"
    echo "  start    - 启动后台监控 (默认)"
    echo "  status   - 显示实时状态"
    echo "  stop     - 停止监控"
    echo "  logs     - 查看监控日志"
    echo "  help     - 显示帮助"
    echo ""
    echo "监控功能:"
    echo "  - 服务健康检查"
    echo "  - 自动重启异常服务"
    echo "  - 资源使用监控"
    echo "  - 磁盘空间检查"
    echo "  - 自动日志清理"
    echo "  - 定时数据备份"
}

# 停止监控
stop_monitor() {
    log_info "停止监控进程..."
    pkill -f "monitor.sh" 2>/dev/null || true
    log_success "监控已停止"
}

# 主程序
main() {
    # 检查是否在项目根目录
    if [ ! -f "docker-compose.yml" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 获取命令参数
    COMMAND=${1:-start}
    
    case $COMMAND in
        start)
            log_info "启动后台监控..."
            nohup bash "$0" _monitor > /dev/null 2>&1 &
            echo $! > ./database/logs/monitor.pid
            log_success "监控已启动 (PID: $!)"
            ;;
        _monitor)
            monitor_loop
            ;;
        status)
            show_realtime_status
            ;;
        stop)
            stop_monitor
            ;;
        logs)
            if [ -f "$LOG_FILE" ]; then
                tail -100 "$LOG_FILE"
            else
                echo "监控日志文件不存在"
            fi
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

# 捕获中断信号
trap 'log_info "监控器被中断"; exit 0' SIGINT SIGTERM

# 执行主程序
main $@