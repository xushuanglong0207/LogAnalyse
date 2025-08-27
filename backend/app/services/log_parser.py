import re
import json
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.log import LogEntry, LogFile, ParseRule, LogLevel, LogType
from ..models.user import User
from .dsl_parser import DSLRuleEngine


class LogParserService:
    """日志解析服务 - 核心日志分析引擎"""
    
    def __init__(self, db: Session):
        self.db = db
        self.builtin_rules = self._init_builtin_rules()
    
    def _init_builtin_rules(self) -> List[Dict]:
        """初始化内置解析规则"""
        return [
            {
                "name": "OOM Killer",
                "pattern": r"(oom|out of memory|oom[-_]?kill|earlyoom)",
                "problem_type": "内存溢出",
                "problem_description": "系统内存不足，触发OOM Killer机制",
                "priority": 10
            },
            {
                "name": "Kernel Panic",
                "pattern": r"(kernel panic|panic|oops|bug:|call trace)",
                "problem_type": "内核错误",
                "problem_description": "内核崩溃或严重错误",
                "priority": 10
            },
            {
                "name": "Segmentation Fault",
                "pattern": r"(segfault|segmentation fault|sigsegv)",
                "problem_type": "程序错误",
                "problem_description": "程序访问了非法内存地址",
                "priority": 8
            },
            {
                "name": "Disk Space Error",
                "pattern": r"(no space left|disk full|enospc)",
                "problem_type": "磁盘空间",
                "problem_description": "磁盘空间不足",
                "priority": 7
            },
            {
                "name": "Network Error",
                "pattern": r"(network unreachable|connection refused|timeout|dns)",
                "problem_type": "网络错误",
                "problem_description": "网络连接问题",
                "priority": 6
            },
            {
                "name": "File System Error",
                "pattern": r"(i\/o error|read-only file system|filesystem|mount)",
                "problem_type": "文件系统错误",
                "problem_description": "文件系统相关错误",
                "priority": 7
            },
            {
                "name": "Authentication Error",
                "pattern": r"(authentication failed|permission denied|access denied|unauthorized)",
                "problem_type": "认证错误",
                "problem_description": "身份验证或权限错误",
                "priority": 5
            }
        ]
    
    async def parse_log_file(self, log_file: LogFile, user: User) -> Dict:
        """解析日志文件"""
        start_time = time.time()
        
        try:
            # 读取文件内容
            with open(log_file.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # 更新文件统计信息
            log_file.total_lines = len(lines)
            self.db.commit()
            
            # 获取解析规则
            rules = self._get_parse_rules()
            
            # 解析每一行
            processed_count = 0
            error_count = 0
            problems_found = 0
            problem_summary = {}
            
            for line_number, line in enumerate(lines, 1):
                try:
                    log_entry = self._parse_log_line(
                        log_file.id, line_number, line.strip(), rules
                    )
                    
                    if log_entry.problem_detected:
                        problems_found += 1
                        problem_type = log_entry.problem_type
                        if problem_type not in problem_summary:
                            problem_summary[problem_type] = 0
                        problem_summary[problem_type] += 1
                    
                    self.db.add(log_entry)
                    processed_count += 1
                    
                    # 批量提交以提高性能
                    if processed_count % 1000 == 0:
                        self.db.commit()
                        log_file.processed_lines = processed_count
                        self.db.commit()
                        
                except Exception as e:
                    error_count += 1
                    print(f"解析第 {line_number} 行时出错: {str(e)}")
                    continue
            
            # 最终提交
            self.db.commit()
            
            # 更新文件状态
            log_file.processed_lines = processed_count
            log_file.error_lines = error_count
            log_file.is_processed = True
            self.db.commit()
            
            processing_time = time.time() - start_time
            
            return {
                "total_lines": log_file.total_lines,
                "processed_lines": processed_count,
                "error_lines": error_count,
                "problems_found": problems_found,
                "problem_summary": [
                    {"type": k, "count": v} for k, v in problem_summary.items()
                ],
                "processing_time": round(processing_time, 2)
            }
            
        except Exception as e:
            # 标记为处理失败
            log_file.is_processed = False
            self.db.commit()
            raise Exception(f"解析文件失败: {str(e)}")
    
    def _get_parse_rules(self) -> List[Dict]:
        """获取所有解析规则（内置 + 自定义）"""
        rules = self.builtin_rules.copy()
        
        # 获取数据库中的自定义规则
        custom_rules = self.db.query(ParseRule).filter(
            ParseRule.is_active == True
        ).order_by(ParseRule.priority.desc()).all()
        
        for rule in custom_rules:
            # 编译DSL规则
            compiled_rule = None
            if rule.rule_type.value == "dsl":
                compiled_rule = DSLRuleEngine.compile_rule(rule.pattern)
                if not compiled_rule["compiled"]:
                    print(f"DSL规则编译失败: {rule.name} - {compiled_rule['error']}")
                    continue
            
            rules.append({
                "name": rule.name,
                "pattern": rule.pattern,
                "problem_type": rule.problem_type,
                "problem_description": rule.problem_description,
                "priority": rule.priority,
                "rule_type": rule.rule_type.value,
                "compiled_dsl": compiled_rule if rule.rule_type.value == "dsl" else None
            })
        
        return sorted(rules, key=lambda x: x["priority"], reverse=True)
    
    def _parse_log_line(self, log_file_id: int, line_number: int, 
                       content: str, rules: List[Dict]) -> LogEntry:
        """解析单行日志"""
        log_entry = LogEntry(
            log_file_id=log_file_id,
            line_number=line_number,
            raw_content=content,
            problem_detected=False
        )
        
        # 尝试解析时间戳
        timestamp = self._extract_timestamp(content)
        if timestamp:
            log_entry.timestamp = timestamp
        
        # 尝试解析日志级别
        level = self._extract_log_level(content)
        if level:
            log_entry.log_level = level
        
        # 尝试解析来源
        source = self._extract_source(content)
        if source:
            log_entry.source = source
        
        # 提取消息内容
        message = self._extract_message(content)
        log_entry.message = message
        
        # 应用解析规则检测问题
        for rule in rules:
            if self._apply_rule(content, rule):
                log_entry.problem_detected = True
                log_entry.problem_type = rule["problem_type"]
                log_entry.problem_description = rule["problem_description"]
                break  # 只应用第一个匹配的规则（按优先级排序）
        
        return log_entry
    
    def _extract_timestamp(self, content: str) -> Optional[datetime]:
        """提取时间戳"""
        # 常见的时间戳格式
        timestamp_patterns = [
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',  # 2024-01-01 12:00:00
            r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})',    # Jan 01 12:00:00
            r'(\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2})', # 01/01/2024 12:00:00
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    timestamp_str = match.group(1)
                    # 尝试不同的时间格式解析
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%b %d %H:%M:%S', '%m/%d/%Y %H:%M:%S']:
                        try:
                            return datetime.strptime(timestamp_str, fmt)
                        except ValueError:
                            continue
                except Exception:
                    continue
        
        return None
    
    def _extract_log_level(self, content: str) -> Optional[LogLevel]:
        """提取日志级别"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['error', 'err', 'fatal']):
            return LogLevel.ERROR
        elif any(word in content_lower for word in ['warn', 'warning']):
            return LogLevel.WARNING
        elif any(word in content_lower for word in ['info', 'information']):
            return LogLevel.INFO
        elif any(word in content_lower for word in ['debug', 'dbg']):
            return LogLevel.DEBUG
        elif any(word in content_lower for word in ['critical', 'crit', 'panic']):
            return LogLevel.CRITICAL
        
        return None
    
    def _extract_source(self, content: str) -> Optional[str]:
        """提取日志来源"""
        # 尝试提取进程名或模块名
        patterns = [
            r'(\w+)\[\d+\]:',  # process[pid]:
            r'(\w+):\s',       # module: 
            r'\[(\w+)\]',      # [module]
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_message(self, content: str) -> str:
        """提取消息内容"""
        # 移除时间戳和来源信息，保留主要消息
        message = content
        
        # 移除常见的前缀
        patterns_to_remove = [
            r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[.\d]*\s*',
            r'^\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s*',
            r'^\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2}\s*',
            r'^\w+\[\d+\]:\s*',
            r'^\[\w+\]\s*',
        ]
        
        for pattern in patterns_to_remove:
            message = re.sub(pattern, '', message)
        
        return message.strip()
    
    def _apply_rule(self, content: str, rule: Dict) -> bool:
        """应用解析规则"""
        try:
            pattern = rule["pattern"]
            rule_type = rule.get("rule_type", "regex")
            
            if rule_type == "regex":
                return bool(re.search(pattern, content, re.IGNORECASE))
            elif rule_type == "keyword":
                return pattern.lower() in content.lower()
            elif rule_type == "dsl":
                # 使用DSL规则引擎
                compiled_rule = rule.get("compiled_dsl")
                if compiled_rule and compiled_rule["compiled"]:
                    return DSLRuleEngine.match_rule(compiled_rule, content)
                return False
            elif rule_type == "json_path":
                # 对于JSON格式的日志
                try:
                    data = json.loads(content)
                    # 简单的JSON路径解析（可以后续扩展）
                    return self._check_json_path(data, pattern)
                except json.JSONDecodeError:
                    return False
            
            return False
            
        except re.error:
            # 正则表达式错误
            return False
    
    def _check_json_path(self, data: dict, path: str) -> bool:
        """检查JSON路径"""
        # 简单实现，可以后续扩展为更复杂的JSONPath
        keys = path.split('.')
        current = data
        
        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return False
            return True
        except Exception:
            return False 