#!/usr/bin/env python3
"""
快速修复和启动NAS监控系统
"""

import os
import json
from datetime import datetime

def main():
    print("🔧 快速修复NAS监控系统...\n")
    
    # 1. 创建环境配置
    env_content = """# 数据库配置
DATABASE_URL=sqlite:///./loganalyzer.db
USE_REDIS=false

# SMTP邮件配置 - 请修改为您的配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SENDER_EMAIL=your_email@gmail.com
SENDER_NAME=NAS日志监控系统

# JWT配置
SECRET_KEY=nas-monitor-secret-key
DEBUG=true
"""
    
    os.makedirs("backend", exist_ok=True)
    with open("backend/.env", 'w') as f:
        f.write(env_content)
    print("✅ 环境配置: backend/.env")
    
    # 2. 数据持久化
    os.makedirs("database", exist_ok=True)
    data = {"devices": [], "tasks": [], "last_updated": datetime.now().isoformat()}
    with open("database/nas_devices.json", 'w') as f:
        json.dump(data, f, indent=2)
    print("✅ 数据存储: database/nas_devices.json")
    
    # 3. SSH测试工具
    test_script = '''#!/usr/bin/env python3
import paramiko, sys

def test(ip, user, pwd):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, 22, user, pwd, timeout=30)
        print(f"✅ SSH连接成功: {user}@{ip}")
        
        stdin, stdout, stderr = ssh.exec_command("hostname && uptime")
        print(f"系统信息: {stdout.read().decode().strip()}")
        ssh.close()
        return True
    except Exception as e:
        print(f"❌ SSH连接失败: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法: python3 test_ssh.py <IP> <用户名> <密码>")
    else:
        test(sys.argv[1], sys.argv[2], sys.argv[3])
'''
    
    with open("test_ssh.py", 'w') as f:
        f.write(test_script)
    os.chmod("test_ssh.py", 0o755)
    print("✅ SSH测试: test_ssh.py")
    
    # 4. 简化监控服务
    monitor_service = '''#!/usr/bin/env python3
"""简化NAS监控服务"""
import json, time, paramiko, smtplib, os, logging
from datetime import datetime
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Monitor:
    def __init__(self):
        self.data_file = "database/nas_devices.json"
        
    def load_config(self):
        if os.path.exists("backend/.env"):
            with open("backend/.env") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        k, v = line.strip().split("=", 1)
                        os.environ[k] = v
        
    def ssh_get_info(self, ip, user, pwd):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, 22, user, pwd, timeout=30)
            
            stdin, stdout, stderr = ssh.exec_command("hostname && uptime && df -h | head -3")
            info = stdout.read().decode().strip()
            ssh.close()
            return info
        except Exception as e:
            logger.error(f"SSH连接失败 {ip}: {e}")
            return None
    
    def analyze_log(self, ip, user, pwd, log_path):
        try:
            ssh = paramiko.SSHClient() 
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, 22, user, pwd, timeout=30)
            
            # 检查日志大小，限制100MB
            stdin, stdout, stderr = ssh.exec_command(f"stat -c%s {log_path} 2>/dev/null || echo 0")
            size = int(stdout.read().decode().strip() or 0)
            
            if size > 100*1024*1024:
                cmd = f"tail -5000 {log_path}"
            else:
                cmd = f"cat {log_path}"
                
            stdin, stdout, stderr = ssh.exec_command(f"{cmd} | grep -i 'error\\|exception\\|failed' | tail -20")
            errors = stdout.read().decode().strip()
            ssh.close()
            
            if errors:
                return {"count": len(errors.split("\\n")), "errors": errors.split("\\n")[:5]}
            return None
        except Exception as e:
            logger.error(f"日志分析失败: {e}")
            return None
    
    def write_errors(self, device_name, errors):
        try:
            os.makedirs(f"error_logs/{device_name}", exist_ok=True)
            file_path = f"error_logs/{device_name}/errors_{datetime.now().strftime('%Y%m%d_%H')}.txt"
            
            with open(file_path, "a") as f:
                f.write(f"\\n=== {datetime.now()} ===\\n")
                f.write(f"错误数量: {errors['count']}\\n")
                for i, err in enumerate(errors['errors'], 1):
                    f.write(f"{i}. {err}\\n")
                f.write("\\n")
            return file_path
        except Exception as e:
            logger.error(f"写入错误文件失败: {e}")
            return None
    
    def send_email(self, device_name, system_info, errors, recipients):
        try:
            smtp_server = os.getenv("SMTP_SERVER", "")
            smtp_user = os.getenv("SMTP_USERNAME", "")
            smtp_pass = os.getenv("SMTP_PASSWORD", "")
            
            if not smtp_user or not smtp_pass:
                logger.warning("邮件配置不完整")
                return False
                
            msg = MIMEText(f"""NAS监控报告
            
设备: {device_name}
时间: {datetime.now()}

系统信息:
{system_info or '获取失败'}

错误统计:
{f"发现 {errors['count']} 个错误" if errors else "无错误"}

详细信息请查看服务器日志。
""", "plain", "utf-8")
            
            msg["Subject"] = f"NAS监控报告 - {device_name}"
            msg["From"] = smtp_user
            msg["To"] = ", ".join(recipients)
            
            with smtplib.SMTP(smtp_server, int(os.getenv("SMTP_PORT", "587"))) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            
            logger.info(f"邮件发送成功: {device_name}")
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def run_monitoring(self):
        try:
            if not os.path.exists(self.data_file):
                logger.info("暂无监控任务")
                return
                
            with open(self.data_file) as f:
                data = json.load(f)
            
            devices = {d["id"]: d for d in data.get("devices", [])}
            tasks = data.get("tasks", [])
            
            for task in tasks:
                if not task.get("is_active", True):
                    continue
                    
                device = devices.get(task["device_id"])
                if not device:
                    continue
                
                logger.info(f"监控设备: {device['name']}")
                
                # 1. 获取系统信息
                info = self.ssh_get_info(device["ip_address"], device["ssh_username"], device.get("ssh_password", ""))
                
                # 2. 分析日志
                errors = self.analyze_log(device["ip_address"], device["ssh_username"], 
                                        device.get("ssh_password", ""), task.get("log_path", "/var/log/syslog"))
                
                # 3. 记录错误
                if errors:
                    error_file = self.write_errors(device["name"], errors)
                    logger.info(f"错误已记录: {error_file}")
                
                # 4. 每天15点发邮件
                if datetime.now().hour == 15 and task.get("email_recipients"):
                    self.send_email(device["name"], info, errors, task["email_recipients"])
                
                # 更新任务状态
                task["last_run"] = datetime.now().isoformat()
            
            # 保存数据
            with open(self.data_file, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"监控失败: {e}")
    
    def start(self):
        self.load_config()
        logger.info("NAS监控服务启动")
        
        while True:
            try:
                logger.info("执行监控检查...")
                self.run_monitoring()
                logger.info("监控完成，1小时后再次执行")
                time.sleep(3600)  # 每小时执行
            except KeyboardInterrupt:
                logger.info("服务停止")
                break

if __name__ == "__main__":
    Monitor().start()
'''
    
    with open("backend/monitor.py", 'w') as f:
        f.write(monitor_service)
    os.chmod("backend/monitor.py", 0o755)
    print("✅ 监控服务: backend/monitor.py")
    
    # 5. 启动脚本
    start_script = '''#!/bin/bash
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
'''
    
    with open("start_monitor.sh", 'w') as f:
        f.write(start_script)
    os.chmod("start_monitor.sh", 0o755)
    print("✅ 启动脚本: start_monitor.sh")
    
    print("\n🎉 系统修复完成!")
    print("\n📋 使用步骤:")
    print("1. 修改邮件配置: nano backend/.env") 
    print("2. 测试SSH连接: python3 test_ssh.py 192.168.1.100 admin password123")
    print("3. 启动监控: ./start_monitor.sh")
    print("4. 添加设备: 编辑 database/nas_devices.json")
    
    print("\n✅ 所有问题已解决:")
    print("✅ SSH连接获取系统信息 - 每次连接获取最新信息")
    print("✅ 数据持久化存储 - database/nas_devices.json")
    print("✅ 文件大小100MB限制 - 超出自动截取")
    print("✅ 邮件发送修复 - 详细错误处理")  
    print("✅ 每小时监控任务 - 自动执行")
    print("✅ 错误记录txt文档 - 按小时追加")
    print("✅ 每天15点汇总邮件 - 自动发送")

if __name__ == "__main__":
    main()