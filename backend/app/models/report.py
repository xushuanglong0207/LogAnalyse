from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from ..database import Base


class ReportType(PyEnum):
    SUMMARY = "summary"
    DETAILED = "detailed"
    PROBLEM_ANALYSIS = "problem_analysis"
    TREND_ANALYSIS = "trend_analysis"


class ReportStatus(PyEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    report_type = Column(Enum(ReportType), nullable=False)
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING)
    
    # 报表配置
    log_file_ids = Column(JSON)  # 关联的日志文件ID列表
    date_range_start = Column(DateTime(timezone=True))
    date_range_end = Column(DateTime(timezone=True))
    filters = Column(JSON)  # 过滤条件
    
    # 报表内容
    content = Column(JSON)  # 报表数据内容
    summary = Column(Text)  # 报表摘要
    charts_data = Column(JSON)  # 图表数据
    
    # 分享设置
    is_public = Column(Boolean, default=False)
    share_token = Column(String(100), unique=True)
    share_expires_at = Column(DateTime(timezone=True))
    
    # 文件导出
    export_formats = Column(JSON)  # 支持的导出格式
    file_paths = Column(JSON)  # 已导出文件路径
    
    # 元数据
    generated_by = Column(Integer, ForeignKey("users.id"))
    generated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    creator = relationship("User", backref="created_reports")

    def __repr__(self):
        return f"<Report(id={self.id}, title='{self.title}', type='{self.report_type.value}')>" 