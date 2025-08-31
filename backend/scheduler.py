#!/usr/bin/env python3
"""
Background scheduler for hourly log analysis and daily email reports
"""
import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
import subprocess
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/log-monitor-scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('scheduler')

# Data directory paths
DATA_DIR = os.environ.get("LOG_ANALYZER_DATA", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database")))
NAS_DEVICES_PATH = os.path.join(DATA_DIR, "nas_devices.json")
MONITOR_TASKS_PATH = os.path.join(DATA_DIR, "monitor_tasks.json")
EMAIL_CONFIG_PATH = os.path.join(DATA_DIR, "email_config.json")
DETECTION_RULES_PATH = os.path.join(DATA_DIR, "detection_rules.json")
SCHEDULER_STATE_PATH = os.path.join(DATA_DIR, "scheduler_state.json")

class LogMonitorScheduler:
    def __init__(self):
        self.is_running = False
        self.last_hourly_check = None
        self.last_daily_report = None
        self.nas_devices = []
        self.monitor_tasks = []
        self.email_config = {}
        self.detection_rules = []
        
    def load_data(self):
        """Load configuration data from JSON files"""
        try:
            # Load NAS devices
            if os.path.exists(NAS_DEVICES_PATH):
                with open(NAS_DEVICES_PATH, 'r', encoding='utf-8') as f:
                    self.nas_devices = json.load(f)
            
            # Load monitor tasks
            if os.path.exists(MONITOR_TASKS_PATH):
                with open(MONITOR_TASKS_PATH, 'r', encoding='utf-8') as f:
                    self.monitor_tasks = json.load(f)
            
            # Load email config
            if os.path.exists(EMAIL_CONFIG_PATH):
                with open(EMAIL_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    self.email_config = json.load(f)
            
            # Load detection rules
            if os.path.exists(DETECTION_RULES_PATH):
                with open(DETECTION_RULES_PATH, 'r', encoding='utf-8') as f:
                    self.detection_rules = json.load(f)
            
            # Load scheduler state
            if os.path.exists(SCHEDULER_STATE_PATH):
                with open(SCHEDULER_STATE_PATH, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.last_hourly_check = state.get('last_hourly_check')
                    self.last_daily_report = state.get('last_daily_report')
                    
            logger.info(f"Loaded {len(self.nas_devices)} devices, {len(self.monitor_tasks)} tasks, {len(self.detection_rules)} rules")
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    
    def save_state(self):
        """Save scheduler state"""
        try:
            state = {
                'last_hourly_check': self.last_hourly_check,
                'last_daily_report': self.last_daily_report,
                'updated_at': datetime.now().isoformat()
            }
            with open(SCHEDULER_STATE_PATH, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def get_log_content_via_ssh(self, device: Dict[str, Any], log_paths: List[str]) -> str:
        """Get log content from device via SSH"""
        try:
            ip = device['ip_address']
            port = device['ssh_port']
            username = device['ssh_username'] 
            password = device['ssh_password']
            
            # Combine multiple log paths
            log_paths_str = ' '.join(f'"{path}"' for path in log_paths)
            
            # Get recent logs with errors
            cmd = [
                'sshpass', '-p', password,
                'ssh',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'ConnectTimeout=10',
                '-p', str(port),
                f'{username}@{ip}',
                f'for file in {log_paths_str}; do if [ -f "$file" ]; then echo "=== $file ==="; tail -100 "$file"; fi; done'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning(f"SSH command failed for device {device['name']}: {result.stderr}")
                return ""
                
        except subprocess.TimeoutExpired:
            logger.warning(f"SSH timeout for device {device['name']}")
            return ""
        except Exception as e:
            logger.error(f"SSH error for device {device['name']}: {e}")
            return ""
    
    def analyze_log_content(self, content: str, rules: List[Dict]) -> List[Dict]:
        """Analyze log content using detection rules"""
        issues = []
        
        for rule in rules:
            if not rule.get('enabled', True):
                continue
                
            # Simple pattern matching - can be enhanced with the DSL parser from main.py
            patterns = rule.get('patterns', [])
            if not patterns:
                continue
                
            for pattern in patterns:
                # Count occurrences of pattern in content (case insensitive)
                import re
                try:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        issues.append({
                            'rule_name': rule['name'],
                            'description': rule.get('description', ''),
                            'pattern': pattern,
                            'match_count': len(matches),
                            'severity': 'high' if any(word in rule['name'].lower() for word in ['panic', 'oom', 'critical']) else 'medium'
                        })
                except re.error:
                    # If regex is invalid, try literal match
                    if pattern.lower() in content.lower():
                        issues.append({
                            'rule_name': rule['name'],
                            'description': rule.get('description', ''),
                            'pattern': pattern,
                            'match_count': content.lower().count(pattern.lower()),
                            'severity': 'medium'
                        })
        
        return issues
    
    def send_email_report(self, task: Dict[str, Any], device: Dict[str, Any], issues: List[Dict]):
        """Send email report for a monitoring task"""
        if not self.email_config.get('is_configured'):
            logger.warning("Email not configured, skipping email report")
            return False
            
        recipients = task.get('email_recipients', [])
        if not recipients:
            logger.warning(f"No recipients for task {task['name']}")
            return False
        
        try:
            # Create email message
            msg = MimeMultipart()
            msg['From'] = f"{self.email_config['sender_name']} <{self.email_config['sender_email']}>"
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[日志分析] {device['name']} - {task['name']} 监控报告"
            
            # Email body
            body = f"""
日志监控报告

监控任务: {task['name']}
监控设备: {device['name']} ({device['ip_address']})
日志路径: {task['log_path']}
报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

分析结果:
"""
            
            if issues:
                body += f"发现 {len(issues)} 个问题:\n\n"
                for issue in issues:
                    body += f"• {issue['rule_name']}: {issue['description']}\n"
                    body += f"  匹配次数: {issue['match_count']} | 严重级别: {issue['severity']}\n\n"
            else:
                body += "未发现问题，系统运行正常。\n"
            
            body += "\n---\n日志分析系统自动发送"
            
            msg.attach(MimeText(body, 'plain', 'utf-8'))
            
            # Send email
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            
            if self.email_config.get('use_tls', True):
                server.starttls()
            
            server.login(self.email_config['sender_email'], self.email_config['sender_password'])
            
            for recipient in recipients:
                server.send_message(msg, to_addrs=[recipient])
            
            server.quit()
            
            logger.info(f"Email report sent for task {task['name']} to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email for task {task['name']}: {e}")
            return False
    
    def run_hourly_analysis(self):
        """Run hourly log analysis for all monitor tasks"""
        logger.info("Starting hourly log analysis...")
        
        for task in self.monitor_tasks:
            if task.get('status') != 'running':
                continue
                
            device = next((d for d in self.nas_devices if d['id'] == task['device_id']), None)
            if not device:
                logger.warning(f"Device not found for task {task['name']}")
                continue
            
            # Parse log paths (comma separated)
            log_paths = [path.strip() for path in task['log_path'].split(',')]
            
            # Get log content
            content = self.get_log_content_via_ssh(device, log_paths)
            if not content:
                logger.warning(f"No log content retrieved for task {task['name']}")
                continue
            
            # Filter rules for this task
            task_rules = [rule for rule in self.detection_rules if rule['id'] in task.get('rule_ids', [])]
            
            # Analyze content
            issues = self.analyze_log_content(content, task_rules)
            
            logger.info(f"Task {task['name']}: found {len(issues)} issues")
            
            # Update task statistics
            task['error_count'] = len(issues)
            task['last_run'] = datetime.now().isoformat()
            
        # Save updated tasks
        self.save_tasks()
        self.last_hourly_check = datetime.now().isoformat()
    
    def run_daily_reports(self):
        """Send daily email reports at 3PM"""
        current_time = datetime.now()
        
        # Check if it's around 3PM (15:00)
        if current_time.hour != 15:
            return
            
        # Check if we already sent reports today
        if self.last_daily_report:
            try:
                last_report_date = datetime.fromisoformat(self.last_daily_report).date()
                if last_report_date == current_time.date():
                    return  # Already sent today
            except:
                pass
        
        logger.info("Starting daily email reports...")
        
        for task in self.monitor_tasks:
            device = next((d for d in self.nas_devices if d['id'] == task['device_id']), None)
            if not device:
                continue
            
            # Get log content for the past 24 hours
            log_paths = [path.strip() for path in task['log_path'].split(',')]
            content = self.get_log_content_via_ssh(device, log_paths)
            
            # Filter rules for this task
            task_rules = [rule for rule in self.detection_rules if rule['id'] in task.get('rule_ids', [])]
            
            # Analyze content
            issues = self.analyze_log_content(content, task_rules)
            
            # Send email report
            self.send_email_report(task, device, issues)
        
        self.last_daily_report = current_time.isoformat()
    
    def save_tasks(self):
        """Save monitor tasks to file"""
        try:
            with open(MONITOR_TASKS_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.monitor_tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving tasks: {e}")
    
    async def run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Starting log monitor scheduler...")
        self.is_running = True
        
        while self.is_running:
            try:
                # Reload data every cycle
                self.load_data()
                
                current_time = datetime.now()
                
                # Run hourly analysis (every hour)
                if not self.last_hourly_check or \
                   (current_time - datetime.fromisoformat(self.last_hourly_check)).total_seconds() >= 3600:
                    self.run_hourly_analysis()
                
                # Run daily reports at 3PM
                self.run_daily_reports()
                
                # Save state
                self.save_state()
                
                # Sleep for 5 minutes before next check
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Short sleep on error
    
    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping scheduler...")
        self.is_running = False

def main():
    """Main function to run the scheduler"""
    scheduler = LogMonitorScheduler()
    
    try:
        # Run the scheduler
        asyncio.run(scheduler.run_scheduler())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
        scheduler.stop()
    except Exception as e:
        logger.error(f"Scheduler error: {e}")

if __name__ == "__main__":
    main()