# 🐳 Docker 日志分析平台

## 📋 系统概述

这是一个基于Docker的日志分析平台，支持多用户并发使用，具备文件上传、智能分析、问题分类等功能。

## 🚀 快速启动

### 1. 启动平台
```bash
./docker-start.sh start
```

### 2. 访问地址
- 前端界面: http://localhost:3000
- API文档: http://localhost:8001/docs
- 数据库: localhost:5433 (用户名: admin, 密码: password123)

## 📦 系统架构

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   前端Web   │────│   后端API    │────│  PostgreSQL │
│ (Next.js)   │    │  (FastAPI)   │    │  数据库     │
└─────────────┘    └──────────────┘    └─────────────┘
                           │
                    ┌──────────────┐
                    │    Redis     │
                    │   缓存服务    │
                    └──────────────┘
```

## 🛠️ 管理脚本

### 主要脚本

1. **docker-start.sh** - Docker容器管理脚本
   ```bash
   ./docker-start.sh start    # 启动平台
   ./docker-start.sh stop     # 停止服务
   ./docker-start.sh restart  # 重启服务
   ./docker-start.sh status   # 查看状态
   ./docker-start.sh logs     # 查看日志
   ./docker-start.sh backup   # 备份数据
   ```

2. **monitor.sh** - 系统监控脚本
   ```bash
   ./monitor.sh start   # 启动后台监控
   ./monitor.sh status  # 实时状态显示
   ./monitor.sh stop    # 停止监控
   ./monitor.sh logs    # 查看监控日志
   ```

3. **diagnose.sh** - 问题诊断脚本
   ```bash
   ./diagnose.sh check       # 系统诊断
   ./diagnose.sh fix         # 自动修复
   ./diagnose.sh performance # 性能分析
   ./diagnose.sh solutions   # 解决方案
   ```

## 📁 目录结构

```
project-v2/
├── docker-compose.yml     # Docker编排配置
├── docker-start.sh        # Docker管理脚本
├── monitor.sh            # 监控脚本
├── diagnose.sh           # 诊断脚本
├── frontend/             # 前端代码
├── backend/              # 后端代码
└── database/             # 数据持久化目录
    ├── uploads/          # 上传文件存储
    ├── logs/            # 系统日志
    └── backups/         # 数据备份
```

## ⚙️ 系统配置

### 资源限制
- 后端: CPU 2核, 内存 2GB
- 前端: CPU 1核, 内存 1GB  
- 数据库: CPU 1核, 内存 1GB
- 最大文件上传: 10MB
- 并发分析任务: 2个

### 环境变量
```env
MAX_CONTENT_BYTES=10485760      # 最大文件大小
ANALYSIS_WORKERS=2              # 分析并发数
MAX_CONCURRENT_ANALYSIS=3       # 最大同时分析数
REQUEST_TIMEOUT=300             # 请求超时时间
```

## 🔧 常见问题

### 问题1: 服务启动失败
**症状**: 容器无法启动或端口占用
**解决方案**:
```bash
./diagnose.sh check    # 诊断问题
./diagnose.sh fix      # 自动修复
./docker-start.sh restart
```

### 问题2: 文件上传失败/系统崩溃
**症状**: 7MB文件上传后系统无响应
**原因**: 
- 多用户同时使用导致资源耗尽
- 并发分析任务过多
- 内存不足

**解决方案**:
```bash
# 立即重启释放资源
./docker-start.sh restart

# 启动监控防止再次发生
./monitor.sh start

# 检查系统资源
./diagnose.sh performance
```

### 问题3: 数据丢失
**症状**: 重启容器后数据消失
**原因**: 持久化配置问题或volumes被删除
**解决方案**:
```bash
# 检查数据目录
ls -la ./database/

# 恢复备份
./docker-start.sh restore

# 如果没有备份，重新初始化
./docker-start.sh clean
./docker-start.sh start
```

### 问题4: 性能缓慢
**症状**: 分析速度慢，界面卡顿
**优化方案**:
```bash
# 性能分析
./diagnose.sh performance

# 启动监控
./monitor.sh start

# 限制并发用户数量
# 清理旧文件释放空间
# 增加系统内存
```

## 🔒 安全建议

1. **生产环境配置**:
   - 修改数据库密码
   - 更改SECRET_KEY
   - 关闭DEBUG模式
   - 配置HTTPS

2. **访问控制**:
   - 设置防火墙规则
   - 限制管理员权限
   - 定期备份数据

## 📊 监控和维护

### 自动监控功能
- 服务健康检查 (每30秒)
- 自动重启异常服务
- 资源使用监控
- 磁盘空间检查
- 自动日志轮转
- 凌晨2点自动备份

### 手动维护
```bash
# 每日检查
./diagnose.sh check
./docker-start.sh status

# 每周备份
./docker-start.sh backup

# 每月清理
./diagnose.sh fix
docker system prune -f
```

## 🆘 技术支持

### 日志位置
- 应用日志: `./database/logs/`
- 监控日志: `./database/logs/monitor.log`
- 容器日志: `docker compose logs`

### 调试命令
```bash
# 查看容器状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 进入容器调试
docker compose exec backend bash
docker compose exec postgres psql -U admin -d loganalyzer

# 查看资源使用
docker stats

# 网络诊断
docker network ls
docker network inspect project-v2_app
```

## 📈 性能优化

### 高负载处理
1. **增加系统资源**: CPU和内存
2. **优化数据库**: 添加索引、定期维护
3. **负载均衡**: 多实例部署
4. **缓存优化**: Redis配置调优
5. **文件管理**: 定期清理大文件

### 扩展方案
- 使用Nginx反向代理
- 配置Docker Swarm集群
- 使用外部数据库服务
- CDN加速静态资源

---

## 🎯 更新日志

### v2.0 (当前版本)
- ✅ Docker容器化部署
- ✅ 自动监控和恢复
- ✅ 系统资源限制
- ✅ 数据持久化保证
- ✅ 完整的管理脚本
- ✅ 问题诊断工具

### 已知限制
- 单机部署，不支持集群
- 文件大小限制10MB
- 并发用户建议不超过10人

---

**记住**: 在生产环境中，务必修改默认密码并启用HTTPS！