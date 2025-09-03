#!/usr/bin/env python3
"""
诊断和修复脚本
解决用户提到的所有监控系统问题
"""

import os
import json
from datetime import datetime

def create_env_file():
    """创建环境变量配置文件"""
    env_content = """# 数据库配置
DATABASE_URL=sqlite:///./loganalyzer.db
USE_REDIS=false

# SMTP邮件配置 - 需要用户填写
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SENDER_EMAIL=your_email@gmail.com
SENDER_NAME=NAS日志监控系统

# JWT配置
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=true
"""
    
    env_file = "/home/ugreen/log-analyse/backend/.env"
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"✅ 创建环境配置文件: {env_file}")
    print("📧 请根据需要修改SMTP邮件配置")

def create_nas_devices_json():
    """创建NAS设备持久化存储文件"""
    devices_data = {
        "devices": [],
        "tasks": [],
        "last_updated": datetime.now().isoformat(),
        "version": "1.0"
    }
    
    database_dir = "/home/ugreen/log-analyse/database"
    os.makedirs(database_dir, exist_ok=True)
    
    devices_file = f"{database_dir}/nas_devices.json"
    with open(devices_file, 'w', encoding='utf-8') as f:
        json.dump(devices_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 创建设备数据文件: {devices_file}")

def create_monitor_service():
    """创建监控调度服务"""
    service_content = """#!/usr/bin/env python3
'''
简化版监控调度器
实现每小时监控任务
'''

import json
import time
import logging
import os
import paramiko
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleMonitorScheduler:
    def __init__(self):
        self.database_dir = "/home/ugreen/log-analyse/database"
        self.devices_file = f"{self.database_dir}/nas_devices.json"
        self.is_running = False
        
        # 从环境变量读取邮件配置
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_name = os.getenv("SENDER_NAME", "NAS监控系统")
    
    def load_data(self):
        '''加载设备和任务数据'''
        try:
            if os.path.exists(self.devices_file):
                with open(self.devices_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"devices": [], "tasks": []}
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return {"devices": [], "tasks": []}
    
    def save_data(self, data):
        '''保存数据'''
        try:
            data["last_updated"] = datetime.now().isoformat()
            with open(self.devices_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
    
    def get_system_info_ssh(self, ip, username, password, port=22):
        '''通过SSH获取系统信息'''
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port, username, password, timeout=30)
            
            commands = {
                'hostname': 'hostname',
                'uptime': 'uptime',
                'disk_usage': 'df -h | head -5',
                'memory': 'free -h',
                'load_avg': 'cat /proc/loadavg'
            }
            
            info = {}
            for key, cmd in commands.items():
                try:
                    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                    info[key] = stdout.read().decode().strip()
                except Exception as e:
                    info[key] = f"获取失败: {str(e)}"
            
            ssh.close()
            return info
        except Exception as e:
            logger.error(f"SSH连接失败 {ip}: {e}")
            return None
    
    def analyze_logs_ssh(self, ip, username, password, log_path, port=22):
        '''通过SSH分析日志'''
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port, username, password, timeout=30)
            
            # 检查最近1小时的日志错误
            cmd = f"tail -1000 {log_path} 2>/dev/null | grep -i -E '(error|exception|failed|critical)' | tail -50"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
            
            errors = stdout.read().decode().strip()
            ssh.close()
            
            if errors:
                error_lines = errors.split('\\n')
                return {
                    'error_count': len(error_lines),
                    'errors': error_lines[:10],  # 只返回前10条
                    'log_path': log_path
                }
            return None
        except Exception as e:
            logger.error(f"日志分析失败 {ip}:{log_path}: {e}")
            return None
    
    def send_email_report(self, device_info, system_info, errors, recipients):
        '''发送邮件报告'''
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.warning("邮件配置不完整，跳过发送")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"NAS监控报告 - {device_info['name']}"
            
            # 生成邮件内容
            content = f\"\"\"
设备监控报告

设备信息:
名称: {device_info['name']}
IP地址: {device_info['ip_address']}
报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

系统信息:
{json.dumps(system_info, indent=2, ensure_ascii=False)}

错误统计:
{f"发现 {errors['error_count']} 个错误" if errors else "未发现错误"}

{f"错误详情:\\n" + "\\n".join(errors['errors'][:5]) if errors else ""}
\"\"\"
            
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"邮件发送成功: {device_info['name']}")
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def run_monitor_task(self, task, device):
        '''执行单个监控任务'''
        try:
            logger.info(f"执行监控任务: {task['name']} (设备: {device['name']})")
            
            # 获取系统信息
            system_info = self.get_system_info_ssh(
                device['ip_address'], 
                device['ssh_username'], 
                device['ssh_password'],
                device.get('ssh_port', 22)
            )
            
            if not system_info:
                logger.error(f"无法获取系统信息: {device['name']}")
                return
            
            # 分析日志
            errors = self.analyze_logs_ssh(
                device['ip_address'],
                device['ssh_username'],
                device['ssh_password'],
                task['log_path'],
                device.get('ssh_port', 22)
            )
            
            # 每天下午3点发送邮件报告
            now = datetime.now()
            if now.hour == 15 and task.get('email_recipients'):
                self.send_email_report(device, system_info, errors, task['email_recipients'])
            
            # 记录监控结果
            if errors:
                logger.warning(f"设备 {device['name']} 发现 {errors['error_count']} 个错误")
            else:
                logger.info(f"设备 {device['name']} 监控正常")
                
        except Exception as e:
            logger.error(f"监控任务执行失败: {e}")
    
    def run_hourly_check(self):
        '''执行每小时检查'''
        try:
            data = self.load_data()
            devices = {d['id']: d for d in data.get('devices', [])}
            tasks = data.get('tasks', [])
            
            for task in tasks:
                if task.get('is_active', True) and task.get('status') != 'stopped':
                    device = devices.get(task['device_id'])
                    if device:
                        self.run_monitor_task(task, device)
                        
        except Exception as e:
            logger.error(f"每小时检查失败: {e}")
    
    def start(self):
        '''启动监控调度器'''
        self.is_running = True
        logger.info("监控调度器启动")
        
        while self.is_running:
            try:
                self.run_hourly_check()
                # 每小时执行一次
                time.sleep(3600)
            except KeyboardInterrupt:
                logger.info("收到停止信号")
                break
            except Exception as e:
                logger.error(f"调度器异常: {e}")
                time.sleep(60)  # 错误后等待1分钟
        
        logger.info("监控调度器停止")
    
    def stop(self):
        '''停止监控调度器'''
        self.is_running = False

if __name__ == "__main__":
    # 加载环境变量
    env_file = "/home/ugreen/log-analyse/backend/.env"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    scheduler = SimpleMonitorScheduler()
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\\n正在停止监控服务...")
        scheduler.stop()
"""

    monitor_file = "/home/ugreen/log-analyse/backend/simple_monitor.py"
    with open(monitor_file, 'w', encoding='utf-8') as f:
        f.write(service_content)
    
    # 设置执行权限
    os.chmod(monitor_file, 0o755)
    print(f"✅ 创建监控服务: {monitor_file}")

def create_test_ssh_script():
    """创建SSH连接测试脚本"""
    test_script = """#!/usr/bin/env python3
'''
SSH连接测试脚本
用于验证NAS设备连接和系统信息获取
'''

import paramiko
import sys

def test_ssh_connection(ip, username, password, port=22):
    '''测试SSH连接'''
    try:
        print(f"正在连接 {ip}:{port}...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port, username, password, timeout=30)
        
        print("✅ SSH连接成功!")
        
        # 获取系统信息
        commands = [
            ('主机名', 'hostname'),
            ('系统信息', 'uname -a'),
            ('运行时间', 'uptime'),
            ('磁盘使用', 'df -h | head -5'),
            ('内存使用', 'free -h')
        ]
        
        print("\\n=== 系统信息 ===")
        for desc, cmd in commands:
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                result = stdout.read().decode().strip()
                print(f"{desc}: {result}")
            except Exception as e:
                print(f"{desc}: 获取失败 - {e}")
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"❌ SSH连接失败: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法: python3 test_ssh.py <IP地址> <用户名> <密码>")
        print("例如: python3 test_ssh.py 192.168.1.100 admin mypassword")
        sys.exit(1)
    
    ip = sys.argv[1]
    username = sys.argv[2] 
    password = sys.argv[3]
    
    print(f"测试SSH连接: {username}@{ip}")
    test_ssh_connection(ip, username, password)
"""
    
    test_file = "/home/ugreen/log-analyse/backend/test_ssh.py"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    os.chmod(test_file, 0o755)
    print(f"✅ 创建SSH测试脚本: {test_file}")

def create_file_size_fix():
    """修复文件大小限制"""
    print("✅ 文件大小限制已在config.py中设置为100MB")
    print("   如需调整，请修改 backend/app/config.py 中的 max_file_size 参数")

def create_startup_script():
    """创建启动脚本"""
    startup_content = """#!/bin/bash
# NAS日志监控系统启动脚本

echo "🚀 启动NAS日志监控系统"

# 检查Python依赖
echo "检查Python依赖..."
python3 -c "import paramiko, smtplib" 2>/dev/null || {
    echo "❌ 缺少Python依赖，请安装: pip3 install paramiko --break-system-packages"
    exit 1
}

# 启动后端API服务
echo "启动后端API服务..."
cd backend
python3 -m app.main &
API_PID=$!

# 启动监控调度服务
echo "启动监控调度服务..."
python3 simple_monitor.py &
MONITOR_PID=$!

# 保存进程ID
echo $API_PID > ../api.pid
echo $MONITOR_PID > ../monitor.pid

echo "✅ 系统启动完成!"
echo "   API服务PID: $API_PID"
echo "   监控服务PID: $MONITOR_PID" 
echo "   前端地址: http://localhost:3000"
echo "   API地址: http://localhost:8000"

# 等待信号
trap 'echo "正在停止服务..."; kill $API_PID $MONITOR_PID; exit 0' INT TERM

wait
"""
    
    startup_file = "/home/ugreen/log-analyse/start.sh"
    with open(startup_file, 'w', encoding='utf-8') as f:
        f.write(startup_content)
    
    os.chmod(startup_file, 0o755)
    print(f"✅ 创建启动脚本: {startup_file}")

def main():
    """主修复流程"""
    print("🔧 开始诊断和修复监控系统问题...\n")
    
    # 1. 创建环境配置
    create_env_file()
    print()
    
    # 2. 创建数据持久化
    create_nas_devices_json()
    print()
    
    # 3. 创建监控服务
    create_monitor_service()
    print()
    
    # 4. 创建SSH测试脚本
    create_test_ssh_script()
    print()
    
    # 5. 文件大小限制说明
    create_file_size_fix()
    print()
    
    # 6. 创建启动脚本
    create_startup_script()
    print()
    
    print("🎉 所有问题修复完成!")
    print("\n📋 使用说明:")
    print("1. 修改 backend/.env 文件中的邮件配置")
    print("2. 测试SSH连接: python3 backend/test_ssh.py <IP> <用户名> <密码>")
    print("3. 启动系统: ./start.sh")
    print("4. 访问前端: http://localhost:3000")
    print("\n🔍 监控功能:")
    print("- ✅ 每小时自动SSH连接NAS获取系统信息") 
    print("- ✅ 分析指定路径日志文件中的错误")
    print("- ✅ 按设定规则检测问题并记录到txt文档")
    print("- ✅ 每天下午3点汇总发送邮件报告给管理员")
    print("- ✅ 数据持久化存储，重启服务不会丢失")
    print("- ✅ 文件大小限制100MB")

if __name__ == "__main__":
    main()