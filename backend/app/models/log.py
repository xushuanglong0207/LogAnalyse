from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from ..database import Base


class LogType(PyEnum):
    SYSLOG = "syslog"
    KERNLOG = "kernlog"
    CUSTOM = "custom"


class LogLevel(PyEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ParseRuleType(PyEnum):
    REGEX = "regex"
    KEYWORD = "keyword"
    JSON_PATH = "json_path"


class LogFile(Base):
    __tablename__ = "log_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(50))
    log_type = Column(Enum(LogType), default=LogType.CUSTOM)
    total_lines = Column(Integer, default=0)
    processed_lines = Column(Integer, default=0)
    error_lines = Column(Integer, default=0)
    is_processed = Column(Boolean, default=False)
    upload_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    upload_user = relationship("User", backref="uploaded_files")
    log_entries = relationship("LogEntry", back_populates="log_file", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LogFile(id={self.id}, filename='{self.filename}', type='{self.log_type.value}')>"


class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    log_file_id = Column(Integer, ForeignKey("log_files.id"), nullable=False)
    line_number = Column(Integer, nullable=False)
    raw_content = Column(Text, nullable=False)
    parsed_content = Column(JSON)
    timestamp = Column(DateTime(timezone=True))
    log_level = Column(Enum(LogLevel))
    source = Column(String(100))
    message = Column(Text)
    problem_detected = Column(Boolean, default=False)
    problem_type = Column(String(100))
    problem_description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    log_file = relationship("LogFile", back_populates="log_entries")

    def __repr__(self):
        return f"<LogEntry(id={self.id}, line={self.line_number}, level='{self.log_level}')>"


class ParseRule(Base):
    __tablename__ = "parse_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    rule_type = Column(Enum(ParseRuleType), nullable=False)
    pattern = Column(Text, nullable=False)
    problem_type = Column(String(100))
    problem_description = Column(Text)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    creator = relationship("User", backref="created_rules")

    def __repr__(self):
        return f"<ParseRule(id={self.id}, name='{self.name}', type='{self.rule_type.value}')>" 