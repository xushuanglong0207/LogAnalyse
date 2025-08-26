from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime
from ..models.report import ReportType, ReportStatus


class ReportCreate(BaseModel):
    title: str = Field(..., max_length=200, description="报表标题")
    description: Optional[str] = Field(None, description="报表描述")
    report_type: ReportType = Field(..., description="报表类型")
    log_file_ids: List[int] = Field(..., description="关联的日志文件ID列表")
    date_range_start: Optional[datetime] = Field(None, description="开始时间")
    date_range_end: Optional[datetime] = Field(None, description="结束时间")
    filters: Optional[dict] = Field(None, description="过滤条件")


class ReportUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class ReportResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    report_type: ReportType
    status: ReportStatus
    log_file_ids: Optional[List[int]]
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
    filters: Optional[dict]
    content: Optional[dict]
    summary: Optional[str]
    charts_data: Optional[dict]
    is_public: bool
    share_token: Optional[str]
    share_expires_at: Optional[datetime]
    export_formats: Optional[List[str]]
    file_paths: Optional[dict]
    generated_by: Optional[int]
    generated_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReportShareRequest(BaseModel):
    is_public: bool = Field(..., description="是否公开分享")
    expires_hours: Optional[int] = Field(24, description="分享过期时间（小时）")


class ReportExportRequest(BaseModel):
    format: str = Field(..., description="导出格式: pdf, excel, csv")
    include_charts: bool = Field(True, description="是否包含图表") 