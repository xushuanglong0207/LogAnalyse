#!/usr/bin/env python3
"""
邮件服务
用于发送NAS监控错误报告
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import os
from jinja2 import Template

logger = logging.getLogger(__name__)


class EmailService:
    """邮件服务类"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.sender_email = os.getenv("SENDER_EMAIL", self.smtp_username)
        self.sender_name = os.getenv("SENDER_NAME", "NAS日志监控系统")
    
    async def send_error_report(self, 
                              recipients: List[str],
                              device_info: Dict[str, Any],
                              error_summary: Dict[str, Any],
                              error_logs: List[Dict[str, Any]]) -> bool:
        """
        发送错误报告邮件
        
        Args:
            recipients: 收件人列表
            device_info: 设备信息
            error_summary: 错误摘要统计
            error_logs: 错误日志详情
        
        Returns:
            发送是否成功
        """
        try:
            # 生成邮件内容
            subject = self._generate_email_subject(device_info, error_summary)
            html_body = self._generate_email_body(device_info, error_summary, error_logs)
            
            # 创建邮件消息
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = ", ".join(recipients)
            
            # 添加HTML内容
            html_part = MIMEText(html_body, "html", "utf-8")
            message.attach(html_part)
            
            # 发送邮件
            return await self._send_email(message, recipients)
            
        except Exception as e:
            logger.error(f"发送错误报告邮件失败: {str(e)}")
            return False
    
    def _generate_email_subject(self, device_info: Dict[str, Any], error_summary: Dict[str, Any]) -> str:
        """生成邮件主题"""
        device_name = device_info.get('name', '未知设备')
        total_errors = error_summary.get('total_errors', 0)
        
        if total_errors == 0:
            return f"[NAS监控] {device_name} - 监控正常"
        else:
            return f"[NAS监控] {device_name} - 发现 {total_errors} 个错误"
    
    def _generate_email_body(self, 
                           device_info: Dict[str, Any], 
                           error_summary: Dict[str, Any], 
                           error_logs: List[Dict[str, Any]]) -> str:
        """生成邮件HTML内容"""
        
        template_str = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: 'Microsoft YaHei', 'SimHei', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
        }
        .content {
            padding: 30px;
        }
        .device-info {
            background-color: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .summary-card {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .error-card {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .normal-card {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        .info-label {
            font-weight: bold;
            color: #666;
        }
        .error-details {
            background-color: #f1f3f4;
            border-radius: 4px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            overflow-x: auto;
            max-height: 200px;
            overflow-y: auto;
        }
        .footer {
            background-color: #6c757d;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 12px;
        }
        .timestamp {
            color: #6c757d;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖥️ NAS设备监控报告</h1>
            <p>自动监控系统 - 每日错误报告</p>
        </div>
        
        <div class="content">
            <!-- 设备信息 -->
            <div class="device-info">
                <h3>📊 设备信息</h3>
                <div class="info-row">
                    <span class="info-label">设备名称:</span>
                    <span>{{ device_info.name }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">IP地址:</span>
                    <span>{{ device_info.ip_address }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">SSH用户:</span>
                    <span>{{ device_info.ssh_username }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">监控路径:</span>
                    <span>{{ device_info.log_path }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">报告时间:</span>
                    <span>{{ report_time }}</span>
                </div>
            </div>
            
            {% if error_summary.total_errors == 0 %}
            <!-- 正常状态 -->
            <div class="normal-card">
                <h3>✅ 监控状态正常</h3>
                <p>在过去24小时内，未发现任何错误。系统运行正常。</p>
                <p class="timestamp">最后检查时间: {{ error_summary.last_check_time or '未知' }}</p>
            </div>
            {% else %}
            <!-- 错误摘要 -->
            <div class="summary-card">
                <h3>⚠️ 错误摘要</h3>
                <div class="info-row">
                    <span class="info-label">总错误数:</span>
                    <span><strong>{{ error_summary.total_errors }}</strong></span>
                </div>
                <div class="info-row">
                    <span class="info-label">错误类型数:</span>
                    <span>{{ error_summary.error_types }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">影响的日志文件:</span>
                    <span>{{ error_summary.affected_logs }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">监控周期:</span>
                    <span>{{ error_summary.monitoring_period }}</span>
                </div>
            </div>
            
            <!-- 错误详情 -->
            <h3>🔍 错误详情</h3>
            {% for error_log in error_logs %}
            <div class="error-card">
                <h4>{{ error_log.rule_name }}</h4>
                <p><strong>描述:</strong> {{ error_log.description }}</p>
                <div class="info-row">
                    <span class="info-label">出现次数:</span>
                    <span>{{ error_log.count }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">首次发现:</span>
                    <span>{{ error_log.first_seen }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">最后发现:</span>
                    <span>{{ error_log.last_seen }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">来源文件:</span>
                    <span>{{ error_log.source_file }}</span>
                </div>
                
                {% if error_log.sample_content %}
                <p><strong>示例内容:</strong></p>
                <div class="error-details">{{ error_log.sample_content }}</div>
                {% endif %}
            </div>
            {% endfor %}
            {% endif %}
            
            <!-- 建议操作 -->
            <div class="device-info">
                <h3>💡 建议操作</h3>
                {% if error_summary.total_errors == 0 %}
                <p>✅ 系统运行正常，无需特殊操作。</p>
                <p>✅ 继续保持定期监控。</p>
                {% else %}
                <p>⚠️ 建议立即检查出错的日志文件。</p>
                <p>⚠️ 根据错误类型采取相应的修复措施。</p>
                <p>⚠️ 如果错误持续出现，请考虑调整监控规则。</p>
                {% endif %}
            </div>
        </div>
        
        <div class="footer">
            <p>此邮件由 NAS日志监控系统 自动发送</p>
            <p>如有问题，请联系系统管理员</p>
            <p class="timestamp">发送时间: {{ current_time }}</p>
        </div>
    </div>
</body>
</html>
        """
        
        # 准备模板数据
        template_data = {
            'device_info': device_info,
            'error_summary': error_summary,
            'error_logs': error_logs,
            'report_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 渲染模板
        template = Template(template_str)
        return template.render(**template_data)
    
    async def _send_email(self, message: MIMEMultipart, recipients: List[str]) -> bool:
        """发送邮件"""
        try:
            # 创建SSL上下文
            context = ssl.create_default_context()
            
            # 连接SMTP服务器
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)
                
                # 发送邮件
                text = message.as_string()
                server.sendmail(self.sender_email, recipients, text)
                
                logger.info(f"邮件发送成功，收件人: {', '.join(recipients)}")
                return True
                
        except Exception as e:
            logger.error(f"SMTP发送邮件失败: {str(e)}")
            return False
    
    async def send_test_email(self, recipients: List[str]) -> bool:
        """发送测试邮件"""
        try:
            message = MIMEMultipart()
            message["Subject"] = "[NAS监控] 邮件服务测试"
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = ", ".join(recipients)
            
            body = f"""
            <html>
            <body>
                <h2>NAS监控系统邮件服务测试</h2>
                <p>如果您收到这封邮件，说明邮件服务配置正确。</p>
                <p>测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>SMTP服务器: {self.smtp_server}:{self.smtp_port}</p>
                <p>发送者: {self.sender_email}</p>
            </body>
            </html>
            """
            
            html_part = MIMEText(body, "html", "utf-8")
            message.attach(html_part)
            
            return await self._send_email(message, recipients)
            
        except Exception as e:
            logger.error(f"发送测试邮件失败: {str(e)}")
            return False


# 全局邮件服务实例
email_service = EmailService()