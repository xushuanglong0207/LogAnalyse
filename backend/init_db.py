#!/usr/bin/env python3
"""
数据库初始化脚本
创建所有必要的表和初始数据
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models import User, LogFile, Report
from app.auth.password import get_password_hash
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """创建所有表"""
    print("创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成!")

def create_admin_user():
    """创建管理员用户"""
    db = SessionLocal()
    try:
        # 检查是否已存在admin用户
        existing_user = db.query(User).filter(User.username == "admin").first()
        if existing_user:
            print("管理员用户已存在，跳过创建")
            return
        
        # 创建管理员用户
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password=get_password_hash("admin123")
        )
        
        db.add(admin_user)
        db.commit()
        print("管理员用户创建成功:")
        print("  用户名: admin")
        print("  密码: admin123")
        print("  邮箱: admin@example.com")
        
    except Exception as e:
        print(f"创建管理员用户失败: {e}")
        db.rollback()
    finally:
        db.close()

def create_default_rules():
    """创建默认检测规则"""
    db = SessionLocal()
    try:
        # 检查是否已存在默认文件夹
        existing_folder = db.query(detection_rule.RuleFolder).filter(
            detection_rule.RuleFolder.name == "默认"
        ).first()
        
        if not existing_folder:
            # 创建默认文件夹
            default_folder = detection_rule.RuleFolder(
                name="默认",
                description="系统默认规则文件夹",
                created_by=1  # admin用户ID
            )
            db.add(default_folder)
            db.commit()
            
            folder_id = default_folder.id
            print("默认规则文件夹创建成功")
        else:
            folder_id = existing_folder.id
            print("默认规则文件夹已存在")
        
        # 创建一些默认检测规则
        default_rules = [
            {
                "name": "错误日志检测",
                "description": "检测包含ERROR关键字的日志",
                "patterns": ["ERROR", "error", "Error"],
                "enabled": True,
                "folder_id": folder_id
            },
            {
                "name": "异常日志检测", 
                "description": "检测包含Exception关键字的日志",
                "patterns": ["Exception", "exception", "EXCEPTION"],
                "enabled": True,
                "folder_id": folder_id
            },
            {
                "name": "失败日志检测",
                "description": "检测包含FAILED或FAIL关键字的日志", 
                "patterns": ["FAILED", "FAIL", "failed", "fail"],
                "enabled": True,
                "folder_id": folder_id
            }
        ]
        
        for rule_data in default_rules:
            existing_rule = db.query(detection_rule.DetectionRule).filter(
                detection_rule.DetectionRule.name == rule_data["name"]
            ).first()
            
            if not existing_rule:
                rule = detection_rule.DetectionRule(
                    name=rule_data["name"],
                    description=rule_data["description"],
                    patterns=rule_data["patterns"],
                    enabled=rule_data["enabled"],
                    folder_id=rule_data["folder_id"],
                    created_by=1
                )
                db.add(rule)
        
        db.commit()
        print("默认检测规则创建完成")
        
    except Exception as e:
        print(f"创建默认规则失败: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """主函数"""
    print("开始初始化数据库...")
    
    try:
        # 1. 创建所有表
        create_tables()
        
        # 2. 创建管理员用户
        create_admin_user()
        
        print("\n数据库初始化完成!")
        print("现在可以启动应用程序了")
        
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()