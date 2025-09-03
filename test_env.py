#!/usr/bin/env python3

import os
from dotenv import load_dotenv

# 测试.env文件加载
env_path = '/home/ugreen/log-analyse/backend/.env'
print(f"Testing .env loading from: {env_path}")

# 检查文件是否存在
if os.path.exists(env_path):
    print(f"✅ .env file exists")
else:
    print(f"❌ .env file does not exist")
    exit(1)

# 加载环境变量
load_dotenv(env_path, override=True)

# 检查环境变量
smtp_server = os.getenv('SMTP_SERVER')
smtp_username = os.getenv('SMTP_USERNAME')
smtp_password = os.getenv('SMTP_PASSWORD')
sender_name = os.getenv('SENDER_NAME')

print(f"SMTP_SERVER: '{smtp_server}'")
print(f"SMTP_USERNAME: '{smtp_username}'")
print(f"SMTP_PASSWORD: '{smtp_password}'")
print(f"SENDER_NAME: '{sender_name}'")

if smtp_server and smtp_username:
    print("✅ Environment variables loaded successfully")
else:
    print("❌ Environment variables not loaded properly")