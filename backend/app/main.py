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

# 可存储内容的最大字节数（5MB）
MAX_CONTENT_BYTES = 5 * 1024 * 1024

# 会话有效期
DEFAULT_TTL_HOURS = 24
REMEMBER_TTL_DAYS = 30

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

# 内存存储（临时）
uploaded_files: List[Dict[str, Any]] = []
analysis_results: List[Dict[str, Any]] = []
problems: List[Dict[str, Any]] = []  # 问题库：{id, title, url, error_type, created_at}

# 简易用户模型与内存用户表
class UserCreate(BaseModel):
    username: str
    email: Optional[str] = ""
    password: Optional[str] = ""  # 演示用，未加密
    role: Optional[str] = "普通用户"

class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None

class LoginPayload(BaseModel):
    username: str
    password: str
    remember: bool = False

class ChangePasswordPayload(BaseModel):
    old_password: str
    new_password: str

users: List[Dict[str, Any]] = [
    {"id": 1, "username": "admin", "email": "", "role": "管理员", "password": "admin123"}
]

# 规则与文件夹模型
class RuleCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    enabled: bool = True
    patterns: List[str] = []  # 正则或关键字列表
    operator: str = "OR"      # AND / OR / NOT
    is_regex: bool = True
    folder_id: Optional[int] = 1

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    patterns: Optional[List[str]] = None
    operator: Optional[str] = None
    is_regex: Optional[bool] = None
    folder_id: Optional[int] = None

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

# —— 问题库模型 ——
class ProblemCreate(BaseModel):
    title: str
    url: str
    error_type: str  # 关联的错误类型（如 I/O error、OOM Killer 等）

class ProblemUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    error_type: Optional[str] = None

# 简易令牌会话存储：token -> {user_id, expiry}
sessions: Dict[str, Dict[str, Any]] = {}

def _public_user(u: Dict[str, Any]) -> Dict[str, Any]:
    return {k: u[k] for k in ["id", "username", "email", "role"]}

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
    return {
        "uploaded_files": len(uploaded_files),
        "detected_issues": sum(len(result.get("issues", [])) for result in analysis_results),
        "detection_rules": len([rule for rule in detection_rules if rule["enabled"]]),
        "recent_activity": []
    }

