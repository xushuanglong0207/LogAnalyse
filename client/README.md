# 日志分析工具 - 桌面客户端

🖥️ **专业的桌面端日志分析工具**

支持Windows和macOS系统，提供单个文件分析和批量压缩包分析功能，具备强大的规则管理和双向同步能力。

## ✨ 主要特性

- 🔍 **单个分析**: 选择单个日志文件进行深度分析，快速定位问题
- 📦 **批量分析**: 上传压缩包，自动解压并分析所有日志文件
- ⚙️ **规则管理**: 管理本地和服务端规则，支持双向同步
- 📊 **分析报告**: 生成详细的HTML/PDF格式分析报告
- 🌓 **主题切换**: 支持明暗主题切换
- 🔄 **双向同步**: 本地和服务端规则智能同步
- 🛡️ **安全可靠**: 本地处理，数据安全有保障
- ⚡ **高效处理**: 多线程并发，快速分析大文件

## 🚀 快速开始

### 环境要求

- Node.js >= 16.0.0
- npm >= 8.0.0

### 安装依赖

```bash
cd client
npm install
```

### 开发模式

```bash
# 启动React开发服务器
npm start

# 在新终端中启动Electron
npm run electron-dev
```

### 构建应用

```bash
# 构建React应用
npm run build

# 打包Electron应用
npm run dist

# 分别打包不同平台
npm run dist-win    # Windows
npm run dist-mac    # macOS
```

## 📁 项目结构

```
client/
├── public/
│   ├── electron.js         # Electron主进程
│   └── index.html         # HTML模板
├── src/
│   ├── components/        # React组件
│   │   └── Sidebar.js    # 侧边栏组件
│   ├── pages/            # 页面组件
│   │   ├── HomePage.js           # 首页
│   │   ├── SingleAnalysisPage.js # 单个分析
│   │   ├── BulkAnalysisPage.js   # 批量分析
│   │   ├── RuleManagePage.js     # 规则管理
│   │   ├── ReportPage.js         # 分析报告
│   │   └── SettingsPage.js       # 设置
│   ├── utils/            # 工具类
│   │   └── electronAPI.js # Electron API封装
│   ├── App.js            # 主应用组件
│   ├── App.css           # 应用样式
│   └── index.js          # 应用入口
├── package.json          # 项目配置
└── README.md            # 项目说明
```

## 🎯 功能模块

### 1. 单个分析
- 支持多种日志格式（.log, .txt等）
- 拖拽或点击选择文件
- 实时分析进度显示
- 错误上下文展示

### 2. 批量分析
- 支持多种压缩格式（.zip, .rar, .7z, .tar, .gz）
- 自动解压和文件识别
- 并发处理多个文件
- 统一的分析结果展示

### 3. 规则管理
- 本地规则存储
- 服务端规则同步
- 规则增删改查
- 双向同步功能

### 4. 分析报告
- 错误统计和分类
- 详细的错误上下文
- 支持导出HTML/PDF
- 图表和可视化展示

## 🔧 技术栈

- **前端框架**: React 18
- **UI组件库**: Ant Design 5
- **路由管理**: React Router 6
- **桌面框架**: Electron 28
- **构建工具**: React Scripts
- **打包工具**: Electron Builder

## 📦 打包配置

应用支持打包成以下格式：

- **Windows**: NSIS安装包 (.exe)
- **macOS**: DMG磁盘映像 (.dmg)

打包后的应用具有以下特性：
- 自动创建桌面快捷方式
- 自动创建开始菜单快捷方式
- 支持自定义安装目录
- 应用图标和元数据

## 🛠️ 开发指南

### 添加新页面

1. 在 `src/pages/` 目录下创建新的页面组件
2. 在 `src/App.js` 中添加路由配置
3. 在 `src/components/Sidebar.js` 中添加菜单项

### 添加Electron功能

1. 在 `public/electron.js` 中添加IPC处理
2. 在 `src/utils/electronAPI.js` 中添加API封装
3. 在React组件中调用相应的API

### 样式定制

- 全局样式：修改 `src/App.css`
- 组件样式：使用Ant Design的theme配置
- 主题切换：通过ConfigProvider动态切换

## 🐛 常见问题

### Q: 应用启动后白屏？
A: 检查React开发服务器是否正常启动，确保端口3000可用。

### Q: 打包失败？
A: 确保所有依赖都已正确安装，检查网络连接是否正常。

### Q: 文件选择不工作？
A: 检查Electron的安全策略配置，确保nodeIntegration已启用。

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 👥 贡献

欢迎提交Issue和Pull Request！

## 📞 支持

如有问题，请联系开发团队：
- 邮箱: support@loganalyzer.com
- 项目地址: https://github.com/loganalyzer/desktop-client

---

© 2024 LogAnalyzer Team. All rights reserved. 