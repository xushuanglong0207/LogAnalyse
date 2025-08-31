#!/usr/bin/env python3
"""
NAS设备SSH连接和脚本部署服务
"""

import asyncio
import asyncssh
import tempfile
import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
from .nas_monitor_generator import NASMonitorScriptGenerator

logger = logging.getLogger(__name__)


class SSHConnectionError(Exception):
    """SSH连接错误"""
    pass


class ScriptDeploymentError(Exception):
    """脚本部署错误"""
    pass


class NASDeviceManager:
    """NAS设备管理器"""
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        初始化设备管理器
        
        Args:
            encryption_key: 用于加密设备密码的密钥
        """
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        self.script_generator = NASMonitorScriptGenerator()
        self.connection_timeout = 30
        self.command_timeout = 120
    
    def encrypt_password(self, password: str) -> bytes:
        """加密密码"""
        return self.cipher.encrypt(password.encode())
    
    def decrypt_password(self, encrypted_password: bytes) -> str:
        """解密密码"""
        return self.cipher.decrypt(encrypted_password).decode()
    
    async def test_connection(self, ip_address: str, username: str, password: str, port: int = 22) -> Tuple[bool, str]:
        """
        测试SSH连接
        
        Returns:
            (连接是否成功, 错误信息或成功信息)
        """
        try:
            async with asyncssh.connect(
                host=ip_address,
                port=port,
                username=username,
                password=password,
                known_hosts=None,
                server_host_key_algs=['ssh-rsa', 'ecdsa-sha2-nistp256', 'ssh-ed25519'],
                connect_timeout=self.connection_timeout
            ) as conn:
                # 执行简单命令测试连接
                result = await conn.run('echo "Connection test successful"', timeout=10)
                return True, f"连接成功: {result.stdout.strip()}"
                
        except asyncssh.Error as e:
            logger.error(f"SSH连接失败 {ip_address}: {str(e)}")
            return False, f"SSH连接失败: {str(e)}"
        except asyncio.TimeoutError:
            logger.error(f"SSH连接超时 {ip_address}")
            return False, "连接超时"
        except Exception as e:
            logger.error(f"连接测试异常 {ip_address}: {str(e)}")
            return False, f"连接异常: {str(e)}"
    
    async def get_system_info(self, ip_address: str, username: str, password: str, port: int = 22) -> Dict[str, Any]:
        """
        获取系统信息
        
        Returns:
            系统信息字典
        """
        try:
            async with asyncssh.connect(
                host=ip_address,
                port=port,
                username=username,
                password=password,
                known_hosts=None,
                server_host_key_algs=['ssh-rsa', 'ecdsa-sha2-nistp256', 'ssh-ed25519'],
                connect_timeout=self.connection_timeout
            ) as conn:
                # 获取系统信息的命令
                commands = {
                    'hostname': 'hostname',
                    'os_info': 'cat /etc/os-release | head -n 2',
                    'uptime': 'uptime',
                    'disk_usage': 'df -h | head -n 5',
                    'memory': 'free -h',
                    'cpu_info': 'cat /proc/cpuinfo | grep "model name" | head -n 1 | cut -d: -f2',
                    'kernel': 'uname -r'
                }
                
                system_info = {}
                for key, command in commands.items():
                    try:
                        result = await conn.run(command, timeout=15)
                        system_info[key] = result.stdout.strip()
                    except Exception as e:
                        system_info[key] = f"获取失败: {str(e)}"
                
                return system_info
                
        except Exception as e:
            logger.error(f"获取系统信息失败 {ip_address}: {str(e)}")
            raise SSHConnectionError(f"获取系统信息失败: {str(e)}")
    
    async def deploy_monitor_script(self, 
                                   device_info: Dict[str, Any],
                                   monitor_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        部署监控脚本到NAS设备
        
        Args:
            device_info: 设备信息 {'ip': '', 'username': '', 'password': '', 'port': 22}
            monitor_config: 监控配置 {
                'task_name': '',
                'log_paths': [],
                'rules': [],
                'email_recipients': []
            }
        
        Returns:
            (部署是否成功, 消息)
        """
        ip_address = device_info['ip']
        username = device_info['username']
        password = device_info['password']
        port = device_info.get('port', 22)
        
        try:
            # 生成监控脚本
            script_content = self.script_generator.generate_monitor_script(
                task_name=monitor_config['task_name'],
                log_paths=monitor_config['log_paths'],
                rules=monitor_config['rules'],
                email_recipients=monitor_config['email_recipients'],
                device_info={
                    'name': device_info.get('name', 'Unknown'),
                    'ip': ip_address,
                    'username': username,
                    'password': password
                }
            )
            
            async with asyncssh.connect(
                host=ip_address,
                port=port,
                username=username,
                password=password,
                known_hosts=None,
                server_host_key_algs=['ssh-rsa', 'ecdsa-sha2-nistp256', 'ssh-ed25519'],
                connect_timeout=self.connection_timeout
            ) as conn:
                
                remote_dir = f"/home/{username}/nas-log-monitor"
                script_name = "nas-log-monitor.sh"
                remote_script_path = f"{remote_dir}/{script_name}"
                
                # 1. 创建监控目录
                logger.info(f"在设备 {ip_address} 创建监控目录: {remote_dir}")
                result = await conn.run(f"mkdir -p {remote_dir}", timeout=30)
                if result.exit_status != 0:
                    raise ScriptDeploymentError(f"创建目录失败: {result.stderr}")
                
                # 2. 创建临时脚本文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as tmp_file:
                    tmp_file.write(script_content)
                    tmp_file.flush()
                    temp_script_path = tmp_file.name
                
                try:
                    # 3. 上传脚本文件
                    logger.info(f"上传监控脚本到 {ip_address}:{remote_script_path}")
                    await asyncssh.scp(temp_script_path, (conn, remote_script_path))
                    
                    # 4. 设置执行权限
                    result = await conn.run(f"chmod +x {remote_script_path}", timeout=30)
                    if result.exit_status != 0:
                        raise ScriptDeploymentError(f"设置执行权限失败: {result.stderr}")
                    
                    # 5. 设置crontab任务
                    cron_command = f"0 * * * * {remote_script_path} >> /var/log/nas-monitor.log 2>&1"
                    crontab_setup = f'''
(crontab -l 2>/dev/null | grep -v "{remote_script_path}" || true; echo "{cron_command}") | crontab -
'''
                    result = await conn.run(crontab_setup, timeout=30)
                    if result.exit_status != 0:
                        logger.warning(f"设置crontab可能失败: {result.stderr}")
                    
                    # 6. 验证部署
                    result = await conn.run(f"ls -la {remote_script_path}", timeout=15)
                    if result.exit_status != 0:
                        raise ScriptDeploymentError("脚本文件验证失败")
                    
                    # 7. 测试脚本执行（不执行实际监控，只验证语法）
                    result = await conn.run(f"bash -n {remote_script_path}", timeout=15)
                    if result.exit_status != 0:
                        logger.warning(f"脚本语法检查警告: {result.stderr}")
                    
                    logger.info(f"监控脚本成功部署到 {ip_address}")
                    return True, f"监控脚本已成功部署到 {remote_script_path}\\n" + \\
                                f"Crontab任务已配置，每小时执行一次监控\\n" + \\
                                f"日志文件位置: /var/log/nas-monitor.log"
                    
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(temp_script_path)
                    except:
                        pass
                
        except asyncssh.Error as e:
            logger.error(f"SSH连接失败 {ip_address}: {str(e)}")
            return False, f"SSH连接失败: {str(e)}"
        except Exception as e:
            logger.error(f"脚本部署失败 {ip_address}: {str(e)}")
            return False, f"部署失败: {str(e)}"
    
    async def check_monitor_status(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查监控脚本状态
        
        Returns:
            状态信息字典
        """
        ip_address = device_info['ip']
        username = device_info['username']
        password = device_info['password']
        port = device_info.get('port', 22)
        
        try:
            async with asyncssh.connect(
                host=ip_address,
                port=port,
                username=username,
                password=password,
                known_hosts=None,
                server_host_key_algs=['ssh-rsa', 'ecdsa-sha2-nistp256', 'ssh-ed25519'],
                connect_timeout=self.connection_timeout
            ) as conn:
                
                remote_dir = f"/home/{username}/nas-log-monitor"
                script_path = f"{remote_dir}/nas-log-monitor.sh"
                
                status = {
                    'script_exists': False,
                    'script_executable': False,
                    'crontab_configured': False,
                    'last_run_time': None,
                    'error_logs_count': 0,
                    'monitor_log_exists': False
                }
                
                # 检查脚本文件是否存在
                result = await conn.run(f"ls -la {script_path}", timeout=15)
                if result.exit_status == 0:
                    status['script_exists'] = True
                    # 检查执行权限
                    if 'x' in result.stdout:
                        status['script_executable'] = True
                
                # 检查crontab配置
                result = await conn.run("crontab -l", timeout=15)
                if result.exit_status == 0 and script_path in result.stdout:
                    status['crontab_configured'] = True
                
                # 检查监控日志文件
                result = await conn.run("ls -la /var/log/nas-monitor.log", timeout=15)
                if result.exit_status == 0:
                    status['monitor_log_exists'] = True
                    # 获取最后修改时间
                    result = await conn.run("stat -c %Y /var/log/nas-monitor.log", timeout=15)
                    if result.exit_status == 0:
                        try:
                            timestamp = int(result.stdout.strip())
                            status['last_run_time'] = datetime.fromtimestamp(timestamp)
                        except:
                            pass
                
                # 检查错误日志文件数量
                result = await conn.run(f"ls {remote_dir}/error-log-*.log 2>/dev/null | wc -l", timeout=15)
                if result.exit_status == 0:
                    try:
                        status['error_logs_count'] = int(result.stdout.strip())
                    except:
                        pass
                
                return status
                
        except Exception as e:
            logger.error(f"检查监控状态失败 {ip_address}: {str(e)}")
            return {'error': str(e)}
    
    async def get_error_logs(self, device_info: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取错误日志列表
        
        Returns:
            错误日志信息列表
        """
        ip_address = device_info['ip']
        username = device_info['username']
        password = device_info['password']
        port = device_info.get('port', 22)
        
        try:
            async with asyncssh.connect(
                host=ip_address,
                port=port,
                username=username,
                password=password,
                known_hosts=None,
                server_host_key_algs=['ssh-rsa', 'ecdsa-sha2-nistp256', 'ssh-ed25519'],
                connect_timeout=self.connection_timeout
            ) as conn:
                
                remote_dir = f"/home/{username}/nas-log-monitor"
                
                # 获取错误日志文件列表
                result = await conn.run(
                    f"ls -lt {remote_dir}/error-log-*.log 2>/dev/null | head -n {limit}",
                    timeout=30
                )
                
                if result.exit_status != 0:
                    return []
                
                logs = []
                for line in result.stdout.strip().split('\\n'):
                    if not line or not line.startswith('-'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 9:
                        filename = parts[-1]
                        file_size = parts[4]
                        modified_time = ' '.join(parts[5:8])
                        
                        logs.append({
                            'filename': os.path.basename(filename),
                            'full_path': filename,
                            'size': file_size,
                            'modified_time': modified_time
                        })
                
                return logs
                
        except Exception as e:
            logger.error(f"获取错误日志失败 {ip_address}: {str(e)}")
            return []
    
    async def download_error_log(self, device_info: Dict[str, Any], log_filename: str) -> Optional[str]:
        """
        下载错误日志内容
        
        Returns:
            日志内容字符串，失败返回None
        """
        ip_address = device_info['ip']
        username = device_info['username']
        password = device_info['password']
        port = device_info.get('port', 22)
        
        try:
            async with asyncssh.connect(
                host=ip_address,
                port=port,
                username=username,
                password=password,
                known_hosts=None,
                server_host_key_algs=['ssh-rsa', 'ecdsa-sha2-nistp256', 'ssh-ed25519'],
                connect_timeout=self.connection_timeout
            ) as conn:
                
                remote_dir = f"/home/{username}/nas-log-monitor"
                log_path = f"{remote_dir}/{log_filename}"
                
                # 下载日志文件内容
                result = await conn.run(f"cat {log_path}", timeout=60)
                if result.exit_status == 0:
                    return result.stdout
                else:
                    logger.error(f"下载日志失败: {result.stderr}")
                    return None
                
        except Exception as e:
            logger.error(f"下载错误日志失败 {ip_address}: {str(e)}")
            return None
    
    async def remove_monitor_script(self, device_info: Dict[str, Any]) -> Tuple[bool, str]:
        """
        移除监控脚本和相关配置
        
        Returns:
            (操作是否成功, 消息)
        """
        ip_address = device_info['ip']
        username = device_info['username']
        password = device_info['password']
        port = device_info.get('port', 22)
        
        try:
            async with asyncssh.connect(
                host=ip_address,
                port=port,
                username=username,
                password=password,
                known_hosts=None,
                server_host_key_algs=['ssh-rsa', 'ecdsa-sha2-nistp256', 'ssh-ed25519'],
                connect_timeout=self.connection_timeout
            ) as conn:
                
                remote_dir = f"/home/{username}/nas-log-monitor"
                script_path = f"{remote_dir}/nas-log-monitor.sh"
                
                # 移除crontab任务
                result = await conn.run(
                    f'crontab -l 2>/dev/null | grep -v "{script_path}" | crontab -',
                    timeout=30
                )
                
                # 删除监控目录（确认操作）
                result = await conn.run(f"rm -rf {remote_dir}", timeout=30)
                if result.exit_status != 0:
                    logger.warning(f"删除监控目录可能失败: {result.stderr}")
                
                return True, "监控脚本和相关配置已成功移除"
                
        except Exception as e:
            logger.error(f"移除监控脚本失败 {ip_address}: {str(e)}")
            return False, f"移除失败: {str(e)}"


# 使用示例
async def main():
    """测试示例"""
    manager = NASDeviceManager()
    
    device_info = {
        'name': '测试NAS',
        'ip': '192.168.1.100',
        'username': 'admin',
        'password': 'password123',
        'port': 22
    }
    
    # 测试连接
    success, message = await manager.test_connection(
        device_info['ip'],
        device_info['username'],
        device_info['password'],
        device_info['port']
    )
    print(f"连接测试: {success} - {message}")
    
    if success:
        # 获取系统信息
        try:
            sys_info = await manager.get_system_info(
                device_info['ip'],
                device_info['username'],
                device_info['password'],
                device_info['port']
            )
            print("系统信息:")
            for key, value in sys_info.items():
                print(f"  {key}: {value}")
        except Exception as e:
            print(f"获取系统信息失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())