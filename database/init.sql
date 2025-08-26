-- 日志分析平台数据库初始化脚本

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS loganalyzer;

-- 使用数据库
\c loganalyzer;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建索引函数
CREATE OR REPLACE FUNCTION create_indexes_if_not_exists() RETURNS void AS $$
BEGIN
    -- 为日志条目创建全文搜索索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_log_entries_search'
    ) THEN
        CREATE INDEX idx_log_entries_search ON log_entries USING gin(to_tsvector('english', raw_content));
    END IF;

    -- 为时间戳创建索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_log_entries_timestamp'
    ) THEN
        CREATE INDEX idx_log_entries_timestamp ON log_entries (timestamp);
    END IF;

    -- 为问题检测创建索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_log_entries_problem'
    ) THEN
        CREATE INDEX idx_log_entries_problem ON log_entries (problem_detected, problem_type);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 创建默认管理员用户的函数
CREATE OR REPLACE FUNCTION create_default_admin() RETURNS void AS $$
BEGIN
    -- 这里只是占位，实际的用户创建会通过应用程序处理
    -- 因为需要密码哈希等处理
    NULL;
END;
$$ LANGUAGE plpgsql; 