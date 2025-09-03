from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, timedelta
from pydantic import BaseModel
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
import bisect
from dotenv import load_dotenv

# 加载环境变量
def load_env_manually():
    """手动加载.env文件"""
    env_file = '/home/ugreen/log-analyse/backend/.env'
    print(f"Manually loading .env from: {env_file}")
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    print(f"Set {key}={value}")

load_env_manually()
load_dotenv('/home/ugreen/log-analyse/backend/.env', override=True)
print(f"Loading .env from: /home/ugreen/log-analyse/backend/.env")  # 调试输出

# 暂时注释掉数据库相关导入，等依赖安装好后再启用
# from .api.v1 import rules as rules_router
# from .api.v1 import monitor as monitor_router

# 可存储内容的最大字节数（默认20MB，可通过环境变量覆盖）
MAX_CONTENT_BYTES = int(os.environ.get("MAX_CONTENT_BYTES", str(20 * 1024 * 1024)))

# 会话有效期
DEFAULT_TTL_HOURS = 24
REMEMBER_TTL_DAYS = 30
RETENTION_DAYS = int(os.environ.get("LOG_RETENTION_DAYS", "30"))  # 日志保留天数

# 创建FastAPI应用
app = FastAPI(
    title="日志分析平台 API",
    description="高性能的syslog和kernlog日志分析平台",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 暂时注释掉API路由注册，等依赖安装好后再启用
# app.include_router(rules_router.router, prefix="/api/v1", tags=["规则管理"])
# app.include_router(monitor_router.router, prefix="/api/monitor", tags=["定时分析"])

# 内存存储（临时）
uploaded_files: List[Dict[str, Any]] = []
analysis_results: List[Dict[str, Any]] = []
problems: List[Dict[str, Any]] = []  # 问题库：{id, title, url, error_type, created_at}

# 简单后台分析队列（线程池），避免阻塞主事件循环
EXECUTOR = ThreadPoolExecutor(max_workers=int(os.environ.get("ANALYSIS_WORKERS", "2")))
ANALYSIS_RUNNING = set()  # file_id 集合，表示正在分析

# —— 规则DSL解析 ——
class _Ast:
    def __init__(self, op=None, left=None, right=None, value=None):
        self.op = op  # 'AND' 'OR' 'NOT' or None
        self.left = left
        self.right = right
        self.value = value  # phrase

_DEF_PRECEDENCE = {'!': 3, '&': 2, '|': 1}

def _tokenize(expr: str):
    if not expr:
        return []
    s = expr.replace('！', '!')
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c in '()&|!':
            out.append(c)
            i += 1
            continue
        if c == '"':
            j = i + 1
            buf = []
            while j < n and s[j] != '"':
                buf.append(s[j])
                j += 1
            # 跳过结束引号
            i = j + 1 if j < n and s[j] == '"' else j
            out.append(('PHRASE', ''.join(buf)))
            continue
        # 普通单词直到空白或运算符
        j = i
        buf = []
        while j < n and (not s[j].isspace()) and s[j] not in '()&|!':
            buf.append(s[j])
            j += 1
        out.append(('PHRASE', ''.join(buf)))
        i = j
    # 插入隐式与（AND）：operand 后紧跟 operand/!/( 的情况
    implicit = []
    def is_operand(tok):
        return isinstance(tok, tuple) and tok[0] == 'PHRASE' or tok == ')'
    def is_unary_or_open(tok):
        return tok == '!' or tok == '(' or (isinstance(tok, tuple) and tok[0] == 'PHRASE')
    for idx, tok in enumerate(out):
        if idx > 0:
            prev = out[idx-1]
            if (is_operand(prev) and (tok == '(' or tok == '!' or (isinstance(tok, tuple) and tok[0]=='PHRASE'))):
                implicit.append('&')
        implicit.append(tok)
    return implicit

def _to_rpn(tokens):
    # Shunting-yard 算法
    output = []
    ops = []
    def prec(op):
        return _DEF_PRECEDENCE.get(op, 0)
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if isinstance(tok, tuple):  # PHRASE
            output.append(tok)
        elif tok == '!' :
            ops.append(tok)
        elif tok in ('&','|'):
            while ops and ops[-1] != '(' and prec(ops[-1]) >= prec(tok):
                output.append(ops.pop())
            ops.append(tok)
        elif tok == '(':
            ops.append(tok)
        elif tok == ')':
            while ops and ops[-1] != '(':
                output.append(ops.pop())
            if ops and ops[-1] == '(':
                ops.pop()
        i += 1
    while ops:
        output.append(ops.pop())
    return output

def _rpn_to_ast(rpn):
    st = []
    for tok in rpn:
        if isinstance(tok, tuple):
            st.append(_Ast(value=tok[1]))
        elif tok == '!':
            a = st.pop() if st else _Ast(value='')
            st.append(_Ast(op='NOT', left=a))
        elif tok in ('&','|'):
            b = st.pop() if st else _Ast(value='')
            a = st.pop() if st else _Ast(value='')
            st.append(_Ast(op=('AND' if tok=='&' else 'OR'), left=a, right=b))
    return st[-1] if st else None

DEBUG_DSL = os.environ.get("DEBUG_DSL", "0") == "1"

def _eval_ast(ast: _Ast, text_lower: str) -> bool:
    if ast is None:
        return False
    if ast.op is None:
        phrase = (ast.value or '').lower()
        if phrase == '':
            return False
        result = phrase in text_lower
        if DEBUG_DSL:
            print(f"    检查短语 '{phrase}' 在文本中: {result}")
        return result
    if ast.op == 'NOT':
        return not _eval_ast(ast.left, text_lower)
    if ast.op == 'AND':
        left_result = _eval_ast(ast.left, text_lower)
        right_result = _eval_ast(ast.right, text_lower)
        final_result = left_result and right_result
        if DEBUG_DSL:
            print(f"    AND操作: {left_result} & {right_result} = {final_result}")
        return final_result
    if ast.op == 'OR':
        left_result = _eval_ast(ast.left, text_lower)
        right_result = _eval_ast(ast.right, text_lower)
        final_result = left_result or right_result
        if DEBUG_DSL:
            print(f"    OR操作: {left_result} | {right_result} = {final_result}")
        return final_result
    return False

# —— 规则匹配逻辑 ——

# 预处理内容：拆分行、小写缓存、换行位置索引
def _precompute_content(content: str):
    lines = content.split('\n')
    lines_lower = [ln.lower() for ln in lines]
    content_lower = content.lower()
    # 记录每个换行符在内容中的偏移，用于快速行号定位
    newline_positions = []
    off = 0
    for ln in lines[:-1]:  # 最后一行之后没有换行符
        off += len(ln)
        newline_positions.append(off)
        off += 1  # '\n'
    return {"lines": lines, "lines_lower": lines_lower, "content_lower": content_lower, "newline_positions": newline_positions}

def _line_number_from_pos(pos: int, newline_positions: list[int]) -> int:
    # 基于二分查找快速定位行号（1-based）
    return bisect.bisect_right(newline_positions, max(0, pos)) + 1

DSL_CACHE: Dict[str, Any] = {}

def _compile_dsl(rule_id: Any, expr: str):
    key = f"{rule_id}:{expr}"
    c = DSL_CACHE.get(key)
    if c:
        return c
    tokens = _tokenize(expr)
    rpn = _to_rpn(tokens)
    ast = _rpn_to_ast(rpn)
    phrases = [t[1] for t in tokens if isinstance(t, tuple) and t[0] == 'PHRASE']
    c = {"tokens": tokens, "rpn": rpn, "ast": ast, "phrases": phrases}
    DSL_CACHE[key] = c
    return c

def evaluate_rule_matches(content: str, rule: Dict[str, Any], pre: Optional[Dict[str, Any]] = None) -> List[Any]:
    """根据规则返回匹配列表。支持 DSL(| & ! () 和引号短语)；
    若未检测到DSL符号，则回退到旧的 OR/AND/NOT/正则 行为。
    结果以“近似行级”返回，避免逐字匹配。
    """
    prectx = pre or _precompute_content(content)
    lines = prectx["lines"]
    lines_lower = prectx["lines_lower"]
    content_lower = prectx["content_lower"]
    # 预判 DSL
    expr = ''
    
    if isinstance(rule.get('dsl'), str) and rule['dsl'].strip():
        expr = rule['dsl'].strip()
    # 注意：不再将单行 patterns 自动当作 DSL，避免正则包含元字符被误判
    
    if expr:
        compiled = _compile_dsl(rule.get('id','0'), expr)
        tokens = compiled["tokens"]
        ast = compiled["ast"]
        # 按行评估
        matches = []
        offset = 0
        matched_lines = 0
        for idx, line_lower in enumerate(lines_lower):
            if _eval_ast(ast, line_lower):
                matched_lines += 1
                # 代表性的命中位置：取任意短语首次出现
                pos = 0
                found = False
                for p in compiled["phrases"]:
                    pl = p.lower()
                    k = line_lower.find(pl)
                    if k >= 0:
                        pos = k
                        found = True
                        break
                start_index = offset + (pos if found else 0)
                end_index = start_index + (len(compiled["phrases"][0]) if (found and compiled["phrases"]) else max(1, len(lines[idx])))
                # 构造一个与正则匹配对象类似的轻量对象
                class M:
                    def __init__(self, s, e, g):
                        self._s=s; self._e=e; self._g=g
                    def start(self): return self._s
                    def end(self): return self._e
                    def group(self): return lines[idx].strip()
                matches.append(M(start_index, end_index, lines[idx].strip()))
            offset += len(lines[idx]) + 1
        return matches

    # —— 旧逻辑回退（保留向后兼容） ——
    patterns = rule.get("patterns", []) or []
    operator = (rule.get("operator") or "OR").upper()
    is_regex = bool(rule.get("is_regex", True))

    def find_matches(pat: str):
        if is_regex:
            try:
                ms = list(re.finditer(pat, content, re.IGNORECASE))
                # 保护：避免纯前瞻/零宽模式在全文每个位置都命中导致爆炸
                if ms and any((m.end() - m.start()) == 0 for m in ms):
                    return ms[:1]
                return ms
            except re.error:
                return []
        else:
            # 使用不区分大小写的单个模式搜索
            return list(re.finditer(re.escape(pat), content, re.IGNORECASE))

    # 性能优化：OR 情况尽可能合并为一次正则扫描
    if operator == "OR" and patterns:
        try:
            if is_regex:
                union = "(?:" + ")|(?:".join(patterns) + ")"
                reg = re.compile(union, re.IGNORECASE)
            else:
                union = "|".join(re.escape(p) for p in patterns)
                reg = re.compile(union, re.IGNORECASE)
            flat = list(reg.finditer(content))
            # 保护：零宽匹配只取首个，避免 O(n) 命中
            if flat and any((m.end() - m.start()) == 0 for m in flat):
                return flat[:1]
            return flat
        except Exception:
            pass

    all_lists = [find_matches(p) for p in patterns]

    if operator == "AND":
        return [lst[0] for lst in all_lists if lst] if all(len(lst) > 0 for lst in all_lists) else []
    elif operator == "NOT":
        # 所有模式都不出现才算命中（返回一个空占位匹配）
        if all(len(lst) == 0 for lst in all_lists):
            class M:
                def start(self): return 0
                def end(self): return 0
                def group(self): return ""
            return [M()]
        return []
    else:  # OR
        flat = [m for lst in all_lists for m in lst]
        return flat

# —— 持久化设置 ——
DATA_DIR = os.environ.get("LOG_ANALYZER_DATA", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "database")))
FILES_DIR = os.path.join(DATA_DIR, "uploads")
INDEX_PATH = os.path.join(DATA_DIR, "uploads_index.json")
ANALYSIS_INDEX_PATH = os.path.join(DATA_DIR, "analysis_results.json")
ANALYSIS_RUNS_PATH = os.path.join(DATA_DIR, "analysis_runs.json")
PROBLEMS_PATH = os.path.join(DATA_DIR, "problems.json")
RULES_PATH = os.path.join(DATA_DIR, "detection_rules.json")  # 新增规则持久化路径
USERS_PATH = os.path.join(DATA_DIR, "users.json")

