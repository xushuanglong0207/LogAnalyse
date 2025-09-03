#!/usr/bin/env python3
"""
简单的数据库初始化脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models import User
from app.auth.password import get_password_hash
from sqlalchemy.orm import sessionmaker

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
            hashed_password=get_password_hash("admin123")
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