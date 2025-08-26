# 日志分析平台

高性能的 syslog 和 kernlog 日志分析平台

## 🚀 快速启动

```bash
# 设置权限
chmod +x start.sh

# 启动平台
./start.sh
```

## 📱 访问地址

- **前端界面**: http://localhost:3000
- **API文档**: http://localhost:8001/docs

## 🔧 功能特性

- 📁 **智能日志解析**: 支持 txt、json、log 格式
- 🔍 **问题自动检测**: 内置7种检测规则（OOM、内核错误等）
- 📊 **数据可视化**: 现代化报表和统计
- 👥 **用户管理**: 完整的用户权限系统
- 🌐 **智能网络**: 自动IP检测和配置

## 🛠️ 技术栈

- **前端**: Next.js 15 + TypeScript + Tailwind CSS
- **后端**: FastAPI + Python 3.8+
- **数据库**: PostgreSQL + Redis
- **部署**: Docker + 原生部署

## 📝 使用说明

1. **启动平台**: `./start.sh`
2. **停止服务**: `./start.sh 2`
3. **检查状态**: `./start.sh 4`
4. **获取帮助**: `./start.sh 5` 