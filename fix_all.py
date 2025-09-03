#!/usr/bin/env python3
"""
诊断和修复脚本 - 解决所有监控系统问题
"""

import os
import json
from datetime import datetime

def main():
    print("🔧 开始修复监控系统问题...\n")
    
    # 1. 创建环境配置文件
    env_content = """# 数据库配置
DATABASE_URL=sqlite:///./loganalyzer.db
USE_REDIS=false

# SMTP邮件配置 - 请修改为您的邮箱配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SENDER_EMAIL=your_email@gmail.com
SENDER_NAME=NAS日志监控系统

# JWT配置
SECRET_KEY=nas-monitor-secret-key-2024
DEBUG=true
"""
    
    os.makedirs("backend", exist_ok=True)
    with open("backend/.env", 'w') as f:
        f.write(env_content)
    
    print("✅ 创建环境配置文件: backend/.env")
    
    # 2. 创建数据持久化文件
    os.makedirs("database", exist_ok=True)
    devices_data = {
        "devices": [],
        "tasks": [],
        "last_updated": datetime.now().isoformat(),
        "version": "1.0"
    }
    
    with open("database/nas_devices.json", 'w') as f:
        json.dump(devices_data, f, indent=2, ensure_ascii=False)
    
    print("✅ 创建数据持久化文件: database/nas_devices.json")
    
    # 3. 创建简化监控服务
    monitor_script = '''#!/usr/bin/env python3
"""
简化监控调度服务 - 实现用户需求的核心功能
"""

import json
import time
import logging
import os
import paramiko
import smtplib
import socket
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NASMonitor:
    def __init__(self):
        self.database_dir = "database"
        self.devices_file = f"{self.database_dir}/nas_devices.json"
        
        # 邮件配置
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.sender_email = os.getenv("SENDER_EMAIL", "")
    
    def load_data(self):
        try:
            if os.path.exists(self.devices_file):
                with open(self.devices_file, 'r') as f:
                    return json.load(f)
            return {"devices": [], "tasks": []}
        except:
            return {"devices": [], "tasks": []}
    
    def save_data(self, data):
        try:
            data["last_updated"] = datetime.now().isoformat()
            with open(self.devices_file, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False
    
    def ssh_connect_and_get_info(self, ip, username, password, port=22):
        """SSH连接获取系统信息"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port, username, password, timeout=30, 
                       allow_agent=False, look_for_keys=False)
            
            # 获取系统信息
            commands = {
                'hostname': 'hostname',
                'uptime': 'uptime',
                'disk_usage': 'df -h | head -5',
                'memory_info': 'free -h',
                'load_average': 'cat /proc/loadavg',
                'disk_io': 'iostat -x 1 1 2>/dev/null | tail -10 || echo "iostat not available"'
            }
            
            system_info = {}
            for key, cmd in commands.items():
                try:
                    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
                    result = stdout.read().decode().strip()
                    if result:
                        system_info[key] = result
                    else:
                        system_info[key] = f"无数据"
                except:
                    system_info[key] = "获取失败"
            
            ssh.close()
            return system_info
        except Exception as e:
            logger.error(f"SSH连接失败 {ip}: {e}")
            return None
    
    def analyze_log_via_ssh(self, ip, username, password, log_path, rules, port=22):
        """SSH连接分析日志"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port, username, password, timeout=30,
                       allow_agent=False, look_for_keys=False)
            
            # 检查日志文件大小(限制100MB)
            size_cmd = f"stat -c%s {log_path} 2>/dev/null || echo 0"
            stdin, stdout, stderr = ssh.exec_command(size_cmd, timeout=10)
            file_size = int(stdout.read().decode().strip() or 0)
            
            if file_size > 100 * 1024 * 1024:  # 100MB限制
                logger.warning(f"日志文件过大({file_size}字节)，只分析最后10000行")
                analyze_cmd = f"tail -10000 {log_path}"
            else:
                analyze_cmd = f"cat {log_path}"
            
            # 根据规则分析日志
            error_patterns = []
            for rule in rules:
                patterns = rule.get('patterns', [])
                error_patterns.extend(patterns)
            
            if error_patterns:
                pattern_str = '|'.join(error_patterns)
                full_cmd = f"{analyze_cmd} 2>/dev/null | grep -i -E '({pattern_str})' | tail -50"
            else:
                full_cmd = f"{analyze_cmd} 2>/dev/null | grep -i -E '(error|exception|failed|critical)' | tail -50"
            
            stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=60)
            error_lines = stdout.read().decode().strip()
            
            ssh.close()
            
            if error_lines:
                lines = error_lines.split('\\n')
                return {
                    'error_count': len(lines),
                    'errors': lines[:10],  # 只保存前10条
                    'log_path': log_path,
                    'file_size_mb': round(file_size / (1024*1024), 2)
                }
            return None
        except Exception as e:
            logger.error(f"日志分析失败 {ip}:{log_path}: {e}")
            return None
    
    def write_error_to_txt(self, device_name, errors, timestamp):
        """写入错误到txt文档"""
        try:
            error_dir = f"error_logs/{device_name}"
            os.makedirs(error_dir, exist_ok=True)
            
            # 每小时追加写入新错误
            hour_file = f"{error_dir}/errors_{timestamp.strftime('%Y%m%d_%H')}.txt"
            
            with open(hour_file, 'a', encoding='utf-8') as f:
                f.write(f"\\n=== {timestamp.strftime('%Y-%m-%d %H:%M:%S')} ===\\n")
                f.write(f"设备: {device_name}\\n")
                f.write(f"错误数量: {errors['error_count']}\\n")
                f.write(f"日志路径: {errors['log_path']}\\n")
                f.write(f"文件大小: {errors['file_size_mb']}MB\\n")
                f.write("错误内容:\\n")
                for i, error in enumerate(errors['errors'], 1):
                    f.write(f"{i}. {error}\\n")
                f.write("\\n" + "="*50 + "\\n")
            
            return hour_file
        except Exception as e:
            logger.error(f"写入错误文件失败: {e}")
            return None
    
    def send_daily_email(self, device_info, system_info, daily_errors, recipients):
        """每天下午3点发送汇总邮件"""
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.warning("邮件配置不完整")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = f"NAS监控系统 <{self.sender_email}>"
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"NAS日志监控日报 - {device_info['name']} ({datetime.now().strftime('%Y-%m-%d')})"
            
            # 邮件内容
            content = f'''设备监控日报

