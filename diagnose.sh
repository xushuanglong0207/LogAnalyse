#!/bin/bash

# 快速问题诊断脚本
echo "🔧 系统问题诊断工具"
echo "=================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 诊断函数
diagnose_problem() {
    echo -e "${BLUE}开始系统诊断...${NC}"
    echo ""
    
    # 1. 检查Docker环境
    echo "1. 🐳 Docker 环境检查:"
    if command -v docker &> /dev/null; then
        echo -e "   Docker: ${GREEN}✅ 已安装${NC}"
        if docker info &> /dev/null; then
            echo -e "   Docker服务: ${GREEN}✅ 运行中${NC}"
        else
            echo -e "   Docker服务: ${RED}❌ 未运行${NC}"
            echo "   解决方案: 启动Docker服务"
        fi
    else
        echo -e "   Docker: ${RED}❌ 未安装${NC}"
        echo "   解决方案: 安装Docker"
    fi
    echo ""
    
    # 2. 检查端口占用
    echo "2. 🔌 端口占用检查:"
    for port in 3000 5433 6380 8001; do
        if command -v lsof &> /dev/null; then
            if lsof -ti:$port &>/dev/null; then
                local pid=$(lsof -ti:$port)
                local process=$(ps -p $pid -o comm= 2>/dev/null || echo "未知")
                echo -e "   端口 $port: ${YELLOW}⚠️  被占用${NC} (PID: $pid, 进程: $process)"
            else
                echo -e "   端口 $port: ${GREEN}✅ 可用${NC}"
            fi
        elif command -v netstat &> /dev/null; then
            if netstat -tlnp 2>/dev/null | grep ":$port " &>/dev/null; then
                echo -e "   端口 $port: ${YELLOW}⚠️  被占用${NC}"
            else
                echo -e "   端口 $port: ${GREEN}✅ 可用${NC}"
            fi
        else
            echo -e "   端口 $port: ${BLUE}ℹ️  无法检测${NC} (缺少lsof/netstat)"
        fi
    done
    echo ""
    
    # 3. 检查容器状态
    echo "3. 📦 容器状态检查:"
    if docker compose ps &>/dev/null; then
        docker compose ps
    else
        echo -e "   ${RED}❌ 无法获取容器状态，可能Docker Compose未启动${NC}"
    fi
    echo ""
    
    # 4. 检查系统资源
    echo "4. 💻 系统资源检查:"
    echo "   内存使用:"
    free -h
    echo ""
    echo "   磁盘使用:"
    df -h .
    echo ""
    echo "   CPU负载:"
    uptime
    echo ""
    
    # 5. 检查日志错误
    echo "5. 📄 最近错误日志:"
    if [ -f "./database/logs/monitor.log" ]; then
        echo "   监控日志错误:"
        grep -i error "./database/logs/monitor.log" | tail -5 2>/dev/null || echo "   无错误记录"
    fi
    
    # Docker容器日志
    echo "   容器日志错误:"
    docker compose logs --tail=20 2>&1 | grep -i error | head -5 2>/dev/null || echo "   无容器错误"
    echo ""
    
    # 6. 网络连通性检查
    echo "6. 🌐 网络连通性检查:"
    if curl -sf http://localhost:8001/health &>/dev/null; then
        echo -e "   后端API: ${GREEN}✅ 可访问${NC}"
    else
        echo -e "   后端API: ${RED}❌ 不可访问${NC}"
    fi
    
    if curl -sf http://localhost:3000 &>/dev/null; then
        echo -e "   前端: ${GREEN}✅ 可访问${NC}"
    else
        echo -e "   前端: ${RED}❌ 不可访问${NC}"
    fi
    echo ""
    
    # 7. 数据目录检查
    echo "7. 📁 数据目录检查:"
    for dir in "./database" "./database/uploads" "./database/logs"; do
        if [ -d "$dir" ]; then
            local size=$(du -sh "$dir" 2>/dev/null | cut -f1)
            echo -e "   $dir: ${GREEN}✅ 存在${NC} (大小: $size)"
        else
            echo -e "   $dir: ${RED}❌ 不存在${NC}"
        fi
    done
    echo ""
}

# 自动修复函数
auto_fix() {
    echo -e "${BLUE}开始自动修复...${NC}"
    echo ""
    
    # 1. 创建缺失目录
    echo "1. 📁 创建必要目录:"
    for dir in "./database" "./database/uploads" "./database/logs" "./database/backups"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            echo -e "   创建目录: $dir ${GREEN}✅${NC}"
        fi
    done
    
    # 2. 释放占用端口
    echo "2. 🔌 释放端口占用:"
    for port in 3000 8001; do
        local pid=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$pid" ]; then
            kill -TERM $pid 2>/dev/null
            echo -e "   释放端口 $port ${GREEN}✅${NC}"
        fi
    done
    
    # 3. 清理Docker资源
    echo "3. 🧹 清理Docker资源:"
    docker compose down -v --remove-orphans &>/dev/null
    docker system prune -f &>/dev/null
    echo -e "   Docker清理完成 ${GREEN}✅${NC}"
    
    # 4. 重置权限
    echo "4. 🔐 重置目录权限:"
    chmod 755 ./database 2>/dev/null
    chmod 755 ./database/uploads 2>/dev/null
    chmod 755 ./database/logs 2>/dev/null
    echo -e "   权限设置完成 ${GREEN}✅${NC}"
    
    echo ""
    echo -e "${GREEN}✅ 自动修复完成！${NC}"
    echo -e "${YELLOW}建议现在运行: ./docker-start.sh start${NC}"
}

