#!/usr/bin/env python3
"""
定时任务调度服务
处理NAS监控的定时任务，包括每日下午3点发送错误报告邮件
"""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import SessionLocal
from ..models.monitor import NASDevice, MonitorTask, MonitorLog, MonitorStatus, DeviceStatus
from ..models.detection_rule import DetectionRule
from ..services.email_service import email_service
from ..services.nas_device_manager import NASDeviceManager

logger = logging.getLogger(__name__)


class MonitorScheduler:
    """监控调度器"""
    
    def __init__(self):
        self.device_manager = NASDeviceManager()
        self.is_running = False
        self.scheduled_tasks = {}
    
    async def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已经在运行中")
            return
        
        self.is_running = True
        logger.info("监控调度器启动")
        
        # 启动主循环
        await self._run_scheduler()
    
    async def stop(self):
        """停止调度器"""
        self.is_running = False
        logger.info("监控调度器停止")
    
    async def _run_scheduler(self):
        """运行调度器主循环"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # 检查是否到了发送邮件的时间（每日下午3点）
                if self._should_send_daily_report(current_time):
                    await self._send_daily_reports()
                
                # 检查监控任务状态
                await self._check_monitor_tasks()
                
                # 每分钟检查一次
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"调度器运行异常: {str(e)}")
                await asyncio.sleep(60)
    
    def _should_send_daily_report(self, current_time: datetime) -> bool:
        """检查是否应该发送每日报告"""
        # 检查是否是下午3点（15:00）
        target_time = time(15, 0)  # 下午3点
        current_time_obj = current_time.time()
        
        # 检查是否在目标时间的1分钟内
        target_start = time(15, 0, 0)
        target_end = time(15, 1, 0)
        
        return target_start <= current_time_obj <= target_end
    
    async def _send_daily_reports(self):
        """发送每日错误报告"""
        logger.info("开始发送每日错误报告...")
        
        db = SessionLocal()
        try:
            # 获取所有活跃的监控任务
            active_tasks = db.query(MonitorTask).filter(
                and_(
                    MonitorTask.is_active == True,
                    MonitorTask.status == MonitorStatus.RUNNING
                )
            ).all()
            
            for task in active_tasks:
                try:
                    await self._send_task_report(db, task)
                except Exception as e:
                    logger.error(f"发送任务 {task.id} 报告失败: {str(e)}")
                    
        except Exception as e:
            logger.error(f"发送每日报告异常: {str(e)}")
        finally:
            db.close()
    
    async def _send_task_report(self, db: Session, task: MonitorTask):
        """发送单个任务的错误报告"""
        if not task.email_recipients:
            logger.warning(f"任务 {task.id} 没有配置邮件接收者")
            return
        
        device = task.device
        if not device:
            logger.error(f"任务 {task.id} 关联的设备不存在")
            return
        
        # 获取设备的错误日志
        error_summary, error_logs = await self._collect_error_data(db, device, task)
        
        # 准备设备信息
        device_info = {
            'name': device.name,
            'ip_address': device.ip_address,
            'ssh_username': device.ssh_username,
            'log_path': task.log_path,
            'task_name': task.name
        }
        
        # 发送邮件
        success = await email_service.send_error_report(
            recipients=task.email_recipients,
            device_info=device_info,
            error_summary=error_summary,
            error_logs=error_logs
        )
        
        if success:
            logger.info(f"成功发送任务 {task.id} ({task.name}) 的错误报告")
            
            # 更新监控日志记录
            monitor_log = MonitorLog(
                device_id=device.id,
                task_id=task.id,
                log_file=f"daily-report-{datetime.now().strftime('%Y%m%d')}.log",
                error_count=error_summary.get('total_errors', 0),
                error_summary=error_summary,
                email_sent=True,
                email_sent_at=datetime.utcnow()
            )
            db.add(monitor_log)
            db.commit()
        else:
            logger.error(f"发送任务 {task.id} ({task.name}) 的错误报告失败")
    
    async def _collect_error_data(self, db: Session, device: NASDevice, task: MonitorTask) -> tuple:
        """收集设备的错误数据"""
        error_summary = {
            'total_errors': 0,
            'error_types': 0,
            'affected_logs': 0,
            'monitoring_period': '过去24小时',
            'last_check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        error_logs = []
        
        try:
            # 解密密码
            password = self.device_manager.decrypt_password(device.ssh_password)
            device_info = {
                'ip': device.ip_address,
                'username': device.ssh_username,
                'password': password,
                'port': device.ssh_port
            }
            
            # 获取设备上的错误日志文件
            remote_error_logs = await self.device_manager.get_error_logs(device_info, limit=50)
            
            if not remote_error_logs:
                return error_summary, error_logs
            
            # 统计错误信息
            error_summary['affected_logs'] = len(remote_error_logs)
            rule_errors = {}
            
            # 获取任务使用的规则
            rules_dict = {}
            if task.rule_ids:
                rules = db.query(DetectionRule).filter(DetectionRule.id.in_(task.rule_ids)).all()
                rules_dict = {rule.id: rule for rule in rules}
            
            # 处理每个错误日志文件
            for log_file in remote_error_logs[:10]:  # 最多处理10个最新的错误日志
                try:
                    log_content = await self.device_manager.download_error_log(device_info, log_file['filename'])
                    if log_content:
                        parsed_errors = self._parse_error_log_content(log_content, rules_dict)
                        
                        for rule_name, error_info in parsed_errors.items():
                            if rule_name not in rule_errors:
                                rule_errors[rule_name] = {
                                    'rule_name': rule_name,
                                    'description': error_info.get('description', ''),
                                    'count': 0,
                                    'first_seen': error_info.get('first_seen', ''),
                                    'last_seen': error_info.get('last_seen', ''),
                                    'source_file': log_file['filename'],
                                    'sample_content': error_info.get('sample_content', '')
                                }
                            
                            rule_errors[rule_name]['count'] += error_info.get('count', 1)
                            
                            # 更新最后发现时间
                            if error_info.get('last_seen'):
                                if not rule_errors[rule_name]['last_seen'] or error_info['last_seen'] > rule_errors[rule_name]['last_seen']:
                                    rule_errors[rule_name]['last_seen'] = error_info['last_seen']
                
                except Exception as e:
                    logger.warning(f"处理错误日志文件 {log_file['filename']} 失败: {str(e)}")
            
            # 构建最终结果
            error_logs = list(rule_errors.values())
            error_summary['total_errors'] = sum(log['count'] for log in error_logs)
            error_summary['error_types'] = len(error_logs)
            
        except Exception as e:
            logger.error(f"收集设备 {device.id} 错误数据失败: {str(e)}")
        
        return error_summary, error_logs
    
    def _parse_error_log_content(self, log_content: str, rules_dict: Dict[int, Any]) -> Dict[str, Any]:
        """解析错误日志内容"""
        parsed_errors = {}
        
        try:
            lines = log_content.split('\n')
            current_error = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 检查是否是新错误的开始
                if line.startswith('[') and '] 发现新错误' in line:
                    current_error = {}
                elif line.startswith('规则: ') and current_error is not None:
                    current_error['rule_name'] = line[3:].strip()
                elif line.startswith('描述: ') and current_error is not None:
                    current_error['description'] = line[3:].strip()
                elif line.startswith('来源: ') and current_error is not None:
                    current_error['source'] = line[3:].strip()
                elif '出现次数:' in line:
                    # 解析统计信息
                    parts = line.split()
                    if len(parts) >= 3:
                        rule_name = parts[0]
                        try:
                            count = int(parts[2])
                            first_seen = ''
                            if '首次发现:' in line:
                                first_seen_index = line.find('首次发现:') + 5
                                first_seen = line[first_seen_index:].strip(')')
                            
                            parsed_errors[rule_name] = {
                                'rule_name': rule_name,
                                'count': count,
                                'first_seen': first_seen,
                                'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'description': '',
                                'sample_content': ''
                            }
                        except ValueError:
                            pass
                elif current_error is not None and line and not line.startswith('-'):
                    # 收集错误内容作为样本
                    if 'sample_content' not in current_error:
                        current_error['sample_content'] = line[:200]  # 限制样本长度
                    
                    # 如果遇到分隔线，结束当前错误
                    if line.startswith('-'):
                        if current_error and current_error.get('rule_name'):
                            rule_name = current_error['rule_name']
                            parsed_errors[rule_name] = current_error
                        current_error = None
        
        except Exception as e:
            logger.error(f"解析错误日志内容失败: {str(e)}")
        
        return parsed_errors
    
    async def _check_monitor_tasks(self):
        """检查监控任务状态"""
        db = SessionLocal()
        try:
            # 检查需要执行的任务
            now = datetime.utcnow()
            pending_tasks = db.query(MonitorTask).filter(
                and_(
                    MonitorTask.is_active == True,
                    MonitorTask.next_run <= now,
                    MonitorTask.status != MonitorStatus.ERROR
                )
            ).all()
            
            for task in pending_tasks:
                try:
                    await self._execute_monitor_task(db, task)
                except Exception as e:
                    logger.error(f"执行监控任务 {task.id} 失败: {str(e)}")
                    task.status = MonitorStatus.ERROR
                    task.error_count += 1
                    db.commit()
        
        except Exception as e:
            logger.error(f"检查监控任务状态异常: {str(e)}")
        finally:
            db.close()
    
    async def _execute_monitor_task(self, db: Session, task: MonitorTask):
        """执行监控任务"""
        logger.info(f"执行监控任务: {task.id} - {task.name}")
        
        # 更新任务状态
        task.last_run = datetime.utcnow()
        task.next_run = datetime.utcnow() + timedelta(hours=1)  # 默认每小时执行
        db.commit()
        
        # 这里可以添加实际的监控逻辑
        # 比如触发设备上脚本的执行等


# 全局调度器实例
monitor_scheduler = MonitorScheduler()