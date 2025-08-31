from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from ..database import Base


class DeviceStatus(PyEnum):
    """设备状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DEPLOYING = "deploying"


class MonitorStatus(PyEnum):
    """监控状态枚举"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    PENDING = "pending"


class NASDevice(Base):
    """NAS设备模型"""
    __tablename__ = "nas_devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="设备名称")
    ip_address = Column(String(45), nullable=False, comment="IP地址")
    ssh_port = Column(Integer, default=22, comment="SSH端口")
    ssh_username = Column(String(50), nullable=False, comment="SSH用户名")
    ssh_password = Column(String(255), nullable=False, comment="SSH密码(加密存储)")
    description = Column(Text, comment="设备描述")
    status = Column(Enum(DeviceStatus), default=DeviceStatus.INACTIVE, comment="设备状态")
    last_connected = Column(DateTime(timezone=True), comment="最后连接时间")
    script_deployed = Column(Boolean, default=False, comment="监控脚本是否已部署")
    script_version = Column(String(20), comment="脚本版本")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    
    # 关系
    creator = relationship("User")
    monitor_tasks = relationship("MonitorTask", back_populates="device")
    monitor_logs = relationship("MonitorLog", back_populates="device")

    def __repr__(self):
        return f"<NASDevice(id={self.id}, name='{self.name}', ip='{self.ip_address}')>"


class MonitorTask(Base):
    """监控任务模型"""
    __tablename__ = "monitor_tasks"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("nas_devices.id"), nullable=False, comment="设备ID")
    name = Column(String(100), nullable=False, comment="任务名称")
    log_path = Column(String(500), nullable=False, comment="监控的日志路径")
    rule_ids = Column(JSON, comment="使用的规则ID列表")
    email_recipients = Column(JSON, comment="邮件接收者列表")
    status = Column(Enum(MonitorStatus), default=MonitorStatus.STOPPED, comment="监控状态")
    cron_expression = Column(String(100), default="0 * * * *", comment="定时表达式(默认每小时)")
    email_time = Column(String(5), default="15:00", comment="邮件发送时间")
    is_active = Column(Boolean, default=True, comment="是否激活")
    last_run = Column(DateTime(timezone=True), comment="最后执行时间")
    next_run = Column(DateTime(timezone=True), comment="下次执行时间")
    error_count = Column(Integer, default=0, comment="错误计数")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    
    # 关系
    device = relationship("NASDevice", back_populates="monitor_tasks")
    creator = relationship("User")
    monitor_logs = relationship("MonitorLog", back_populates="task")

    def __repr__(self):
        return f"<MonitorTask(id={self.id}, name='{self.name}', device_id={self.device_id})>"


class MonitorLog(Base):
    """监控日志模型"""
    __tablename__ = "monitor_logs"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("nas_devices.id"), nullable=False, comment="设备ID")
    task_id = Column(Integer, ForeignKey("monitor_tasks.id"), nullable=False, comment="任务ID")
    log_file = Column(String(200), nullable=False, comment="错误日志文件名")
    error_count = Column(Integer, default=0, comment="错误总数")
    error_summary = Column(JSON, comment="错误摘要信息")
    email_sent = Column(Boolean, default=False, comment="是否已发送邮件")
    email_sent_at = Column(DateTime(timezone=True), comment="邮件发送时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    
    # 关系
    device = relationship("NASDevice", back_populates="monitor_logs")
    task = relationship("MonitorTask", back_populates="monitor_logs")

    def __repr__(self):
        return f"<MonitorLog(id={self.id}, device_id={self.device_id}, error_count={self.error_count})>"


class EmailTemplate(Base):
    """邮件模板模型"""
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="模板名称")
    subject = Column(String(200), nullable=False, comment="邮件主题")
    content = Column(Text, nullable=False, comment="邮件内容模板")
    is_default = Column(Boolean, default=False, comment="是否为默认模板")
    variables = Column(JSON, comment="模板变量说明")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    
    # 关系
    creator = relationship("User")

    def __repr__(self):
        return f"<EmailTemplate(id={self.id}, name='{self.name}')>"