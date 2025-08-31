#!/usr/bin/env python3
"""
NAS监控脚本生成器
用于生成部署到NAS设备上的监控脚本
"""

import json
from typing import List, Dict, Any
from datetime import datetime
from ..services.dsl_parser import DSLRuleEngine


class NASMonitorScriptGenerator:
    """NAS监控脚本生成器"""
    
    def __init__(self):
        self.script_version = "1.0.0"
        
    def generate_monitor_script(self, 
                               task_name: str,
                               log_paths: List[str], 
                               rules: List[Dict[str, Any]],
                               email_recipients: List[str],
                               device_info: Dict[str, str]) -> str:
        """
        生成监控脚本
        
        Args:
            task_name: 任务名称
            log_paths: 监控的日志路径列表
            rules: 规则列表 [{"id": 1, "name": "OOM检测", "dsl": "...", "description": "..."}]
            email_recipients: 邮件接收者列表
            device_info: 设备信息 {"name": "", "ip": "", "username": "", "password": ""}
        """
        
        # 生成规则匹配函数
        rule_functions = self._generate_rule_functions(rules)
        
        # 生成主脚本
        script_content = f'''#!/bin/bash
# NAS日志监控脚本
# 版本: {self.script_version}
# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# 任务名称: {task_name}

set -e

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
LOG_DIR="$SCRIPT_DIR"
ERROR_LOG_PREFIX="error-log"
LOCK_FILE="$SCRIPT_DIR/.monitor.lock"
STATE_FILE="$SCRIPT_DIR/.monitor.state"

# 设备信息
DEVICE_NAME="{device_info.get('name', 'Unknown')}"
DEVICE_IP="{device_info.get('ip', 'Unknown')}"
DEVICE_USER="{device_info.get('username', 'Unknown')}"

# 监控日志路径
declare -a LOG_PATHS=({' '.join([f'"{path}"' for path in log_paths])})

# 邮件接收者
declare -a EMAIL_RECIPIENTS=({' '.join([f'"{email}"' for email in email_recipients])})

# 创建锁文件，防止重复执行
create_lock() {{
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(cat "$LOCK_FILE")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] 监控脚本正在运行中 (PID: $pid)"
            exit 0
        fi
    fi
    echo $$ > "$LOCK_FILE"
}}

# 清理锁文件
cleanup_lock() {{
    rm -f "$LOCK_FILE"
}}

# 信号处理
trap cleanup_lock EXIT INT TERM

# 获取当前状态
load_state() {{
    if [ -f "$STATE_FILE" ]; then
        source "$STATE_FILE"
    else
        declare -A ERROR_COUNTS=()
        declare -A ERROR_FIRST_SEEN=()
        ERROR_LOG_FILE=""
    fi
}}

# 保存状态
save_state() {{
    {{
        echo "declare -A ERROR_COUNTS=("
        for key in "${{!ERROR_COUNTS[@]}}"; do
            echo "    [\"$key\"]=\"${{ERROR_COUNTS[$key]}}\""
        done
        echo ")"
        echo ""
        echo "declare -A ERROR_FIRST_SEEN=("
        for key in "${{!ERROR_FIRST_SEEN[@]}}"; do
            echo "    [\"$key\"]=\"${{ERROR_FIRST_SEEN[$key]}}\""
        done
        echo ")"
        echo ""
        echo "ERROR_LOG_FILE=\"$ERROR_LOG_FILE\""
    }} > "$STATE_FILE"
}}

# 规则匹配函数
{rule_functions}

# 日志处理函数
process_log_file() {{
    local log_file="$1"
    local content
    
    if [ ! -f "$log_file" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] 日志文件不存在: $log_file"
        return 0
    fi
    
    # 读取文件内容（最近1000行，避免文件过大）
    content=$(tail -n 1000 "$log_file" 2>/dev/null || echo "")
    
    if [ -z "$content" ]; then
        return 0
    fi
    
    # 检查每个规则
{self._generate_rule_checks()}
}}

# 创建错误日志文件
create_error_log() {{
    if [ -z "$ERROR_LOG_FILE" ]; then
        local timestamp=$(date '+%Y%m%d%H%M%S')
        ERROR_LOG_FILE="$LOG_DIR/${{ERROR_LOG_PREFIX}}-$timestamp.log"
        
        # 写入文件头
        {{
            echo "# NAS设备错误日志"
            echo "# 设备名称: $DEVICE_NAME"
            echo "# 设备IP: $DEVICE_IP"
            echo "# 开始监控时间: $(date '+%Y-%m-%d %H:%M:%S')"
            echo "# ========================================"
            echo ""
        }} > "$ERROR_LOG_FILE"
    fi
}}

# 记录错误到日志文件
log_error() {{
    local rule_name="$1"
    local rule_desc="$2"
    local matched_content="$3"
    local log_source="$4"
    local error_key="${{rule_name}}_${{log_source}}"
    
    create_error_log
    
    # 检查是否是新错误
    if [ -z "${{ERROR_COUNTS[$error_key]+x}}" ]; then
        ERROR_COUNTS[$error_key]=1
        ERROR_FIRST_SEEN[$error_key]=$(date '+%Y-%m-%d %H:%M:%S')
        
        # 记录新错误
        {{
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 发现新错误"
            echo "规则: $rule_name"
            echo "描述: $rule_desc" 
            echo "来源: $log_source"
            echo "内容:"
            echo "$matched_content"
            echo "----------------------------------------"
            echo ""
        }} >> "$ERROR_LOG_FILE"
    else
        # 增加错误计数
        ((ERROR_COUNTS[$error_key]++))
        
        # 更新计数信息（替换文件中的计数行）
        sed -i "/^## 错误统计/,/^$/{{
            /^$rule_name.*出现次数/c\\
$rule_name ($log_source) 出现次数: ${{ERROR_COUNTS[$error_key]}} (首次发现: ${{ERROR_FIRST_SEEN[$error_key]}})
        }}" "$ERROR_LOG_FILE" 2>/dev/null || true
    fi
    
    save_state
}}

# 更新错误统计
update_error_stats() {{
    if [ -n "$ERROR_LOG_FILE" ] && [ -f "$ERROR_LOG_FILE" ]; then
        # 添加统计信息到文件末尾
        {{
            echo ""
            echo "## 错误统计 (更新时间: $(date '+%Y-%m-%d %H:%M:%S'))"
            echo "========================================"
            for key in "${{!ERROR_COUNTS[@]}}"; do
                local rule_info=$(echo "$key" | sed 's/_/ (/' | sed 's/$/)/')
                echo "$rule_info 出现次数: ${{ERROR_COUNTS[$key]}} (首次发现: ${{ERROR_FIRST_SEEN[$key]}})"
            done
            echo ""
        }} >> "$ERROR_LOG_FILE"
    fi
}}

# 主函数
main() {{
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] 开始执行日志监控..."
    
    create_lock
    load_state
    
    # 处理每个日志文件
    for log_path in "${{LOG_PATHS[@]}}"; do
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] 处理日志文件: $log_path"
        process_log_file "$log_path"
    done
    
    # 更新错误统计
    update_error_stats
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] 日志监控完成"
    
    # 显示统计信息
    if [ "${{#ERROR_COUNTS[@]}}" -gt 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] 发现 ${{#ERROR_COUNTS[@]}} 类错误"
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] 错误日志: $ERROR_LOG_FILE"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] 未发现错误"
    fi
}}

# 运行主函数
main "$@"
'''
        
        return script_content
    
    def _generate_rule_functions(self, rules: List[Dict[str, Any]]) -> str:
        """生成规则匹配函数"""
        functions = []
        
        for rule in rules:
            rule_id = rule.get('id')
            rule_name = rule.get('name', f'Rule_{rule_id}')
            rule_dsl = rule.get('dsl', '')
            rule_desc = rule.get('description', '')
            
            if not rule_dsl:
                continue
                
            # 将DSL转换为bash可执行的逻辑
            bash_logic = self._convert_dsl_to_bash(rule_dsl, rule_name, rule_desc)
            
            function_name = f"check_rule_{rule_id}"
            
            function_code = f'''# 规则: {rule_name}
# 描述: {rule_desc}
{function_name}() {{
    local content="$1"
    local log_source="$2"
    
    # DSL: {rule_dsl}
    {bash_logic}
}}

'''
            functions.append(function_code)
        
        return '\n'.join(functions)
    
    def _convert_dsl_to_bash(self, dsl_expression: str, rule_name: str = "Unknown", rule_desc: str = "") -> str:
        """将DSL表达式转换为bash逻辑"""
        try:
            # 这里实现DSL到bash的转换逻辑
            # 暂时使用简化版本，后续可以完善
            
            # 替换操作符
            bash_expr = dsl_expression.replace(' & ', ' && ')
            bash_expr = bash_expr.replace(' | ', ' || ')
            bash_expr = bash_expr.replace('!', '!')
            
            # 处理引号字符串，转换为grep检查
            import re
            
            def quote_to_grep(match):
                keyword = match.group(1)
                return f'echo "$content" | grep -qi "{keyword}"'
            
            # 查找所有引号包围的字符串
            bash_expr = re.sub(r'"([^"]+)"', quote_to_grep, bash_expr)
            
            return f'''
    # 转换后的匹配逻辑
    if {bash_expr}; then
        # 提取匹配的上下文（前后3行）
        local matched_context=$(echo "$content" | grep -A 3 -B 3 -i "$(echo "{dsl_expression}" | sed -E 's/[&|!()]//g' | sed -E 's/"//g' | awk '{{print $1}}')" | head -20)
        log_error "{rule_name}" "{rule_desc}" "$matched_context" "$log_source"
        return 0
    fi
    return 1'''
        except Exception as e:
            # 如果转换失败，返回简单的关键字匹配
            return f'''
    # 简化匹配逻辑 (DSL转换失败: {str(e)})
    if echo "$content" | grep -qi "{dsl_expression}"; then
        local matched_context=$(echo "$content" | grep -A 3 -B 3 -i "{dsl_expression}" | head -20)
        log_error "{rule_name}" "DSL匹配" "$matched_context" "$log_source"
        return 0
    fi
    return 1'''
    
    def _generate_rule_checks(self) -> str:
        """生成规则检查调用代码"""
        return '''
    # 逐个检查规则（这部分会在生成时动态替换）
    local rule_matched=false
    
    # 这里会插入具体的规则检查调用
    # check_rule_1 "$content" "$log_file"
    # check_rule_2 "$content" "$log_file"
    # ...
'''

    def generate_crontab_entry(self, script_path: str, cron_expression: str = "0 * * * *") -> str:
        """生成crontab条目"""
        return f"{cron_expression} {script_path} >> /var/log/nas-monitor.log 2>&1"
    
    def generate_deploy_script(self, device_info: Dict[str, str], monitor_script_content: str) -> str:
        """生成部署脚本"""
        deploy_script = f'''#!/bin/bash
# NAS监控脚本部署工具
# 目标设备: {device_info.get('ip', 'Unknown')}

set -e

DEVICE_IP="{device_info.get('ip')}"
DEVICE_USER="{device_info.get('username')}"
DEVICE_PASS="{device_info.get('password')}"
REMOTE_DIR="/home/$DEVICE_USER/nas-log-monitor"
SCRIPT_NAME="nas-log-monitor.sh"

echo "开始部署监控脚本到 $DEVICE_IP..."

# 创建临时脚本文件
TEMP_SCRIPT=$(mktemp)
cat > "$TEMP_SCRIPT" << 'SCRIPT_EOF'
{monitor_script_content}
SCRIPT_EOF

# 使用sshpass进行SSH连接和文件传输
sshpass -p "$DEVICE_PASS" ssh -o StrictHostKeyChecking=no "$DEVICE_USER@$DEVICE_IP" "mkdir -p $REMOTE_DIR"

# 上传脚本文件
sshpass -p "$DEVICE_PASS" scp -o StrictHostKeyChecking=no "$TEMP_SCRIPT" "$DEVICE_USER@$DEVICE_IP:$REMOTE_DIR/$SCRIPT_NAME"

# 设置执行权限
sshpass -p "$DEVICE_PASS" ssh -o StrictHostKeyChecking=no "$DEVICE_USER@$DEVICE_IP" "chmod +x $REMOTE_DIR/$SCRIPT_NAME"

# 添加crontab任务
sshpass -p "$DEVICE_PASS" ssh -o StrictHostKeyChecking=no "$DEVICE_USER@$DEVICE_IP" "
    (crontab -l 2>/dev/null | grep -v '$REMOTE_DIR/$SCRIPT_NAME' || true; echo '0 * * * * $REMOTE_DIR/$SCRIPT_NAME') | crontab -
"

# 清理临时文件
rm -f "$TEMP_SCRIPT"

echo "部署完成！监控脚本已成功部署到 $DEVICE_IP:$REMOTE_DIR/$SCRIPT_NAME"
echo "Crontab已配置，每小时执行一次监控。"
'''
        return deploy_script


# 使用示例
if __name__ == "__main__":
    generator = NASMonitorScriptGenerator()
    
    # 示例配置
    task_name = "生产环境日志监控"
    log_paths = ["/var/log/syslog", "/var/log/messages"]
    rules = [
        {{
            "id": 1,
            "name": "OOM检测",
            "dsl": '"low memory" & "OOM_SCORE" & "victim"',
            "description": "内存不足导致的进程终止"
        }},
        {{
            "id": 2,
            "name": "磁盘空间不足",
            "dsl": '"No space left" | "disk full"',
            "description": "磁盘空间不足错误"
        }}
    ]
    email_recipients = ["admin@company.com"]
    device_info = {{
        "name": "生产NAS-01",
        "ip": "192.168.1.100",
        "username": "admin",
        "password": "password123"
    }}
    
    # 生成监控脚本
    script = generator.generate_monitor_script(
        task_name=task_name,
        log_paths=log_paths,
        rules=rules,
        email_recipients=email_recipients,
        device_info=device_info
    )
    
    print("生成的监控脚本:")
    print("-" * 50)
    print(script)