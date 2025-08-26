from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime
from ..models.log import LogType, LogLevel, ParseRuleType


class LogFileResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: Optional[int]
    file_type: Optional[str]
    log_type: LogType
    total_lines: int
    processed_lines: int
    error_lines: int
    is_processed: bool
    upload_user_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class LogEntryResponse(BaseModel):
    id: int
    log_file_id: int
    line_number: int
    raw_content: str
    parsed_content: Optional[Any]
    timestamp: Optional[datetime]
    log_level: Optional[LogLevel]
    source: Optional[str]
    message: Optional[str]
    problem_detected: bool
    problem_type: Optional[str]
    problem_description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ParseRuleCreate(BaseModel):
    name: str = Field(..., max_length=100, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    rule_type: ParseRuleType = Field(..., description="规则类型")
    pattern: str = Field(..., description="匹配模式")
    problem_type: Optional[str] = Field(None, max_length=100, description="问题类型")
    problem_description: Optional[str] = Field(None, description="问题描述")
    is_active: bool = Field(True, description="是否启用")
    priority: int = Field(0, description="优先级")


class ParseRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pattern: Optional[str] = None
    problem_type: Optional[str] = None
    problem_description: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class ParseRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    rule_type: ParseRuleType
    pattern: str
    problem_type: Optional[str]
    problem_description: Optional[str]
    is_active: bool
    priority: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class LogAnalysisResult(BaseModel):
    total_lines: int
    processed_lines: int
    error_lines: int
    problems_found: int
    problem_summary: List[dict]
    processing_time: float 