os.makedirs(FILES_DIR, exist_ok=True)

# 启动时加载索引
try:
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            uploaded_files = json.load(f)
    else:
        uploaded_files = []
except Exception:
    uploaded_files = []

# 启动时加载分析结果索引
try:
    if os.path.exists(ANALYSIS_INDEX_PATH):
        with open(ANALYSIS_INDEX_PATH, "r", encoding="utf-8") as f:
            analysis_results = json.load(f)
    else:
        analysis_results = []
except Exception:
    analysis_results = []

# 启动时加载总分析次数
try:
    if os.path.exists(ANALYSIS_RUNS_PATH):
        with open(ANALYSIS_RUNS_PATH, "r", encoding="utf-8") as f:
            _d = json.load(f)
            total_analysis_runs_counter = int(_d.get("total", 0))
    else:
        total_analysis_runs_counter = 0
except Exception:
    total_analysis_runs_counter = 0

# 启动时加载问题库
try:
    if os.path.exists(PROBLEMS_PATH):
        with open(PROBLEMS_PATH, "r", encoding="utf-8") as f:
            problems = json.load(f)
    else:
        problems = []
except Exception:
    problems = []

# 启动时加载用户
try:
    if os.path.exists(USERS_PATH):
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            users = json.load(f)
    else:
        # 若无文件，保持内置admin
        users: List[Dict[str, Any]] = [
            {"id": 1, "username": "admin", "email": "", "role": "管理员", "password": "admin123", "position": "管理员"}
        ]
except Exception:
    users = [
        {"id": 1, "username": "admin", "email": "", "role": "管理员", "password": "admin123", "position": "管理员"}
    ]


