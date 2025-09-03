#!/bin/bash
echo "🚀 启动NAS监控系统"

# 检查依赖
python3 -c "import paramiko" 2>/dev/null || {
    echo "正在安装paramiko..."
    pip3 install paramiko --break-system-packages
}

# 创建目录
mkdir -p error_logs database

echo "✅ 启动监控服务..."
cd backend && python3 monitor.py &
echo $! > ../monitor.pid

echo "监控服务已启动 (PID: $(cat ../monitor.pid))"
echo "停止服务: kill $(cat monitor.pid)"
echo ""
echo "📋 功能说明:"
echo "✅ 每小时SSH连接NAS获取系统信息"
echo "✅ 分析指定日志路径，检测错误"  
echo "✅ 错误记录到txt文档(按小时追加)"
echo "✅ 每天15点发送汇总邮件"
echo "✅ 数据持久化存储"
echo "✅ 文件大小限制100MB"
echo ""
echo "📁 配置文件:"
echo "- 邮件配置: backend/.env"
echo "- 设备数据: database/nas_devices.json"
echo "- 错误日志: error_logs/"
echo ""
echo "🔧 测试工具:"
echo "- SSH测试: python3 test_ssh.py <IP> <用户> <密码>"

wait
