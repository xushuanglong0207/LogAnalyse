import os
import socket
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


def get_local_ip() -> str:
    """自动获取本机IPv4地址"""
    try:
        # 创建一个UDP socket连接到外部地址来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # 如果无法连接外网，尝试获取localhost的IP
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip != "127.0.0.1":
                return ip
        except Exception:
            pass
        
        # 最后回退到localhost
        return "127.0.0.1"


def get_all_local_ips() -> List[str]:
    """获取所有可用的本机IP地址"""
    ips = ["localhost", "127.0.0.1"]
    
    try:
        # 获取主机名对应的IP
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)
        if host_ip not in ips:
            ips.append(host_ip)
    except Exception:
        pass
    
    try:
        # 获取所有网络接口的IP地址
        import socket
        import subprocess
        import platform
        
        if platform.system() == "Windows":
            # Windows系统使用ipconfig
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'IPv4' in line and ':' in line:
                    ip = line.split(':')[1].strip()
                    if ip and ip not in ips and not ip.startswith('169.254'):
                        ips.append(ip)
        else:
            # Linux/Mac系统使用hostname -I
            result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            if result.returncode == 0:
                local_ips = result.stdout.strip().split()
                for ip in local_ips:
                    if ip not in ips and not ip.startswith('169.254'):
                        ips.append(ip)
    except Exception:
        pass
    
    # 添加自动检测的主要IP
    main_ip = get_local_ip()
    if main_ip not in ips:
        ips.append(main_ip)
    
    return ips


class Settings(BaseSettings):
    # 数据库配置 - 使用SQLite替换PostgreSQL
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./loganalyzer.db")
    
    # Redis配置 - 可选
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    use_redis: bool = os.getenv("USE_REDIS", "False").lower() == "true"
    
    # JWT配置
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # 文件上传配置 - 修复100MB限制
    upload_dir: str = "uploads"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_file_types: list = [".txt", ".json", ".log", ".csv"]
    
    # SMTP邮件配置
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    sender_email: str = os.getenv("SENDER_EMAIL", "")
    sender_name: str = os.getenv("SENDER_NAME", "NAS日志监控系统")
    
    # 应用配置
    app_name: str = "日志分析平台"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # 网络配置 - 自动识别IPv4地址
    local_ip: str = get_local_ip()
    all_local_ips: List[str] = get_all_local_ips()
    
    # CORS配置 - 自动包含所有本地IP地址
    @property
    def allowed_origins(self) -> List[str]:
        origins = []
        for ip in self.all_local_ips:
            origins.extend([
                f"http://{ip}:3000",
                f"https://{ip}:3000",
                f"http://{ip}:3001",  # 开发环境备用端口
            ])
        
        # 添加常用的开发地址
        origins.extend([
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://0.0.0.0:3000",
        ])
        
        # 去重并返回
        return list(set(origins))
    
    class Config:
        env_file = ".env"
    
    def get_frontend_urls(self) -> List[str]:
        """获取前端可访问的URL列表"""
        urls = []
        for ip in self.all_local_ips:
            if ip not in ["localhost", "127.0.0.1"]:
                urls.append(f"http://{ip}:3000")
        
        # 添加默认地址
        urls.extend([
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ])
        
        return urls
    
    def get_api_urls(self) -> List[str]:
        """获取API可访问的URL列表"""
        urls = []
        for ip in self.all_local_ips:
            if ip not in ["localhost", "127.0.0.1"]:
                urls.append(f"http://{ip}:8000")
        
        # 添加默认地址
        urls.extend([
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ])
        
        return urls


@lru_cache()
def get_settings():
    return Settings() 