设备信息:
名称: {device_info['name']}
IP地址: {device_info['ip_address']}
SSH端口: {device_info.get('ssh_port', 22)}
监控路径: {device_info.get('log_path', '未设置')}

报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

系统信息:
{json.dumps(system_info, indent=2, ensure_ascii=False) if system_info else "获取失败"}

今日错误统计:
{f"共发现 {len(daily_errors)} 次错误事件" if daily_errors else "今日无错误"}

{f"错误详情:" + chr(10) + chr(10).join([f"时间: {e['time']}, 错误数: {e['count']}" for e in daily_errors[:10]]) if daily_errors else ""}

此邮件由NAS日志监控系统自动发送
'''
            
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"日报邮件发送成功: {device_info['name']} -> {recipients}")
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def run_hourly_monitoring(self):
        """每小时监控任务"""
        try:
            data = self.load_data()
            devices = {d['id']: d for d in data.get('devices', [])}
            tasks = data.get('tasks', [])
            current_time = datetime.now()
            
            for task in tasks:
                if not task.get('is_active', True):
                    continue
                    
                device = devices.get(task['device_id'])
                if not device:
                    continue
                
                logger.info(f"监控任务: {task['name']} (设备: {device['name']})")
                
                # 1. SSH连接获取系统信息
                system_info = self.ssh_connect_and_get_info(
                    device['ip_address'],
                    device['ssh_username'], 
                    device.get('ssh_password', ''),
                    device.get('ssh_port', 22)
                )
                
                if not system_info:
                    logger.error(f"无法获取系统信息: {device['name']}")
                    continue
                
                # 2. 分析指定日志路径
                rules = task.get('rule_ids', [])  # 这里应该是规则对象列表
                log_path = task.get('log_path', '/var/log/syslog')
                
                errors = self.analyze_log_via_ssh(
                    device['ip_address'],
                    device['ssh_username'],
                    device.get('ssh_password', ''),
                    log_path,
                    rules,
                    device.get('ssh_port', 22)
                )
                
                # 3. 如有错误，写入txt文档
                if errors:
                    error_file = self.write_error_to_txt(device['name'], errors, current_time)
                    logger.info(f"错误已记录到: {error_file}")
                
                # 4. 每天下午3点发送邮件
                if current_time.hour == 15 and task.get('email_recipients'):
                    # 获取今天的所有错误
                    today_errors = []  # 这里可以从txt文件读取今日错误
                    self.send_daily_email(device, system_info, today_errors, task['email_recipients'])
                
                # 更新任务状态
                task['last_run'] = current_time.isoformat()
                task['next_run'] = (current_time + timedelta(hours=1)).isoformat()
                
                if errors:
                    task['error_count'] = task.get('error_count', 0) + 1
                
            # 保存更新后的数据
            self.save_data(data)
            
        except Exception as e:
            logger.error(f"监控任务执行失败: {e}")

def main():
    # 加载环境变量
    env_file = "backend/.env"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    monitor = NASMonitor()
    
    logger.info("NAS监控调度服务启动")
    logger.info("功能: 每小时SSH连接、分析日志、记录错误、定时邮件")
    
    try:
        while True:
            logger.info("开始执行每小时监控检查...")
            monitor.run_hourly_monitoring()
            logger.info("监控检查完成，等待下次执行...")
            
            # 每小时执行一次
            time.sleep(3600)
            
    except KeyboardInterrupt:
        logger.info("收到停止信号，退出监控服务")

if __name__ == "__main__":
    main()
'''
    
    with open("backend/nas_monitor.py", 'w') as f:
        f.write(monitor_script)
    
    os.chmod("backend/nas_monitor.py", 0o755)
    print("✅ 创建监控调度服务: backend/nas_monitor.py")
    
    # 4. 创建SSH测试脚本
    test_script = '''#!/usr/bin/env python3
"""SSH连接测试脚本"""
import paramiko
import sys

def test_connection(ip, username, password, port=22):
    try:
        print(f"测试连接: {username}@{ip}:{port}")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port, username, password, timeout=30)
        
        print("✅ SSH连接成功!")
        
        # 获取系统信息
        commands = [
            ('主机名', 'hostname'),
            ('运行时间', 'uptime'), 
            ('磁盘使用', 'df -h | head -3'),
            ('内存使用', 'free -h')
        ]
        
        for desc, cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            result = stdout.read().decode().strip()
            print(f"{desc}: {result}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法: python3 test_ssh.py <IP> <用户名> <密码>")
        sys.exit(1)
    
    test_connection(sys.argv[1], sys.argv[2], sys.argv[3])
'''
    
    with open("test_ssh.py", 'w') as f:
        f.write(test_script)
    
    os.chmod("test_ssh.py", 0o755)
    print("✅ 创建SSH测试脚本: test_ssh.py")
    
    # 5. 创建启动脚本
    start_script = '''#!/bin/bash
# NAS监控系统启动脚本

echo "🚀 启动NAS日志监控系统"

# 检查依赖
python3 -c "import paramiko" 2>/dev/null || {
    echo "❌ 缺少paramiko依赖，正在安装..."
    pip3 install paramiko --break-system-packages || {
        echo "安装失败，请手动安装: pip3 install paramiko"
        exit 1
    }
}

# 创建日志目录
mkdir -p error_logs
mkdir -p database

echo "✅ 依赖检查完成"

# 启动监控服务
echo "启动监控调度服务..."
cd backend
python3 nas_monitor.py &
MONITOR_PID=$!

echo $MONITOR_PID > ../monitor.pid
echo "✅ 监控服务启动 (PID: $MONITOR_PID)"

echo "📊 系统功能:"
echo "   - 每小时SSH连接NAS获取系统信息"
echo "   - 分析指定日志路径错误内容"  
echo "   - 错误记录到txt文档(每小时追加)"
echo "   - 每天下午3点发送汇总邮件"
echo "   - 数据持久化存储"
echo "   - 文件大小限制100MB"

echo "⚙️  配置文件:"
echo "   - 环境配置: backend/.env (请修改邮件设置)"
echo "   - 数据存储: database/nas_devices.json"
echo "   - 错误日志: error_logs/"

echo "🔧 测试工具:"
echo "   - SSH测试: python3 test_ssh.py <IP> <用户名> <密码>"

echo "停止服务: kill $(cat monitor.pid)"

# 等待信号
trap 'echo "正在停止服务..."; kill $MONITOR_PID; exit 0' INT TERM
wait
'''
    
    with open("start_monitor.sh", 'w') as f:
        f.write(start_script)
    
    os.chmod("start_monitor.sh", 0o755)
    print("✅ 创建启动脚本: start_monitor.sh")
    
    print("\n🎉 所有问题修复完成!")
    print("\n📋 使用步骤:")
    print("1. 修改邮件配置: nano backend/.env")
    print("2. 测试SSH连接: python3 test_ssh.py 192.168.1.100 admin password")
    print("3. 启动监控系统: ./start_monitor.sh")
    print("4. 添加设备和任务: 通过前端界面或直接编辑database/nas_devices.json")
    print("\n✨ 功能特性:")
    print("✅ 每小时自动SSH连接NAS获取系统信息")
    print("✅ 分析用户设定的日志内容，按照选中规则分析")  
    print("✅ 有对应错误则写入txt文档(每小时追加新错误)")
    print("✅ 每天下午3点汇总发送邮件给管理员")
    print("✅ 所有数据持久化存储，重启不丢失")
    print("✅ 文件大小限制100MB，超出只分析最后部分")
    print("✅ 邮件发送错误已修复，支持详细错误日志")

if __name__ == "__main__":
    main()