# 日志管理
@app.post("/api/logs/upload")
async def upload_log_file(file: UploadFile = File(...), ctx: Dict[str, Any] = Depends(require_auth)):
    try:
        # 放宽文件类型限制：接受所有类型，尽力按utf-8解析
        content = await file.read()
        content_str = content.decode('utf-8', errors='ignore')
        file_info = {
            "id": len(uploaded_files) + 1,
            "filename": file.filename,
            "size": len(content),
            "upload_time": datetime.now().isoformat(),
            "content": content_str[:MAX_CONTENT_BYTES],
            "status": "uploaded"
        }
        uploaded_files.append(file_info)
        return {"message": "文件上传成功", "file_id": file_info["id"], "filename": file.filename, "size": len(content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@app.get("/api/logs")
async def get_uploaded_files(ctx: Dict[str, Any] = Depends(require_auth)):
    return {
        "files": [
            {"id": f["id"], "filename": f["filename"], "size": f["size"], "upload_time": f["upload_time"], "status": f["status"]}
            for f in uploaded_files
        ]
    }

@app.get("/api/logs/{file_id}")
async def get_log_file(file_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    f = next((x for x in uploaded_files if x["id"] == file_id), None)
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {
        "id": f["id"],
        "filename": f["filename"],
        "size": f["size"],
        "upload_time": f["upload_time"],
        "content": f.get("content", "")
    }

@app.delete("/api/logs/{file_id}")
async def delete_log_file(file_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    global uploaded_files, analysis_results
    before = len(uploaded_files)
    uploaded_files = [f for f in uploaded_files if f["id"] != file_id]
    analysis_results = [r for r in analysis_results if r.get("file_id") != file_id]
    if len(uploaded_files) == before:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"message": "文件已删除"}

class AnalyzeTextPayload(BaseModel):
    text: str
    filename: Optional[str] = "pasted.log"

@app.post("/api/logs/analyze_text")
async def analyze_text(payload: AnalyzeTextPayload, ctx: Dict[str, Any] = Depends(require_auth)):
    text_bytes = len(payload.text.encode("utf-8"))
    if text_bytes > MAX_CONTENT_BYTES:
        raise HTTPException(status_code=400, detail="文本内容超过5MB限制")
    # 临时存储为一条文件记录（不写入磁盘）
    file_info = {
        "id": len(uploaded_files) + 1,
        "filename": payload.filename,
        "size": text_bytes,
        "upload_time": datetime.now().isoformat(),
        "content": payload.text,
        "status": "uploaded"
    }
    uploaded_files.append(file_info)
    return await analyze_log_file(file_info["id"])  # 直接复用分析流程

# 规则匹配逻辑

def evaluate_rule_matches(content: str, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not rule.get("enabled", True):
        return []
    patterns = rule.get("patterns", []) or []
    operator = (rule.get("operator") or "OR").upper()
    is_regex = bool(rule.get("is_regex", True))

    def find_matches(pat: str):
        if is_regex:
            return list(re.finditer(pat, content, re.IGNORECASE))
        else:
            matches = []
            start = 0
            pat_l = pat.lower()
            cont_l = content.lower()
            while True:
                idx = cont_l.find(pat_l, start)
                if idx == -1:
                    break
                class M:
                    def __init__(self, s, e):
                        self._s = s; self._e = e
                    def start(self): return self._s
                    def end(self): return self._e
                    def group(self): return content[self._s:self._e]
                matches.append(M(idx, idx + len(pat)))
                start = idx + len(pat)
            return matches

    all_lists = [find_matches(p) for p in patterns]

    if operator == "AND":
        # 所有模式至少出现一次才算匹配，返回每个模式的首个匹配
        if all(len(lst) > 0 for lst in all_lists):
            firsts = [lst[0] for lst in all_lists]
            return firsts
        return []
    elif operator == "NOT":
        # 所有模式都不出现才算命中（返回空匹配以指示命中）
        if all(len(lst) == 0 for lst in all_lists):
            return [None]  # 用None占位表示命中但无具体片段
        return []
    else:  # OR
        flat = [m for lst in all_lists for m in lst]
        return flat

@app.post("/api/logs/{file_id}/analyze")
async def analyze_log_file(file_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    try:
        file_info = next((f for f in uploaded_files if f["id"] == file_id), None)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        content = file_info.get("content", "")
        issues = []
        lines = content.split('\n')
        for rule in detection_rules:
            matches = evaluate_rule_matches(content, rule)
            if not matches:
                continue
            for m in matches:
                if m is None:
                    line_number = 1
                    context = '\n'.join(lines[:5])
                    matched_text = ""
                else:
                    line_number = content[:m.start()].count('\n') + 1
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
        result = {
            "file_id": file_id,
            "filename": file_info["filename"],
            "analysis_time": datetime.now().isoformat(),
            "issues": issues,
            "summary": {
                "total_issues": len(issues),
                "high_severity": len([i for i in issues if i["severity"] == "high"]),
                "medium_severity": len([i for i in issues if i["severity"] == "medium"])
            }
        }
        # 如果已存在同file_id分析，替换
        global analysis_results
        analysis_results = [r for r in analysis_results if r.get("file_id") != file_id]
        analysis_results.append(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

# 分析结果查询
@app.get("/api/analysis/results")
async def get_analysis_results(ctx: Dict[str, Any] = Depends(require_auth)):
    return {"results": analysis_results}

@app.get("/api/analysis/{file_id}")
async def get_file_analysis_result(file_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
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
        "operator": (payload.operator or "OR").upper(),
        "is_regex": bool(payload.is_regex),
        "folder_id": payload.folder_id or 1,
    }
    detection_rules.append(rule)
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
    return {"message": "规则更新成功", "rule": rule}

@app.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    global detection_rules
    before = len(detection_rules)
    detection_rules = [r for r in detection_rules if r["id"] != rule_id]
    if len(detection_rules) == before:
        raise HTTPException(status_code=404, detail="规则不存在")
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
async def list_problems(error_type: Optional[str] = None, ctx: Dict[str, Any] = Depends(require_auth)):
    items = problems
    if error_type:
        items = [p for p in items if p.get("error_type") == error_type]
    return {"problems": items}

@app.post("/api/problems")
async def create_problem(payload: ProblemCreate, ctx: Dict[str, Any] = Depends(require_auth)):
    new = {
        "id": (max([p["id"] for p in problems]) + 1) if problems else 1,
        "title": payload.title,
        "url": payload.url,
        "error_type": payload.error_type,
        "created_at": datetime.now().isoformat()
    }
    problems.append(new)
    return {"message": "已创建", "problem": new}

@app.put("/api/problems/{pid}")
async def update_problem(pid: int, payload: ProblemUpdate, ctx: Dict[str, Any] = Depends(require_auth)):
    pr = next((p for p in problems if p["id"] == pid), None)
    if not pr:
        raise HTTPException(status_code=404, detail="问题不存在")
    for k, v in payload.dict(exclude_unset=True).items():
        pr[k] = v
    return {"message": "已更新", "problem": pr}

@app.delete("/api/problems/{pid}")
async def delete_problem(pid: int, ctx: Dict[str, Any] = Depends(require_auth)):
    global problems
    before = len(problems)
    problems = [p for p in problems if p["id"] != pid]
    if len(problems) == before:
        raise HTTPException(status_code=404, detail="问题不存在")
    return {"message": "已删除"}

@app.get("/api/problems/stats")
async def problem_stats(types: Optional[str] = None, ctx: Dict[str, Any] = Depends(require_auth)):
    # types: 逗号分隔的错误类型；若为空则统计全部
    wanted = None
    if types:
        wanted = set([t for t in types.split(',') if t])
    by_type: Dict[str, int] = {}
    for p in problems:
        et = p.get("error_type") or ""
        if wanted and et not in wanted:
            continue
        by_type[et] = by_type.get(et, 0) + 1
    return {"total": sum(by_type.values()) if wanted else len(problems), "by_type": by_type}

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
        "password": payload.password or ""
    }
    users.append(new_user)
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
    return {"message": "用户更新成功", "user": _public_user(user)}

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, ctx: Dict[str, Any] = Depends(require_auth)):
    global users
    before = len(users)
    users = [u for u in users if u["id"] != user_id]
    if len(users) == before:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"message": "用户已删除"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 