#!/usr/bin/env python3
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
