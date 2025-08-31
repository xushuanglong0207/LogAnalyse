#!/usr/bin/env python3
"""
定时分析模块API路由
包括NAS设备管理、监控任务管理等
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator
from datetime import datetime, timedelta
import asyncio
import logging

from ...database import get_db
from ...models.monitor import NASDevice, MonitorTask, MonitorLog, DeviceStatus, MonitorStatus
from ...models.user import User
from ...auth.jwt_auth import get_current_user
from ...services.nas_device_manager import NASDeviceManager
from ...services.nas_monitor_generator import NASMonitorScriptGenerator

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

# 全局设备管理器实例
device_manager = NASDeviceManager()


# ==================== Pydantic模型 ====================

class DeviceCreate(BaseModel):
    name: str
    ip_address: str
    ssh_port: int = 22
    ssh_username: str
    ssh_password: str
    description: Optional[str] = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    description: Optional[str] = None
    status: Optional[DeviceStatus] = None


class DeviceResponse(BaseModel):
    id: int
    name: str
    ip_address: str
    ssh_port: int
    ssh_username: str
    description: Optional[str]
    status: DeviceStatus
    last_connected: Optional[datetime]
    script_deployed: bool
    script_version: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class MonitorTaskCreate(BaseModel):
    device_id: int
    name: str
    log_path: str
    rule_ids: List[int]
    email_recipients: List[str]
    email_time: str = "15:00"
    
    @validator('email_time')
    def validate_email_time(cls, v):
        try:
            datetime.strptime(v, '%H:%M')
            return v
        except ValueError:
            raise ValueError('邮件时间格式必须为 HH:MM')


class MonitorTaskUpdate(BaseModel):
    name: Optional[str] = None
    log_path: Optional[str] = None
    rule_ids: Optional[List[int]] = None
    email_recipients: Optional[List[str]] = None
    status: Optional[MonitorStatus] = None
    email_time: Optional[str] = None
    is_active: Optional[bool] = None


class MonitorTaskResponse(BaseModel):
    id: int
    device_id: int
    name: str
    log_path: str
    rule_ids: List[int]
    email_recipients: List[str]
    status: MonitorStatus
    email_time: str
    is_active: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    error_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class SystemInfoResponse(BaseModel):
    hostname: str
    os_info: str
    uptime: str
    disk_usage: str
    memory: str
    cpu_info: str
    kernel: str


class DeviceStatusResponse(BaseModel):
    script_exists: bool
    script_executable: bool
    crontab_configured: bool
    last_run_time: Optional[datetime]
    error_logs_count: int
    monitor_log_exists: bool
    error: Optional[str] = None


class ErrorLogResponse(BaseModel):
    filename: str
    full_path: str
    size: str
    modified_time: str


# ==================== 设备管理API ====================

@router.get("/devices", response_model=List[DeviceResponse])
async def get_devices(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取设备列表"""
    devices = db.query(NASDevice).offset(skip).limit(limit).all()
    return devices