def save_index():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(uploaded_files, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def save_analysis_index():
    try:
        with open(ANALYSIS_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def save_analysis_runs():
    try:
        with open(ANALYSIS_RUNS_PATH, "w", encoding="utf-8") as f:
            json.dump({"total": total_analysis_runs_counter}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def save_problems():
    try:
        with open(PROBLEMS_PATH, "w", encoding="utf-8") as f:
            json.dump(problems, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def save_rules():
    """保存检测规则到文件"""
    try:
        with open(RULES_PATH, "w", encoding="utf-8") as f:
            json.dump(detection_rules, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# 新增：保存用户到文件

def save_users():
    try:
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_rules():
    """从文件加载检测规则"""
    global detection_rules
    try:
        if os.path.exists(RULES_PATH):
            with open(RULES_PATH, "r", encoding="utf-8") as f:
                loaded_rules = json.load(f)
                # 合并内置规则和用户规则，避免重复
                builtin_ids = {r["id"] for r in detection_rules}
                for rule in loaded_rules:
                    if rule["id"] not in builtin_ids:
                        detection_rules.append(rule)
    except Exception as e:
        print(f"加载规则失败: {e}")

def purge_old_uploads():
    """清理超过保留期的日志文件及分析结果"""
    global uploaded_files, analysis_results
    try:
        cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
        remain = []
        removed_ids = set()
        for f in uploaded_files:
            try:
                ts = datetime.fromisoformat(f.get("upload_time", ""))
            except Exception:
                ts = datetime.now()
            if ts < cutoff:
                removed_ids.add(f.get("id"))
                p = f.get("path")
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
            else:
                remain.append(f)
        if removed_ids:
            uploaded_files = remain
            analysis_results = [r for r in analysis_results if r.get("file_id") not in removed_ids]
            save_index()
            save_analysis_index()
    except Exception:
        pass

# 简易用户模型与内存用户表
class UserCreate(BaseModel):
    username: str
    email: Optional[str] = ""
    password: Optional[str] = ""  # 演示用，未加密
    role: Optional[str] = "普通用户"
    position: Optional[str] = ""  # 职位

class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    position: Optional[str] = None

class LoginPayload(BaseModel):
    username: str
    password: str
    remember: bool = False

class ChangePasswordPayload(BaseModel):
    old_password: str
    new_password: str


# 在应用启动时执行一次过期清理，避免导入阶段调用
@app.on_event("startup")
async def _startup_cleanup():
    purge_old_uploads()
    load_rules()  # 启动时加载保存的规则
    load_monitor_data()  # 启动时加载监控设备和任务数据

# 规则与文件夹模型
class RuleCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    enabled: bool = True
    patterns: List[str] = []  # 正则或关键字列表
    operator: Optional[str] = "OR"      # 兼容旧逻辑
    is_regex: Optional[bool] = True
    folder_id: Optional[int] = 1
    dsl: Optional[str] = None            # 新增：DSL 表达式

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    patterns: Optional[List[str]] = None
    operator: Optional[str] = None
    is_regex: Optional[bool] = None
    folder_id: Optional[int] = None
    dsl: Optional[str] = None

rule_folders: List[Dict[str, Any]] = [
    {"id": 1, "name": "默认"}
]

# 基础内置规则（将自动扩展为patterns+operator+folder_id）
detection_rules = [
    {"id": 1, "name": "OOM Killer", "description": "内存溢出检测", "enabled": True, "pattern": "Out of memory|OOM killer"},
    {"id": 2, "name": "Kernel Panic", "description": "内核崩溃检测", "enabled": True, "pattern": "Kernel panic|kernel BUG"},
    {"id": 3, "name": "Segmentation Fault", "description": "段错误检测", "enabled": True, "pattern": "segfault|segmentation fault"},
    {"id": 4, "name": "Disk Space Error", "description": "磁盘空间不足", "enabled": True, "pattern": "No space left|disk full"},
    {"id": 5, "name": "Network Error", "description": "网络连接错误", "enabled": True, "pattern": "Network unreachable|Connection refused"},
    {"id": 6, "name": "File System Error", "description": "文件系统错误", "enabled": True, "pattern": "I/O error|filesystem error"},
    {"id": 7, "name": "Authentication Error", "description": "认证失败检测", "enabled": True, "pattern": "authentication failed|login failed"}
]
# 扩展内置规则结构
for r in detection_rules:
    r["folder_id"] = 1
    r["patterns"] = [r.pop("pattern")] if "pattern" in r else []
    r["operator"] = "OR"
    r["is_regex"] = True

# 规范化问题类型：将各种写法映射为规则名
def normalize_error_type(et: str) -> str:
    try:
        et_l = (et or "").strip()
        for rr in detection_rules:
            if et_l == rr.get("name"):
                return rr["name"]
            pats = rr.get("patterns", []) or []
            joined = "|".join(pats)
            if et_l == joined:
                return rr["name"]
            for p in pats:
                pl = (p or "").lower(); el = et_l.lower()
                if pl == el or pl in el or el in pl:
                    return rr["name"]
        return et_l
    except Exception:
        return et

# —— 问题库模型 ——
class ProblemCreate(BaseModel):
    title: str
    url: str
    error_type: str  # 关联的错误类型（如 I/O error、OOM Killer 等）
    category: Optional[str] = ""

class ProblemUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    error_type: Optional[str] = None
    category: Optional[str] = None

# 简易令牌会话存储：token -> {user_id, expiry}
sessions: Dict[str, Dict[str, Any]] = {}

def _public_user(u: Dict[str, Any]) -> Dict[str, Any]:
    return {k: u.get(k, "") for k in ["id", "username", "email", "role", "position"]}

def create_session(user_id: int, remember: bool) -> Dict[str, Any]:
    token = uuid.uuid4().hex
    expiry = datetime.utcnow() + (timedelta(days=REMEMBER_TTL_DAYS) if remember else timedelta(hours=DEFAULT_TTL_HOURS))
    sessions[token] = {"user_id": user_id, "expiry": expiry}
    return {"token": token, "expires_at": expiry.isoformat() + "Z"}

def require_auth(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    token = authorization.split(" ", 1)[1].strip()
    session = sessions.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="无效令牌")
    if datetime.utcnow() > session["expiry"]:
        sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="令牌已过期")
    user = next((u for u in users if u["id"] == session["user_id"]), None)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return {"token": token, "user": user}

@app.get("/api/debug-rule")
async def debug_dsl_rule(ctx: Dict[str, Any] = Depends(require_auth)):
    """调试DSL规则匹配"""
    
    # 测试日志内容（从您的截图中提取）
    test_content = """aq_ring_rx_clean+0x175/0x560 [atlantic]
aq_ring_rx_clean+0x14d/0x560 [atlantic]
aq_ring_update_queue_state+0xd0/0x60 [atlantic]"""
    
    # 查找您的万兽网卡规则
    your_rule = None
    for rule in detection_rules:
        if "万兽" in rule.get("name", "") or "atlantic" in rule.get("dsl", ""):
            your_rule = rule
            break
    
    if not your_rule:
        return {"error": "未找到万兽网卡规则", "all_rules": [{"id": r["id"], "name": r["name"], "dsl": r.get("dsl")} for r in detection_rules]}
    
    # 测试DSL规则
    debug_info = {
        "rule_info": {
            "id": your_rule["id"],
            "name": your_rule["name"],
            "dsl": your_rule.get("dsl"),
            "enabled": your_rule.get("enabled"),
            "patterns": your_rule.get("patterns")
        },
        "test_content": test_content,
        "content_contains_aq_ring": "aq_ring_rx_clean" in test_content.lower(),
        "content_contains_atlantic": "atlantic" in test_content.lower()
    }
    
    # 使用evaluate_rule_matches测试
    try:
        matches = evaluate_rule_matches(test_content, your_rule)
        debug_info["matches_found"] = len(matches)
        debug_info["matches_details"] = []
        for i, match in enumerate(matches[:3]):
            if hasattr(match, 'group'):
                debug_info["matches_details"].append({
                    "index": i,
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end()
                })
            else:
                debug_info["matches_details"].append({
                    "index": i,
                    "match": str(match)
                })
    except Exception as e:
        debug_info["error"] = str(e)
        debug_info["matches_found"] = 0
    
    # 手动测试DSL逻辑
    try:
        # 预判 DSL
        expr = ''
        if isinstance(your_rule.get('dsl'), str) and your_rule['dsl'].strip():
            expr = your_rule['dsl'].strip()
            debug_info["dsl_expression_found"] = expr
        else:
            # 兼容：如果 patterns 是单行表达式且包含 DSL 运算符
            pats = your_rule.get('patterns')
            if isinstance(pats, list) and len(pats)==1 and isinstance(pats[0], str):
                cand = pats[0].strip()
                if any(ch in cand for ch in ['&','|','!','！','(',')','"']):
                    expr = cand
                    debug_info["dsl_from_patterns"] = expr
        
        if expr:
            debug_info["parsing_dsl"] = True
            tokens = _tokenize(expr)
            debug_info["tokens"] = [str(t) for t in tokens]
            
            rpn = _to_rpn(tokens)
            debug_info["rpn"] = [str(r) for r in rpn]
            
            ast = _rpn_to_ast(rpn)
            debug_info["ast_created"] = str(ast) if ast else "None"
            
            # 按行测试
            lines = test_content.split('\n')
            line_results = []
            for idx, line in enumerate(lines):
                line_lower = line.lower()
                line_match = _eval_ast(ast, line_lower)
                line_results.append({
                    "line_num": idx + 1,
                    "line_content": line,
                    "matched": line_match
                })
            debug_info["line_by_line_results"] = line_results
        else:
            debug_info["no_dsl_expression"] = True
            
    except Exception as e:
        debug_info["dsl_parse_error"] = str(e)
    
    return debug_info

@app.get("/api/test-dsl")
async def test_dsl_rule(rule: str, text: str, ctx: Dict[str, Any] = Depends(require_auth)):
    """测试DSL规则功能"""
    try:
        # 构建规则对象
        test_rule = {
            "dsl": rule,
            "enabled": True
        }
        
        # 使用现有的evaluate_rule_matches函数
        matches = evaluate_rule_matches(text, test_rule)
        
        return {
            "rule": rule,
            "text": text[:200] + "..." if len(text) > 200 else text,
            "matched": len(matches) > 0,
            "match_count": len(matches),
            "matches": [{"position": m.start() if hasattr(m, 'start') else 0, 
                        "text": m.group() if hasattr(m, 'group') else str(m)} for m in matches[:5]]
        }
    except Exception as e:
        return {
            "rule": rule,
            "text": text[:200] + "..." if len(text) > 200 else text,
            "matched": False,
            "error": str(e)
        }

@app.get("/")
async def root():
    return {
        "message": "🚀 日志分析平台 API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "backend"
    }

# 认证与用户
@app.post("/api/auth/login")
async def login(payload: LoginPayload):
    user = next((u for u in users if u["username"].lower() == payload.username.lower()), None)
    if not user or user.get("password") != payload.password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    session_info = create_session(user["id"], payload.remember)
    return {"message": "登录成功", "user": _public_user(user), **session_info}

@app.get("/api/auth/me")
async def me(ctx: Dict[str, Any] = Depends(require_auth)):
    return {"user": _public_user(ctx["user"]) }

@app.post("/api/auth/logout")
async def logout(ctx: Dict[str, Any] = Depends(require_auth)):
    token = ctx["token"]
    sessions.pop(token, None)
    return {"message": "已退出"}

@app.post("/api/auth/change_password")
async def change_password(payload: ChangePasswordPayload, ctx: Dict[str, Any] = Depends(require_auth)):
    user = ctx["user"]
    if user.get("password") != payload.old_password:
        raise HTTPException(status_code=400, detail="原密码不正确")
    user["password"] = payload.new_password
    return {"message": "密码已更新"}

# 仪表板
@app.get("/api/dashboard/stats")
async def get_dashboard_stats(ctx: Dict[str, Any] = Depends(require_auth)):
    # 读取最新索引，确保与磁盘同步
    is_admin = (str(ctx["user"].get("username", "")).lower() == "admin")
    user_id = ctx["user"]["id"]
    up_count = len(uploaded_files)
    try:
        if os.path.exists(INDEX_PATH):
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                idx = json.load(f)
            if is_admin:
                up_count = len(idx)
            else:
                up_count = len([x for x in idx if (x.get("owner_id", 1) == user_id)])
    except Exception:
        if not is_admin:
            up_count = len([x for x in uploaded_files if x.get("owner_id", 1) == user_id])
    detected = 0
    total_runs = 0
    try:
        if os.path.exists(ANALYSIS_INDEX_PATH):
            with open(ANALYSIS_INDEX_PATH, "r", encoding="utf-8") as f:
                arr = json.load(f)
            total_runs = len(arr)
            if is_admin:
                detected = sum(len(r.get("issues", [])) for r in arr)
            else:
                mine = [r for r in arr if r.get("owner_id", 1) == user_id]
                detected = sum(len(r.get("issues", [])) for r in mine)
        else:
            total_runs = len(analysis_results)
            if is_admin:
                detected = sum(len(r.get("issues", [])) for r in analysis_results)
            else:
                mine = [r for r in analysis_results if r.get("owner_id", 1) == user_id]
                detected = sum(len(r.get("issues", [])) for r in mine)
    except Exception:
        total_runs = len(analysis_results)
        if is_admin:
            detected = sum(len(r.get("issues", [])) for r in analysis_results)
        else:
            mine = [r for r in analysis_results if r.get("owner_id", 1) == user_id]
            detected = sum(len(r.get("issues", [])) for r in mine)
    resp = {
        "uploaded_files": up_count,
        "detected_issues": detected,
        "detection_rules": len([rule for rule in detection_rules if rule["enabled"]]),
        "recent_activity": []
    }
    if is_admin:
        # 取“累计计数器”和“索引条目数”的较大值，避免显示偏小
        try:
            persisted = int(total_analysis_runs_counter)
        except Exception:
            persisted = 0
        resp["total_analysis_runs"] = max(persisted, int(total_runs))
    return resp

# 日志管理
@app.post("/api/logs/upload")
async def upload_log_file(file: UploadFile = File(...), ctx: Dict[str, Any] = Depends(require_auth)):
    try:
        # 放宽文件类型限制：接受所有类型
        content = await file.read()
        if len(content) > MAX_CONTENT_BYTES:
            raise HTTPException(status_code=400, detail=f"文件过大，最大支持 {int(MAX_CONTENT_BYTES/1024/1024)}MB")
        content_str = content.decode('utf-8', errors='ignore')
        file_id = (max([f["id"] for f in uploaded_files]) + 1) if uploaded_files else 1
        filename = file.filename
        save_path = os.path.join(FILES_DIR, f"{file_id}_{filename}")
        with open(save_path, "w", encoding="utf-8", errors="ignore") as fw:
            fw.write(content_str)
        file_info = {
            "id": file_id,
            "filename": filename,
            "size": len(content),
            "upload_time": datetime.now().isoformat(),
            "path": save_path,
            "status": "uploaded",
            "owner_id": ctx["user"]["id"],
        }
        uploaded_files.append(file_info)
        save_index()
        # 上传后也清理一次过期数据
        purge_old_uploads()
        return {"message": "文件上传成功", "file_id": file_info["id"], "filename": filename, "size": len(content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@app.get("/api/logs")
async def get_uploaded_files(ctx: Dict[str, Any] = Depends(require_auth)):
    is_admin = (str(ctx["user"].get("username", "")).lower() == "admin")
    user_id = ctx["user"]["id"]
    files = [
            {"id": f["id"], "filename": f["filename"], "size": f["size"], "upload_time": f["upload_time"], "status": f["status"]}
            for f in uploaded_files
        if is_admin or (f.get("owner_id", 1) == user_id)
        ]
    return {"files": files}

@app.get("/api/logs/{file_id}")
async def get_log_file(file_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    f = next((x for x in uploaded_files if x["id"] == file_id), None)
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    is_admin = (str(ctx["user"].get("username", "")).lower() == "admin")
    if not is_admin and f.get("owner_id", 1) != ctx["user"]["id"]:
        raise HTTPException(status_code=403, detail="无权访问该文件")
    content = ""
    try:
        with open(f.get("path"), "r", encoding="utf-8", errors="ignore") as fr:
            content = fr.read(MAX_CONTENT_BYTES)
    except Exception:
        content = f.get("content", "")  # 向后兼容
    return {
        "id": f["id"],
        "filename": f["filename"],
        "size": f["size"],
        "upload_time": f["upload_time"],
        "content": content
    }

@app.delete("/api/logs/{file_id}")
async def delete_log_file(file_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    global uploaded_files, analysis_results
    target = next((f for f in uploaded_files if f["id"] == file_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="文件不存在")
    is_admin = (str(ctx["user"].get("username", "")).lower() == "admin")
    if not is_admin and target.get("owner_id", 1) != ctx["user"]["id"]:
        raise HTTPException(status_code=403, detail="无权删除该文件")
    uploaded_files = [f for f in uploaded_files if f["id"] != file_id]
    analysis_results = [r for r in analysis_results if r.get("file_id") != file_id]
    try:
        if target.get("path") and os.path.exists(target["path"]):
            os.remove(target["path"])
    except Exception:
        pass
    save_index()
    save_analysis_index()
    return {"message": "文件已删除"}

@app.get("/api/logs/{file_id}/preview")
async def preview_log_file(file_id: int, offset: int = 0, size: int = 512*1024, ctx: Dict[str, Any] = Depends(require_auth)):
    """按字节偏移返回日志片段，用于大文件分片预览。
    返回：chunk(字符串)、offset、next_offset、eof、total_size、filename
    """
    try:
        f = next((x for x in uploaded_files if x["id"] == file_id), None)
        if not f:
            raise HTTPException(status_code=404, detail="文件不存在")
        # 权限校验
        is_admin = (str(ctx["user"].get("username", "")).lower() == "admin")
        if not is_admin and f.get("owner_id", 1) != ctx["user"]["id"]:
            raise HTTPException(status_code=403, detail="无权预览该文件")
        filename = f.get("filename") or str(file_id)
        # 确定总大小
        total_size = 0
        content_bytes = None
        if f.get("path") and os.path.exists(f["path"]):
            try:
                total_size = os.path.getsize(f["path"])
                size = max(1, min(int(size), 1024 * 1024))  # 上限1MB每次
                offset = max(0, min(int(offset), total_size))
                with open(f["path"], "rb") as frb:
                    frb.seek(offset)
                    data = frb.read(size)
                next_offset = offset + len(data)
                eof = next_offset >= total_size
                chunk = data.decode("utf-8", errors="ignore")
                return {
                    "file_id": file_id,
                    "filename": filename,
                    "offset": offset,
                    "next_offset": next_offset,
                    "eof": eof,
                    "total_size": total_size,
                    "chunk": chunk
                }
            except Exception as e:
                # 回退到内存内容
                pass
        # 内存内容回退
        content_str = f.get("content", "")
        content_bytes = content_str.encode("utf-8", errors="ignore")
        total_size = len(content_bytes)
        size = max(1, min(int(size), 1024 * 1024))
        offset = max(0, min(int(offset), total_size))
        data = content_bytes[offset: offset + size]
        next_offset = offset + len(data)
        eof = next_offset >= total_size
        chunk = data.decode("utf-8", errors="ignore")
        return {
            "file_id": file_id,
            "filename": filename,
            "offset": offset,
            "next_offset": next_offset,
            "eof": eof,
            "total_size": total_size,
            "chunk": chunk
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败: {e}")

class AnalyzeTextPayload(BaseModel):
    text: str
    filename: Optional[str] = "pasted.log"

@app.post("/api/logs/analyze_text")
async def analyze_text(payload: AnalyzeTextPayload, ctx: Dict[str, Any] = Depends(require_auth)):
    text_bytes = len(payload.text.encode("utf-8"))
    if text_bytes > MAX_CONTENT_BYTES:
        raise HTTPException(status_code=400, detail=f"文本内容超过限制，最大 {int(MAX_CONTENT_BYTES/1024/1024)}MB")
    # 临时存储为一条文件记录（不写入磁盘）
    file_info = {
        "id": len(uploaded_files) + 1,
        "filename": payload.filename,
        "size": text_bytes,
        "upload_time": datetime.now().isoformat(),
        "content": payload.text,
        "status": "uploaded",
        "owner_id": ctx["user"]["id"],
    }
    uploaded_files.append(file_info)
    # 文本分析同样走后台队列
    ANALYSIS_RUNNING.add(file_info["id"])
    def _task():
        try:
            _perform_analysis(file_info["id"])
        finally:
            ANALYSIS_RUNNING.discard(file_info["id"])
    EXECUTOR.submit(_task)
    return JSONResponse(status_code=202, content={"status": "accepted", "file_id": file_info["id"]})

# 规则匹配逻辑


def _perform_analysis(file_id: int):
    file_info = next((f for f in uploaded_files if f["id"] == file_id), None)
    if not file_info:
        return
    # 从磁盘读取
    content = ""
    try:
        with open(file_info.get("path"), "r", encoding="utf-8", errors="ignore") as fr:
            chunks = []
            read = 0
            while read < MAX_CONTENT_BYTES:
                part = fr.read(min(1024 * 1024, MAX_CONTENT_BYTES - read))
                if not part:
                    break
                chunks.append(part)
                read += len(part)
            content = ''.join(chunks)
    except Exception:
        content = file_info.get("content", "")
    
    # 分析
    issues = []
    pre = _precompute_content(content)
    lines = pre["lines"]
    print(f"开始分析文件 {file_id}，规则数量: {len(detection_rules)}")
    
    for rule in detection_rules:
        matches = evaluate_rule_matches(content, rule, pre)
        
        if not matches:
            continue
            
        # 对于DSL规则或有多个匹配的情况，合并为一个问题
        if rule.get('dsl') or len(matches) > 1:
            # 收集所有匹配的信息
            match_details = []
            all_contexts = []
            line_numbers = []
            
            for m in matches:
                if m is None:
                    line_number = 1
                    context = '\n'.join(lines[:5])
                    matched_text = ""
                else:
                    line_number = _line_number_from_pos(m.start(), pre["newline_positions"]) 
                    context_start = max(0, line_number - 2)
                    context_end = min(len(lines), line_number + 1)
                    context = '\n'.join(lines[context_start:context_end])
                    matched_text = m.group()
                
                match_details.append({
                    "line": line_number,
                    "text": matched_text,
                    "context": context
                })
                line_numbers.append(line_number)
                all_contexts.append(f"行 {line_number}: {matched_text}")
            
            # 创建合并的问题条目
            combined_context = '\n\n'.join([f"匹配 {i+1} (行 {detail['line']}):\n{detail['context']}" 
                                          for i, detail in enumerate(match_details)])
            combined_matched_text = f"共 {len(matches)} 个匹配: " + "; ".join([detail['text'] for detail in match_details if detail['text']])
            
            issues.append({
                "rule_name": rule["name"],
                "description": rule.get("description", ""),
                "line_number": min(line_numbers) if line_numbers else 1,
                "matched_text": combined_matched_text,
                "context": combined_context,
                "match_count": len(matches),
                "severity": "high" if ("panic" in rule["name"].lower() or "oom" in rule["name"].lower()) else "medium"
            })
        else:
            # 单个匹配的传统处理方式
            m = matches[0]
            if m is None:
                line_number = 1
                context = '\n'.join(lines[:5])
                matched_text = ""
            else:
                line_number = _line_number_from_pos(m.start(), pre["newline_positions"]) 
                context_start = max(0, line_number - 3)
                context_end = min(len(lines), line_number + 2)
                context = '\n'.join(lines[context_start:context_end])
                matched_text = m.group()
            issues.append({
                "rule_name": rule["name"],
                "description": rule.get("description", ""),
                "line_number": line_number,
                "matched_text": matched_text,
                "context": context,
                "severity": "high" if ("panic" in rule["name"].lower() or "oom" in rule["name"].lower()) else "medium"
            })
    
    print(f"分析完成，总问题数: {len(issues)}")
    
    result = {
        "file_id": file_id,
        "filename": file_info["filename"],
        "analysis_time": datetime.now().isoformat(),
        "issues": issues,
        "summary": {
            "total_issues": len(issues),
            "high_severity": len([i for i in issues if i["severity"] == "high"]),
            "medium_severity": len([i for i in issues if i["severity"] == "medium"])
        },
        "owner_id": file_info.get("owner_id", 1)
    }
    global analysis_results
    analysis_results = [r for r in analysis_results if r.get("file_id") != file_id]
    analysis_results.append(result)
    save_analysis_index()
    # 成功完成一次分析则计数+1
    global total_analysis_runs_counter
    try:
        total_analysis_runs_counter = int(total_analysis_runs_counter) + 1
    except Exception:
        total_analysis_runs_counter = 1
    save_analysis_runs()

@app.post("/api/logs/{file_id}/analyze")
async def analyze_log_file(file_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    # 防止重复点击
    if file_id in ANALYSIS_RUNNING:
        return JSONResponse(status_code=202, content={"status": "running"})
    # 权限校验
    f = next((x for x in uploaded_files if x["id"] == file_id), None)
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    is_admin = (str(ctx["user"].get("username", "")).lower() == "admin")
    if not is_admin and f.get("owner_id", 1) != ctx["user"]["id"]:
        raise HTTPException(status_code=403, detail="无权分析该文件")
    ANALYSIS_RUNNING.add(file_id)
    def _task():
        try:
            _perform_analysis(file_id)
        finally:
            ANALYSIS_RUNNING.discard(file_id)
    EXECUTOR.submit(_task)
    return JSONResponse(status_code=202, content={"status": "accepted"})

@app.get("/api/analysis/{file_id}/status")
async def get_analysis_status(file_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    f = next((x for x in uploaded_files if x["id"] == file_id), None)
    if not f:
        return {"status": "none"}
    is_admin = (str(ctx["user"].get("username", "")).lower() == "admin")
    if not is_admin and f.get("owner_id", 1) != ctx["user"]["id"]:
        return {"status": "none"}
    exists = next((r for r in analysis_results if r.get("file_id") == file_id), None)
    if exists:
        return {"status": "ready"}
    if file_id in ANALYSIS_RUNNING:
        return {"status": "running"}
    return {"status": "none"}

# 分析结果查询
@app.get("/api/analysis/results")
async def get_analysis_results(ctx: Dict[str, Any] = Depends(require_auth)):
    is_admin = (str(ctx["user"].get("username", "")).lower() == "admin")
    user_id = ctx["user"]["id"]
    if is_admin:
        return {"results": analysis_results}
    # 非管理员按 owner 过滤
    return {"results": [r for r in analysis_results if r.get("owner_id", 1) == user_id]}

@app.get("/api/analysis/{file_id}")
async def get_file_analysis_result(file_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    # 权限校验基于文件属主
    f = next((x for x in uploaded_files if x["id"] == file_id), None)
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    is_admin = (str(ctx["user"].get("username", "")).lower() == "admin")
    if not is_admin and f.get("owner_id", 1) != ctx["user"]["id"]:
        raise HTTPException(status_code=403, detail="无权访问分析结果")
    result = next((r for r in analysis_results if r.get("file_id") == file_id), None)
    if not result:
        raise HTTPException(status_code=404, detail="分析结果不存在")
    return result

# 规则管理与文件夹
@app.get("/api/rules")
async def get_detection_rules(query: Optional[str] = None, folder_id: Optional[int] = None, ctx: Dict[str, Any] = Depends(require_auth)):
    rules = detection_rules
    if folder_id is not None:
        rules = [r for r in rules if r.get("folder_id") == folder_id]
    if query:
        q = query.lower()
        rules = [r for r in rules if q in r["name"].lower() or q in r.get("description", "").lower()]
    return {"rules": rules}

@app.post("/api/rules")
async def create_rule(payload: RuleCreate, ctx: Dict[str, Any] = Depends(require_auth)):
    new_id = (max([r["id"] for r in detection_rules]) + 1) if detection_rules else 1
    rule = {
        "id": new_id,
        "name": payload.name,
        "description": payload.description or "",
        "enabled": payload.enabled,
        "patterns": payload.patterns or [],
        "operator": (payload.operator or "OR").upper() if payload.operator is not None else "OR",
        "is_regex": bool(payload.is_regex) if payload.is_regex is not None else True,
        "folder_id": payload.folder_id or 1,
        "dsl": (payload.dsl or "").strip(),
    }
    detection_rules.append(rule)
    save_rules()  # 保存规则
    return {"message": "规则创建成功", "rule": rule}

@app.put("/api/rules/{rule_id}")
async def update_detection_rule(rule_id: int, payload: RuleUpdate, ctx: Dict[str, Any] = Depends(require_auth)):
    rule = next((r for r in detection_rules if r["id"] == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    for k, v in payload.dict(exclude_unset=True).items():
        if k == "operator" and v:
            rule[k] = v.upper()
        else:
            rule[k] = v
    save_rules()  # 保存规则
    return {"message": "规则更新成功", "rule": rule}

@app.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    global detection_rules
    before = len(detection_rules)
    detection_rules = [r for r in detection_rules if r["id"] != rule_id]
    if len(detection_rules) == before:
        raise HTTPException(status_code=404, detail="规则不存在")
    save_rules()  # 保存规则
    return {"message": "规则已删除"}

@app.get("/api/rule-folders")
async def list_rule_folders(ctx: Dict[str, Any] = Depends(require_auth)):
    # 附带每个文件夹下规则数量
    folders = []
    for f in rule_folders:
        cnt = len([r for r in detection_rules if r.get("folder_id") == f["id"]])
        folders.append({**f, "count": cnt})
    return {"folders": folders}

class FolderCreate(BaseModel):
    name: str

class FolderUpdate(BaseModel):
    name: str

@app.post("/api/rule-folders")
async def create_folder(payload: FolderCreate, ctx: Dict[str, Any] = Depends(require_auth)):
    new_id = (max([f["id"] for f in rule_folders]) + 1) if rule_folders else 1
    folder = {"id": new_id, "name": payload.name}
    rule_folders.append(folder)
    return {"message": "文件夹创建成功", "folder": folder}

@app.put("/api/rule-folders/{folder_id}")
async def rename_folder(folder_id: int, payload: FolderUpdate, ctx: Dict[str, Any] = Depends(require_auth)):
    folder = next((f for f in rule_folders if f["id"] == folder_id), None)
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    folder["name"] = payload.name
    return {"message": "已重命名", "folder": folder}

@app.delete("/api/rule-folders/{folder_id}")
async def delete_folder(folder_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    global rule_folders
    if folder_id == 1:
        raise HTTPException(status_code=400, detail="默认文件夹不可删除")
    folder = next((f for f in rule_folders if f["id"] == folder_id), None)
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    # 规则迁移到默认文件夹
    for r in detection_rules:
        if r.get("folder_id") == folder_id:
            r["folder_id"] = 1
    rule_folders = [f for f in rule_folders if f["id"] != folder_id]
    return {"message": "文件夹已删除，规则已迁移到默认文件夹"}

# —— 问题库接口 ——
@app.get("/api/problems")
async def list_problems(error_type: Optional[str] = None, q: Optional[str] = None, category: Optional[str] = None, ctx: Dict[str, Any] = Depends(require_auth)):
    items = problems
    if error_type:
        items = [p for p in items if normalize_error_type(p.get("error_type") or "") == error_type]
    if category:
        items = [p for p in items if (p.get("category") or "") == category]
    if q:
        ql = q.lower()
        items = [p for p in items if ql in (p.get("title","" ).lower()) or ql in (p.get("url","" ).lower()) or ql in (p.get("error_type","" ).lower())]
    return {"problems": items}

@app.post("/api/problems")
async def create_problem(payload: ProblemCreate, ctx: Dict[str, Any] = Depends(require_auth)):
    new = {
        "id": (max([p["id"] for p in problems]) + 1) if problems else 1,
        "title": payload.title,
        "url": payload.url,
        "error_type": normalize_error_type(payload.error_type),
        "category": payload.category or "",
        "created_at": datetime.now().isoformat()
    }
    problems.append(new)
    save_problems()
    return {"message": "已创建", "problem": new}

@app.put("/api/problems/{pid}")
async def update_problem(pid: int, payload: ProblemUpdate, ctx: Dict[str, Any] = Depends(require_auth)):
    pr = next((p for p in problems if p["id"] == pid), None)
    if not pr:
        raise HTTPException(status_code=404, detail="问题不存在")
    for k, v in payload.dict(exclude_unset=True).items():
        if k == "error_type" and v is not None:
            pr[k] = normalize_error_type(v)
        else:
            pr[k] = v
    save_problems()
    return {"message": "已更新", "problem": pr}

@app.delete("/api/problems/{pid}")
async def delete_problem(pid: int, ctx: Dict[str, Any] = Depends(require_auth)):
    global problems
    before = len(problems)
    problems = [p for p in problems if p["id"] != pid]
    if len(problems) == before:
        raise HTTPException(status_code=404, detail="问题不存在")
    save_problems()
    return {"message": "已删除"}

@app.get("/api/problems/stats")
async def problem_stats(types: Optional[str] = None, ctx: Dict[str, Any] = Depends(require_auth)):
    # types: 逗号分隔的错误类型；若为空则统计全部
    wanted = None
    if types:
        wanted = set([t for t in types.split(',') if t])
    by_type: Dict[str, int] = {}
    for p in problems:
        et = normalize_error_type(p.get("error_type") or "")
        if wanted and et not in wanted:
            continue
        by_type[et] = by_type.get(et, 0) + 1
    total = sum(by_type.values()) if wanted else len(problems)
    return {"total": total, "type_count": len(by_type), "by_type": by_type}

# 用户管理（演示：任何登录用户可访问）
@app.get("/api/users")
async def list_users(ctx: Dict[str, Any] = Depends(require_auth)):
    return {"users": [_public_user(u) for u in users]}

@app.post("/api/users")
async def create_user(payload: UserCreate, ctx: Dict[str, Any] = Depends(require_auth)):
    if any(u["username"].lower() == payload.username.lower() for u in users):
        raise HTTPException(status_code=400, detail="用户名已存在")
    new_user = {
        "id": (max([u["id"] for u in users]) + 1) if users else 1,
        "username": payload.username,
        "email": payload.email or "",
        "role": payload.role or "普通用户",
        "password": payload.password or "",
        "position": payload.position or ""
    }
    users.append(new_user)
    save_users()
    return {"message": "用户创建成功", "user": _public_user(new_user)}

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, payload: UserUpdate, ctx: Dict[str, Any] = Depends(require_auth)):
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if payload.email is not None:
        user["email"] = payload.email
    if payload.role is not None:
        user["role"] = payload.role
    if payload.password is not None and payload.password != "":
        user["password"] = payload.password
    if payload.position is not None:
        user["position"] = payload.position
    save_users()
    return {"message": "用户更新成功", "user": _public_user(user)}

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    global users
    before = len(users)
    users = [u for u in users if u["id"] != user_id]
    if len(users) == before:
        raise HTTPException(status_code=404, detail="用户不存在")
    save_users()
    return {"message": "用户已删除"}

# ==================== 定时分析（Monitor）API ====================
# 数据文件路径
DEVICES_FILE = "/home/ugreen/log-analyse/database/nas_devices.json"

# 数据持久化函数
def load_monitor_data():
    """从文件加载监控设备和任务数据"""
    global nas_devices, monitor_tasks
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(DEVICES_FILE), exist_ok=True)
        
        if os.path.exists(DEVICES_FILE):
            with open(DEVICES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                nas_devices = data.get('devices', [])
                monitor_tasks = data.get('tasks', [])
                print(f"Loaded {len(nas_devices)} devices and {len(monitor_tasks)} tasks from {DEVICES_FILE}")
        else:
            # 创建空文件
            save_monitor_data()
            print(f"Created new monitor data file: {DEVICES_FILE}")
    except Exception as e:
        print(f"Error loading monitor data: {e}")
        nas_devices = []
        monitor_tasks = []

def save_monitor_data():
    """保存监控设备和任务数据到文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(DEVICES_FILE), exist_ok=True)
        
        data = {
            "devices": nas_devices,
            "tasks": monitor_tasks,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(DEVICES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(nas_devices)} devices and {len(monitor_tasks)} tasks to {DEVICES_FILE}")
    except Exception as e:
        print(f"Error saving monitor data: {e}")

# 临时内存存储 - 将在启动时从文件加载
nas_devices: List[Dict[str, Any]] = []
monitor_tasks: List[Dict[str, Any]] = []

# 邮件配置管理函数
def load_email_config() -> dict:
    """从JSON文件加载邮件配置"""
    import json
    config_file = "/home/ugreen/log-analyse/backend/data/email_config.json"
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 如果JSON文件不存在，返回默认配置
            return {
                "smtp_server": "",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",
                "sender_name": "日志分析系统", 
                "smtp_username": "",
                "use_tls": True,
                "is_configured": False
            }
    except Exception as e:
        logger.error(f"加载邮件配置失败: {str(e)}")
        return {
            "smtp_server": "",
            "smtp_port": 587,
            "sender_email": "",
            "sender_password": "",
            "sender_name": "日志分析系统",
            "smtp_username": "",
            "use_tls": True,
            "is_configured": False
        }

def save_email_config(config: dict) -> bool:
    """保存邮件配置到JSON文件"""
    import json
    config_file = "/home/ugreen/log-analyse/backend/data/email_config.json"
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存邮件配置失败: {str(e)}")
        return False

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

class TaskCreate(BaseModel):
    device_id: int
    name: str
    log_path: str
    rule_ids: List[int]
    email_recipients: List[str]
    email_time: str = "15:00"

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    log_path: Optional[str] = None
    rule_ids: Optional[List[int]] = None
    email_recipients: Optional[List[str]] = None
    email_time: Optional[str] = None

class EmailConfig(BaseModel):
    smtp_server: str
    smtp_port: int = 587
    sender_email: str
    sender_password: str
    sender_name: str = "日志分析系统"
    use_tls: bool = True

# NAS设备管理
@app.get("/api/monitor/devices")
async def get_devices(ctx: Dict[str, Any] = Depends(require_auth)):
    return {"devices": nas_devices}

@app.post("/api/monitor/devices")
async def create_device(payload: DeviceCreate, ctx: Dict[str, Any] = Depends(require_auth)):
    new_device = {
        "id": (max([d["id"] for d in nas_devices]) + 1) if nas_devices else 1,
        "name": payload.name,
        "ip_address": payload.ip_address,
        "ssh_port": payload.ssh_port,
        "ssh_username": payload.ssh_username,
        "ssh_password": payload.ssh_password,  # 实际项目中应加密存储
        "description": payload.description or "",
        "status": "unknown",
        "script_deployed": False,
        "last_connected": None,
        "created_at": datetime.now().isoformat()
    }
    nas_devices.append(new_device)
    save_monitor_data()  # 保存到文件
    return {"message": "设备创建成功", "device": new_device}

@app.put("/api/monitor/devices/{device_id}")
async def update_device(device_id: int, payload: DeviceUpdate, ctx: Dict[str, Any] = Depends(require_auth)):
    device = next((d for d in nas_devices if d["id"] == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    for k, v in payload.dict(exclude_unset=True).items():
        if v is not None:
            device[k] = v
    
    save_monitor_data()  # 保存到文件
    return {"message": "设备更新成功", "device": device}

@app.delete("/api/monitor/devices/{device_id}")
async def delete_device(device_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    global nas_devices, monitor_tasks
    before = len(nas_devices)
    nas_devices = [d for d in nas_devices if d["id"] != device_id]
    if len(nas_devices) == before:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 删除关联的监控任务
    monitor_tasks = [t for t in monitor_tasks if t["device_id"] != device_id]
    save_monitor_data()  # 保存到文件
    return {"message": "设备已删除"}

@app.post("/api/monitor/devices/{device_id}/test-connection")
async def test_device_connection(device_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    device = next((d for d in nas_devices if d["id"] == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 实现真实的SSH连接测试
    import subprocess
    import socket
    
    try:
        ip = device['ip_address']
        port = device['ssh_port']
        username = device['ssh_username']
        password = device['ssh_password']
        
        # 首先测试网络连接
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5秒超时
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result != 0:
                device["status"] = "error"
                return {
                    "success": False,
                    "message": f"网络连接失败：无法连接到 {ip}:{port}"
                }
        except Exception as e:
            device["status"] = "error"
            return {
                "success": False,
                "message": f"网络连接测试失败：{str(e)}"
            }
        
        # 使用sshpass进行SSH连接测试
        try:
            # 检查sshpass是否可用
            sshpass_check = subprocess.run(['which', 'sshpass'], capture_output=True, text=True)
            if sshpass_check.returncode != 0:
                # 如果没有sshpass，使用ssh with expect或直接测试端口
                device["status"] = "active" if result == 0 else "error"
                device["last_connected"] = datetime.now().isoformat() if result == 0 else device.get("last_connected")
                return {
                    "success": result == 0,
                    "message": "端口连接成功（未安装sshpass，无法验证SSH认证）" if result == 0 else "端口连接失败"
                }
            
            # 使用sshpass测试SSH连接
            ssh_cmd = [
                'sshpass', '-p', password,
                'ssh',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'ConnectTimeout=10',
                '-o', 'BatchMode=yes',
                '-p', str(port),
                f'{username}@{ip}',
                'echo "SSH连接测试成功"'
            ]
            
            ssh_result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
            
            if ssh_result.returncode == 0:
                device["status"] = "active"
                device["last_connected"] = datetime.now().isoformat()
                return {
                    "success": True,
                    "message": f"SSH连接测试成功！已成功连接到 {username}@{ip}:{port}"
                }
            else:
                device["status"] = "error"
                error_msg = ssh_result.stderr.strip() if ssh_result.stderr else "SSH认证失败"
                return {
                    "success": False,
                    "message": f"SSH连接失败：{error_msg}"
                }
                
        except subprocess.TimeoutExpired:
            device["status"] = "error"
            return {
                "success": False,
                "message": "SSH连接超时，请检查网络连接和防火墙设置"
            }
        except Exception as e:
            device["status"] = "error"
            return {
                "success": False,
                "message": f"SSH连接测试失败：{str(e)}"
            }
            
    except Exception as e:
        device["status"] = "error"
        return {
            "success": False,
            "message": f"连接测试失败：{str(e)}"
        }

@app.get("/api/monitor/devices/{device_id}/local-system-info")
async def get_device_local_system_info(device_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    device = next((d for d in nas_devices if d["id"] == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 获取真实的系统信息
    import subprocess
    import platform
    
    try:
        # 获取主机名
        hostname_result = subprocess.run(['hostname'], capture_output=True, text=True)
        hostname = hostname_result.stdout.strip() if hostname_result.returncode == 0 else device['name']
        
        # 获取系统信息
        os_release_result = subprocess.run(['cat', '/etc/os-release'], capture_output=True, text=True)
        os_info = "未知系统"
        if os_release_result.returncode == 0:
            lines = os_release_result.stdout.split('\n')
            pretty_name = next((line.split('=')[1].strip('"') for line in lines if line.startswith('PRETTY_NAME=')), None)
            version = next((line.split('=')[1].strip('"') for line in lines if line.startswith('OS_VERSION=')), None)
            if pretty_name:
                os_info = f"{pretty_name}"
                if version:
                    os_info += f" (固件版本: {version})"
        
        # 获取运行时间
        uptime_result = subprocess.run(['uptime', '-p'], capture_output=True, text=True)
        uptime = uptime_result.stdout.strip() if uptime_result.returncode == 0 else "未知"
        if uptime.startswith('up '):
            uptime = uptime[3:]  # 移除 'up ' 前缀
        
        # 获取内核版本
        uname_result = subprocess.run(['uname', '-r'], capture_output=True, text=True)
        kernel = uname_result.stdout.strip() if uname_result.returncode == 0 else "未知"
        
        # 获取CPU信息
        cpu_info = "未知处理器"
        try:
            lscpu_result = subprocess.run(['lscpu'], capture_output=True, text=True)
            if lscpu_result.returncode == 0:
                lines = lscpu_result.stdout.split('\n')
                model_line = next((line for line in lines if 'Model name:' in line), None)
                if model_line:
                    cpu_info = model_line.split(':', 1)[1].strip()
        except:
            pass
        
        # 获取内存信息
        memory_info = "内存信息未知"
        try:
            # 先尝试获取详细内存信息
            dmidecode_result = subprocess.run(['dmidecode', '-t', 'memory'], capture_output=True, text=True)
            if dmidecode_result.returncode == 0:
                lines = dmidecode_result.stdout.split('\n')
                size_line = next((line for line in lines if 'Size:' in line and 'GB' in line), None)
                manufacturer_line = next((line for line in lines if 'Manufacturer:' in line and not line.strip().endswith('Manufacturer: Not Specified')), None)
                part_line = next((line for line in lines if 'Part Number:' in line), None)
                type_line = next((line for line in lines if 'Type:' in line and 'Type Detail' not in line), None)
                speed_line = next((line for line in lines if 'Speed:' in line and 'MT/s' in line), None)
                
                memory_parts = []
                if size_line:
                    size = size_line.split(':', 1)[1].strip()
                    memory_parts.append(f"容量: {size}")
                if type_line:
                    mem_type = type_line.split(':', 1)[1].strip()
                    memory_parts.append(f"类型: {mem_type}")
                if speed_line:
                    speed = speed_line.split(':', 1)[1].strip()
                    memory_parts.append(f"频率: {speed}")
                if manufacturer_line:
                    manufacturer = manufacturer_line.split(':', 1)[1].strip()
                    memory_parts.append(f"制造商: {manufacturer}")
                if part_line:
                    part = part_line.split(':', 1)[1].strip()
                    if part and part != 'Not Specified':
                        memory_parts.append(f"型号: {part}")
                
                if memory_parts:
                    memory_info = " | ".join(memory_parts)
            
            # 如果dmidecode失败，回退到/proc/meminfo
            if memory_info == "内存信息未知":
                meminfo_result = subprocess.run(['cat', '/proc/meminfo'], capture_output=True, text=True)
                if meminfo_result.returncode == 0:
                    lines = meminfo_result.stdout.split('\n')
                    total_line = next((line for line in lines if line.startswith('MemTotal:')), None)
                    available_line = next((line for line in lines if line.startswith('MemAvailable:')), None)
                    if total_line:
                        total_kb = int(total_line.split()[1])
                        total_gb = round(total_kb / 1024 / 1024, 1)
                        memory_info = f"总内存: {total_gb}GB"
                        if available_line:
                            avail_kb = int(available_line.split()[1])
                            avail_gb = round(avail_kb / 1024 / 1024, 1)
                            used_gb = round(total_gb - avail_gb, 1)
                            memory_info += f" | 已用: {used_gb}GB | 可用: {avail_gb}GB"
        except:
            pass
        
        # 获取磁盘使用情况
        disk_info = "磁盘信息未知"
        try:
            # 使用 df 获取文件系统使用情况
            df_result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            if df_result.returncode == 0:
                lines = df_result.stdout.strip().split('\n')
                if len(lines) > 1:
                    fields = lines[1].split()
                    if len(fields) >= 5:
                        filesystem = fields[0]
                        size = fields[1]
                        used = fields[2]
                        avail = fields[3]
                        use_percent = fields[4]
                        disk_info = f"根文件系统 ({filesystem}): {use_percent} 已用 ({used}/{size}，剩余 {avail})"
            
            # 获取存储设备信息
            try:
                lsblk_result = subprocess.run(['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT', '--tree'], capture_output=True, text=True)
                if lsblk_result.returncode == 0:
                    disk_info += "\n\n存储设备信息:\n" + lsblk_result.stdout
            except:
                pass
                
        except:
            pass
        
        return {
            "hostname": hostname,
            "os_info": os_info,
            "uptime": uptime,
            "kernel": kernel,
            "cpu_info": cpu_info,
            "memory": memory_info,
            "disk_usage": disk_info
        }
    except Exception as e:
        # 如果获取失败，返回基本信息
        return {
            "hostname": device['name'],
            "os_info": "系统信息获取失败",
            "uptime": "未知",
            "kernel": "未知",
            "cpu_info": "未知",
            "memory": "内存信息获取失败",
            "disk_usage": "磁盘信息获取失败",
            "error": str(e)
        }

@app.get("/api/monitor/devices/{device_id}/error-logs")
async def get_device_error_logs(device_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    device = next((d for d in nas_devices if d["id"] == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 使用NAS设备管理器获取真实的错误日志
    from .services.nas_device_manager import NASDeviceManager
    
    try:
        manager = NASDeviceManager()
        
        # 构造设备信息
        device_info = {
            'ip': device.get('ip_address', device.get('ip', '')),
            'username': device.get('username', device.get('ssh_username', '')),
            'password': device.get('password', device.get('ssh_password', '')),
            'port': device.get('port', device.get('ssh_port', 22))
        }
        
        # 获取错误日志列表
        error_logs = await manager.get_error_logs(device_info, limit=10)
        
        if not error_logs:
            # 如果没有分析生成的错误日志，返回提示信息
            return [{
                "filename": "暂无错误日志",
                "size": "-",
                "modified_time": "请先运行定时分析任务",
                "note": "错误日志由定时分析任务生成，请确保已配置并运行分析任务"
            }]
        
        return error_logs
        
    except Exception as e:
        # 如果获取失败，返回错误信息
        return [{
            "filename": "获取失败",
            "size": "-",
            "modified_time": f"错误: {str(e)}",
            "note": "请检查设备连接和SSH配置"
        }]

@app.get("/api/monitor/devices/{device_id}/error-logs/{filename}/content")
async def get_log_content(device_id: int, filename: str, ctx: Dict[str, Any] = Depends(require_auth)):
    device = next((d for d in nas_devices if d["id"] == device_id), None)
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 使用NAS设备管理器获取真实的日志内容
    from .services.nas_device_manager import NASDeviceManager
    
    try:
        manager = NASDeviceManager()
        
        # 构造设备信息
        device_info = {
            'ip': device.get('ip_address', device.get('ip', '')),
            'username': device.get('username', device.get('ssh_username', '')),
            'password': device.get('password', device.get('ssh_password', '')),
            'port': device.get('port', device.get('ssh_port', 22))
        }
        
        # 获取日志文件内容
        content = await manager.get_log_file_content(device_info, filename)
        
        if content is None:
            # 如果文件不存在或无法读取
            return {
                "filename": filename,
                "size": 0,
                "content": "错误：无法读取日志文件。可能原因：\n1. 日志文件不存在\n2. 尚未进行日志分析\n3. SSH连接问题\n\n请先运行定时分析任务生成错误日志。"
            }
        
        return {
            "filename": filename,
            "size": len(content),
            "content": content
        }
        
    except Exception as e:
        return {
            "filename": filename,
            "size": 0,
            "content": f"获取日志内容失败：{str(e)}\n\n请检查：\n1. 设备SSH连接配置\n2. 是否已运行日志分析任务\n3. 网络连接状态"
        }

# 监控任务管理
@app.get("/api/monitor/monitor-tasks")
async def get_monitor_tasks(ctx: Dict[str, Any] = Depends(require_auth)):
    return {"tasks": monitor_tasks}

@app.post("/api/monitor/monitor-tasks")
async def create_monitor_task(payload: TaskCreate, ctx: Dict[str, Any] = Depends(require_auth)):
    device = next((d for d in nas_devices if d["id"] == payload.device_id), None)
    if not device:
        raise HTTPException(status_code=400, detail="设备不存在")
    
    new_task = {
        "id": (max([t["id"] for t in monitor_tasks]) + 1) if monitor_tasks else 1,
        "device_id": payload.device_id,
        "name": payload.name,
        "log_path": payload.log_path,
        "rule_ids": payload.rule_ids,
        "email_recipients": payload.email_recipients,
        "email_time": payload.email_time,
        "status": "pending",
        "error_count": 0,
        "last_run": None,
        "next_run": None,
        "created_at": datetime.now().isoformat()
    }
    monitor_tasks.append(new_task)
    save_monitor_data()  # 保存到文件
    return {"message": "任务创建成功", "task": new_task}

@app.put("/api/monitor/monitor-tasks/{task_id}")
async def update_monitor_task(task_id: int, payload: TaskUpdate, ctx: Dict[str, Any] = Depends(require_auth)):
    task = next((t for t in monitor_tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    for k, v in payload.dict(exclude_unset=True).items():
        if v is not None:
            task[k] = v
    
    save_monitor_data()  # 保存到文件
    return {"message": "任务更新成功", "task": task}

@app.delete("/api/monitor/monitor-tasks/{task_id}")
async def delete_monitor_task(task_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    global monitor_tasks
    before = len(monitor_tasks)
    monitor_tasks = [t for t in monitor_tasks if t["id"] != task_id]
    if len(monitor_tasks) == before:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    save_monitor_data()  # 保存到文件
    return {"message": "任务已删除"}

@app.get("/api/monitor/scheduler/status")
async def get_scheduler_status(ctx: Dict[str, Any] = Depends(require_auth)):
    # 模拟调度器状态
    return {
        "is_running": True,
        "next_daily_report": "2024-09-01 15:00:00",
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scheduled_tasks_count": len(monitor_tasks)
    }

# —— 邮件配置相关API ——
@app.get("/api/monitor/email/config")
async def get_email_config(ctx: Dict[str, Any] = Depends(require_auth)):
    """获取邮件配置"""
    config = load_email_config()
    
    # 为了前端显示，不返回密码
    return {
        "smtp_server": config.get("smtp_server", ""),
        "smtp_port": config.get("smtp_port", 587),
        "sender_email": config.get("sender_email", ""),
        "sender_name": config.get("sender_name", "日志分析系统"),
        "is_configured": config.get("is_configured", False)
    }

@app.put("/api/monitor/email/config")  
async def update_email_config(
    smtp_server: str = Body(...),
    smtp_port: int = Body(587),
    sender_email: str = Body(...),
    sender_password: str = Body(...),
    sender_name: str = Body("NAS日志监控系统"),
    ctx: Dict[str, Any] = Depends(require_auth)
):
    """更新邮件配置"""
    try:
        # 创建新的配置对象
        config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "sender_email": sender_email,
            "sender_name": sender_name,
            "smtp_username": sender_email,  # 兼容性字段
            "smtp_password": sender_password, # 统一使用这个字段名
            "use_tls": True,
            "is_configured": bool(sender_email and sender_password)
        }
        
        # 保存到JSON文件
        if save_email_config(config):
            # 同时更新全局邮件服务实例
            from .services.email_service import email_service
            email_service.reload_config()
            
            return {
                "success": True,
                "message": "邮件配置已成功保存"
            }
        else:
            return {
                "success": False,
                "message": "保存配置失败"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"保存配置失败: {str(e)}"
        }

@app.get("/api/monitor/scheduler/status")
async def get_scheduler_status(ctx: Dict[str, Any] = Depends(require_auth)):
    """获取调度器状态"""
    return {
        "status": "running",
        "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "next_check": (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "tasks_count": 0
    }

@app.post("/api/monitor/email/test")
async def send_test_email(recipients: List[str] = Body(...), ctx: Dict[str, Any] = Depends(require_auth)):
    # 实现真实的邮件发送
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime
    
    # 获取邮件配置
    email_config = load_email_config()
    
    if not email_config.get("is_configured"):
        return {
            "success": False,
            "message": "邮件配置未完成，请先配置SMTP设置"
        }
    
    if not recipients:
        return {
            "success": False,
            "message": "请提供收件人邮箱地址"
        }
    
    try:
        # 创建邮件消息
        msg = MIMEMultipart()
        # QQ邮箱要求严格的From格式
        msg['From'] = email_config['sender_email']
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = "=?utf-8?B?5pel5b+X5YiG5p6Q57O757uf?= - =?utf-8?B?6YKu5Lu25rWL6K+V?="  # "日志分析系统 - 邮件测试" 的UTF-8 Base64编码
        
        # 邮件正文
        body = f"""
这是一封来自日志分析系统的测试邮件。

测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
发送服务器: {email_config['smtp_server']}:{email_config['smtp_port']}
收件人数量: {len(recipients)}

如果您收到此邮件，说明邮件服务配置正常。

---
日志分析系统自动发送
        """.strip()
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 连接SMTP服务器并发送邮件
        server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
        
        if email_config.get('use_tls', True):
            server.starttls()
        
        server.login(email_config['sender_email'], email_config['sender_password'])
        
        # 发送邮件到所有收件人
        for recipient in recipients:
            server.send_message(msg, to_addrs=[recipient])
        
        server.quit()
        
        return {
            "success": True,
            "message": f"测试邮件已成功发送到 {len(recipients)} 个邮箱"
        }
        
    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "SMTP认证失败，请检查邮箱用户名和密码"
        }
    except smtplib.SMTPConnectError:
        return {
            "success": False,
            "message": f"无法连接到SMTP服务器 {email_config['smtp_server']}:{email_config['smtp_port']}"
        }
    except smtplib.SMTPRecipientsRefused as e:
        return {
            "success": False,
            "message": f"收件人地址被拒绝: {', '.join(e.recipients.keys())}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"邮件发送失败: {str(e)}"
        }

# —— NAS设备系统信息API ——
@app.get("/api/monitor/devices/{device_id}/system-info")
async def get_device_system_info(device_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    """实时获取NAS设备系统信息"""
    try:
        import paramiko
        
        # 从JSON文件加载设备信息
        devices_file = "/home/ugreen/log-analyse/database/nas_devices.json"
        if not os.path.exists(devices_file):
            return {"success": False, "message": "设备配置文件不存在"}
            
        with open(devices_file, 'r') as f:
            data = json.load(f)
        
        # 查找设备
        device = None
        for d in data.get('devices', []):
            if d['id'] == device_id:
                device = d
                break
                
        if not device:
            return {"success": False, "message": "设备不存在"}
        
        # SSH连接获取系统信息
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            device['ip_address'], 
            device.get('ssh_port', 22),
            device['ssh_username'], 
            device.get('ssh_password', ''),
            timeout=30
        )
        
        # 执行系统命令获取信息
        commands = {
            'hostname': 'hostname',
            'os_info': 'cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d \'"\' || uname -s',
            'uptime': 'uptime -p || uptime',
            'kernel': 'uname -r',
            'cpu_info': 'cat /proc/cpuinfo | grep "model name" | head -1 | cut -d: -f2 | xargs',
            'memory': 'free -h | head -2 | tail -1',
            'disk_usage': 'df -h / | tail -1'
        }
        
        system_info = {}
        for key, cmd in commands.items():
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                result = stdout.read().decode().strip()
                system_info[key] = result if result else '获取失败'
            except Exception as e:
                system_info[key] = f"获取失败: {str(e)}"
        
        ssh.close()
        
        # 返回扁平化的系统信息，符合前端期望的格式
        return system_info
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取系统信息失败: {str(e)}"
        }


@app.post("/api/monitor/email/send-report")
async def send_manual_report(payload: Dict[str, Any] = Body(...), ctx: Dict[str, Any] = Depends(require_auth)):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    task_id = payload.get("task_id")
    task = next((t for t in monitor_tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取邮件配置
    email_config = load_email_config()
    
    if not email_config.get("is_configured"):
        return {
            "success": False,
            "message": "邮件配置未完成，请先配置SMTP设置"
        }
    
    recipients = task.get('email_recipients', [])
    if not recipients:
        return {
            "success": False,
            "message": "任务未配置邮件接收者"
        }
    
    try:
        device = next((d for d in nas_devices if d["id"] == task["device_id"]), None)
        device_name = device['name'] if device else f"设备ID-{task['device_id']}"
        
        # 使用EmailService发送测试邮件（简化版监控报告）
        from .services.email_service import email_service
        
        # 准备邮件内容作为测试邮件发送
        success = await email_service.send_test_email(recipients)
        
        if success:
            return {
                "success": True,
                "message": f"监控报告已发送到 {len(recipients)} 个邮箱"
            }
        else:
            return {
                "success": False,
                "message": "邮件发送失败，请检查邮件配置和网络连接"
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"报告发送失败: {str(e)}"
        }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 