# 性能优化建议
performance_tips() {
    echo -e "${BLUE}🚀 性能优化建议${NC}"
    echo "================"
    echo ""
    
    echo "📊 当前系统状态:"
    
    # 检查内存
    local total_mem=$(free -g | awk 'NR==2{print $2}')
    local used_mem=$(free -g | awk 'NR==2{print $3}')
    local mem_percent=$((used_mem * 100 / total_mem))
    
    echo "   内存使用: ${used_mem}GB / ${total_mem}GB (${mem_percent}%)"
    
    if [ $mem_percent -gt 80 ]; then
        echo -e "   ${RED}❌ 内存使用过高${NC}"
        echo "   建议: 减少并发用户数量或增加系统内存"
    elif [ $mem_percent -gt 60 ]; then
        echo -e "   ${YELLOW}⚠️  内存使用较高${NC}"
        echo "   建议: 监控内存使用情况"
    else
        echo -e "   ${GREEN}✅ 内存使用正常${NC}"
    fi
    
    # 检查磁盘空间
    local disk_usage=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
    echo "   磁盘使用: ${disk_usage}%"
    
    if [ $disk_usage -gt 85 ]; then
        echo -e "   ${RED}❌ 磁盘空间不足${NC}"
        echo "   建议: 清理旧文件或扩展存储空间"
    elif [ $disk_usage -gt 70 ]; then
        echo -e "   ${YELLOW}⚠️  磁盘使用较高${NC}"
        echo "   建议: 定期清理上传文件和日志"
    else
        echo -e "   ${GREEN}✅ 磁盘空间充足${NC}"
    fi
    
    echo ""
    echo "🔧 优化建议:"
    echo "1. 限制文件上传大小 (当前: 10MB)"
    echo "2. 减少并发分析任务数 (当前: 2个)"
    echo "3. 定期清理旧的上传文件"
    echo "4. 使用监控脚本自动管理资源"
    echo "5. 在高负载时重启服务释放内存"
    
    echo ""
    echo "⚡ 紧急处理高负载:"
    echo "   ./docker-start.sh restart  # 重启所有服务"
    echo "   ./monitor.sh start         # 启动自动监控"
}

# 显示常见问题解决方案
show_solutions() {
    echo -e "${BLUE}🆘 常见问题解决方案${NC}"
    echo "=================="
    echo ""
    
    echo "❓ 问题: 服务启动失败"
    echo "💡 解决方案:"
    echo "   1. 检查端口占用: lsof -i:3000,8001"
    echo "   2. 清理Docker: docker system prune -af"
    echo "   3. 重新启动: ./docker-start.sh restart"
    echo ""
    
    echo "❓ 问题: 文件上传失败/服务崩溃"
    echo "💡 解决方案:"
    echo "   1. 检查文件大小 (限制: 10MB)"
    echo "   2. 检查系统内存使用情况"
    echo "   3. 减少同时上传的用户数量"
    echo "   4. 重启后端服务: docker compose restart backend"
    echo ""
    
    echo "❓ 问题: 数据丢失"
    echo "💡 解决方案:"
    echo "   1. 检查数据目录: ls -la ./database/"
    echo "   2. 恢复备份: ./docker-start.sh restore"
    echo "   3. 重新初始化: ./docker-start.sh clean"
    echo ""
    
    echo "❓ 问题: 性能缓慢"
    echo "💡 解决方案:"
    echo "   1. 运行诊断: ./diagnose.sh performance"
    echo "   2. 启动监控: ./monitor.sh start"
    echo "   3. 限制并发用户数量"
    echo ""
    
    echo "❓ 问题: 网络连接问题"
    echo "💡 解决方案:"
    echo "   1. 检查防火墙设置"
    echo "   2. 确认Docker网络配置"
    echo "   3. 重启Docker服务"
}

# 显示帮助
show_help() {
    echo -e "${BLUE}🆘 诊断工具帮助${NC}"
    echo "=============="
    echo ""
    echo "使用方法:"
    echo "  ./diagnose.sh [命令]"
    echo ""
    echo "可用命令:"
    echo "  check       - 系统诊断检查 (默认)"
    echo "  fix         - 自动修复常见问题"
    echo "  performance - 性能分析和建议"
    echo "  solutions   - 常见问题解决方案"
    echo "  help        - 显示帮助"
    echo ""
    echo "使用示例:"
    echo "  ./diagnose.sh           # 运行完整诊断"
    echo "  ./diagnose.sh fix       # 自动修复问题"
    echo "  ./diagnose.sh performance # 性能分析"
}

# 主程序
main() {
    # 检查是否在项目根目录
    if [ ! -f "docker-compose.yml" ]; then
        echo -e "${RED}❌ 请在项目根目录运行此脚本${NC}"
        exit 1
    fi
    
    # 获取命令参数
    COMMAND=${1:-check}
    
    case $COMMAND in
        check)
            diagnose_problem
            ;;
        fix)
            auto_fix
            ;;
        performance)
            performance_tips
            ;;
        solutions)
            show_solutions
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