@router.post("/devices", response_model=DeviceResponse)
async def create_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新设备"""
    # 检查IP是否已存在
    existing = db.query(NASDevice).filter(NASDevice.ip_address == device.ip_address).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"IP地址 {device.ip_address} 已被使用"
        )
    
    # 加密密码
    encrypted_password = device_manager.encrypt_password(device.ssh_password)
    
    # 创建设备记录
    db_device = NASDevice(
        name=device.name,
        ip_address=device.ip_address,
        ssh_port=device.ssh_port,
        ssh_username=device.ssh_username,
        ssh_password=encrypted_password,
        description=device.description,
        status=DeviceStatus.INACTIVE,
        created_by=current_user.id
    )
    
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    
    return db_device


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取设备详情"""
    device = db.query(NASDevice).filter(NASDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    return device


@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    device_update: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新设备信息"""
    device = db.query(NASDevice).filter(NASDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 更新字段
    update_data = device_update.dict(exclude_unset=True)
    
    # 如果更新密码，需要加密
    if 'ssh_password' in update_data:
        update_data['ssh_password'] = device_manager.encrypt_password(update_data['ssh_password'])
    
    for key, value in update_data.items():
        setattr(device, key, value)
    
    device.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(device)
    
    return device


@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除设备"""
    device = db.query(NASDevice).filter(NASDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 检查是否有关联的监控任务
    task_count = db.query(MonitorTask).filter(MonitorTask.device_id == device_id).count()
    if task_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"无法删除设备，存在 {task_count} 个关联的监控任务"
        )
    
    db.delete(device)
    db.commit()
    
    return {"message": "设备已删除"}


@router.post("/devices/{device_id}/test-connection")
async def test_device_connection(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """测试设备连接"""
    device = db.query(NASDevice).filter(NASDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 解密密码
    password = device_manager.decrypt_password(device.ssh_password)
    
    # 测试连接
    try:
        success, message = await device_manager.test_connection(
            device.ip_address,
            device.ssh_username,
            password,
            device.ssh_port
        )
        
        # 更新设备状态和最后连接时间
        if success:
            device.status = DeviceStatus.ACTIVE
            device.last_connected = datetime.utcnow()
        else:
            device.status = DeviceStatus.ERROR
        
        db.commit()
        
        return {
            "success": success,
            "message": message,
            "status": device.status.value
        }
        
    except Exception as e:
        logger.error(f"测试连接异常: {str(e)}")
        device.status = DeviceStatus.ERROR
        db.commit()
        
        return {
            "success": False,
            "message": f"连接测试失败: {str(e)}",
            "status": device.status.value
        }


@router.get("/devices/{device_id}/system-info", response_model=SystemInfoResponse)
async def get_device_system_info(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取设备系统信息"""
    device = db.query(NASDevice).filter(NASDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    password = device_manager.decrypt_password(device.ssh_password)
    
    try:
        system_info = await device_manager.get_system_info(
            device.ip_address,
            device.ssh_username,
            password,
            device.ssh_port
        )
        return SystemInfoResponse(**system_info)
        
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取系统信息失败: {str(e)}"
        )


# ==================== 监控任务API ====================

@router.get("/monitor-tasks", response_model=List[MonitorTaskResponse])
async def get_monitor_tasks(
    device_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取监控任务列表"""
    query = db.query(MonitorTask)
    if device_id:
        query = query.filter(MonitorTask.device_id == device_id)
    
    tasks = query.offset(skip).limit(limit).all()
    return tasks


@router.post("/monitor-tasks", response_model=MonitorTaskResponse)
async def create_monitor_task(
    task: MonitorTaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建监控任务"""
    # 检查设备是否存在
    device = db.query(NASDevice).filter(NASDevice.id == task.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 创建监控任务
    db_task = MonitorTask(
        device_id=task.device_id,
        name=task.name,
        log_path=task.log_path,
        rule_ids=task.rule_ids,
        email_recipients=task.email_recipients,
        email_time=task.email_time,
        status=MonitorStatus.PENDING,
        created_by=current_user.id
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # 异步部署监控脚本
    background_tasks.add_task(deploy_monitor_script_task, db_task.id)
    
    return db_task


@router.get("/monitor-tasks/{task_id}", response_model=MonitorTaskResponse)
async def get_monitor_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取监控任务详情"""
    task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="监控任务不存在")
    return task


@router.put("/monitor-tasks/{task_id}", response_model=MonitorTaskResponse)
async def update_monitor_task(
    task_id: int,
    task_update: MonitorTaskUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新监控任务"""
    task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="监控任务不存在")
    
    # 更新字段
    update_data = task_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    
    # 如果更新了关键配置，需要重新部署脚本
    if any(key in update_data for key in ['log_path', 'rule_ids', 'email_recipients']):
        background_tasks.add_task(deploy_monitor_script_task, task.id)
    
    return task


@router.delete("/monitor-tasks/{task_id}")
async def delete_monitor_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除监控任务"""
    task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="监控任务不存在")
    
    # 删除设备上的监控脚本
    try:
        device = task.device
        password = device_manager.decrypt_password(device.ssh_password)
        device_info = {
            'ip': device.ip_address,
            'username': device.ssh_username,
            'password': password,
            'port': device.ssh_port
        }
        await device_manager.remove_monitor_script(device_info)
    except Exception as e:
        logger.warning(f"删除监控脚本失败: {str(e)}")
    
    db.delete(task)
    db.commit()
    
    return {"message": "监控任务已删除"}


@router.get("/devices/{device_id}/monitor-status", response_model=DeviceStatusResponse)
async def get_device_monitor_status(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取设备监控状态"""
    device = db.query(NASDevice).filter(NASDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    password = device_manager.decrypt_password(device.ssh_password)
    device_info = {
        'ip': device.ip_address,
        'username': device.ssh_username,
        'password': password,
        'port': device.ssh_port
    }
    
    try:
        status = await device_manager.check_monitor_status(device_info)
        return DeviceStatusResponse(**status)
    except Exception as e:
        logger.error(f"获取监控状态失败: {str(e)}")
        return DeviceStatusResponse(
            script_exists=False,
            script_executable=False,
            crontab_configured=False,
            error_logs_count=0,
            monitor_log_exists=False,
            error=str(e)
        )


@router.get("/devices/{device_id}/error-logs", response_model=List[ErrorLogResponse])
async def get_device_error_logs(
    device_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取设备错误日志列表"""
    device = db.query(NASDevice).filter(NASDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    password = device_manager.decrypt_password(device.ssh_password)
    device_info = {
        'ip': device.ip_address,
        'username': device.ssh_username,
        'password': password,
        'port': device.ssh_port
    }
    
    try:
        logs = await device_manager.get_error_logs(device_info, limit)
        return [ErrorLogResponse(**log) for log in logs]
    except Exception as e:
        logger.error(f"获取错误日志失败: {str(e)}")
        return []


@router.get("/devices/{device_id}/error-logs/{log_filename}/content")
async def get_error_log_content(
    device_id: int,
    log_filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取错误日志内容"""
    device = db.query(NASDevice).filter(NASDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    password = device_manager.decrypt_password(device.ssh_password)
    device_info = {
        'ip': device.ip_address,
        'username': device.ssh_username,
        'password': password,
        'port': device.ssh_port
    }
    
    try:
        content = await device_manager.download_error_log(device_info, log_filename)
        if content is None:
            raise HTTPException(status_code=404, detail="日志文件不存在")
        
        return {
            "filename": log_filename,
            "content": content,
            "size": len(content)
        }
    except Exception as e:
        logger.error(f"下载日志内容失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"下载日志失败: {str(e)}"
        )


# ==================== 后台任务 ====================

async def deploy_monitor_script_task(task_id: int):
    """部署监控脚本的后台任务"""
    from ...database import SessionLocal
    
    db = SessionLocal()
    try:
        task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
        if not task:
            logger.error(f"监控任务 {task_id} 不存在")
            return
        
        device = task.device
        if not device:
            logger.error(f"监控任务 {task_id} 关联的设备不存在")
            return
        
        # 更新任务状态为部署中
        task.status = MonitorStatus.PENDING
        db.commit()
        
        # 获取规则信息（这里需要根据实际的规则表结构调整）
        # rules = get_rules_by_ids(task.rule_ids, db)
        rules = []  # 临时空列表，需要实际实现
        
        # 准备设备信息
        password = device_manager.decrypt_password(device.ssh_password)
        device_info = {
            'name': device.name,
            'ip': device.ip_address,
            'username': device.ssh_username,
            'password': password,
            'port': device.ssh_port
        }
        
        # 准备监控配置
        monitor_config = {
            'task_name': task.name,
            'log_paths': [task.log_path],
            'rules': rules,
            'email_recipients': task.email_recipients
        }
        
        # 部署脚本
        success, message = await device_manager.deploy_monitor_script(device_info, monitor_config)
        
        if success:
            task.status = MonitorStatus.RUNNING
            device.script_deployed = True
            device.script_version = "1.0.0"
            task.next_run = datetime.utcnow() + timedelta(hours=1)
            logger.info(f"监控脚本部署成功: 任务{task_id}")
        else:
            task.status = MonitorStatus.ERROR
            task.error_count += 1
            logger.error(f"监控脚本部署失败: 任务{task_id} - {message}")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"部署监控脚本异常: 任务{task_id} - {str(e)}")
        try:
            task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
            if task:
                task.status = MonitorStatus.ERROR
                task.error_count += 1
                db.commit()
        except:
            pass
    finally:
        db.close()


# ==================== 邮件服务API ====================

@router.post("/email/test")
async def test_email_service(
    recipients: List[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """测试邮件服务"""
    from ...services.email_service import email_service
    
    try:
        success = await email_service.send_test_email(recipients)
        return {
            "success": success,
            "message": "测试邮件发送成功" if success else "测试邮件发送失败"
        }
    except Exception as e:
        logger.error(f"测试邮件服务失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"邮件服务测试失败: {str(e)}"
        )


@router.post("/email/send-report")
async def send_error_report_manually(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动发送错误报告"""
    from ...services.email_service import email_service
    from ...services.monitor_scheduler import monitor_scheduler
    
    task = db.query(MonitorTask).filter(MonitorTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="监控任务不存在")
    
    if not task.email_recipients:
        raise HTTPException(status_code=400, detail="任务未配置邮件接收者")
    
    try:
        await monitor_scheduler._send_task_report(db, task)
        return {
            "success": True,
            "message": f"错误报告已发送到 {', '.join(task.email_recipients)}"
        }
    except Exception as e:
        logger.error(f"手动发送错误报告失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"发送错误报告失败: {str(e)}"
        )


class EmailConfigResponse(BaseModel):
    smtp_server: str
    smtp_port: int
    sender_email: str
    sender_name: str
    is_configured: bool


@router.get("/email/config", response_model=EmailConfigResponse)
async def get_email_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取邮件配置信息"""
    from ...services.email_service import email_service
    
    return EmailConfigResponse(
        smtp_server=email_service.smtp_server,
        smtp_port=email_service.smtp_port,
        sender_email=email_service.sender_email,
        sender_name=email_service.sender_name,
        is_configured=bool(email_service.smtp_username and email_service.smtp_password)
    )


@router.get("/scheduler/status")
async def get_scheduler_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取调度器状态"""
    from ...services.monitor_scheduler import monitor_scheduler
    
    return {
        "is_running": monitor_scheduler.is_running,
        "scheduled_tasks_count": len(monitor_scheduler.scheduled_tasks),
        "next_daily_report": "每日 15:00",
        "current_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }