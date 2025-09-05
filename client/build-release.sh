#!/bin/bash

echo "========================================"
echo "日志分析工具 v1.0.0 打包脚本"
echo "作者: xushuanglong"
echo "========================================"

# 检查环境
echo ""
echo "正在检查环境..."

if ! command -v node &> /dev/null; then
    echo "错误: 未找到 Node.js，请先安装 Node.js"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "错误: 未找到 npm，请先安装 npm"
    exit 1
fi

echo "Node.js 版本: $(node --version)"
echo "npm 版本: $(npm --version)"
echo "环境检查通过"

# 安装依赖
echo ""
echo "正在安装依赖..."
npm install
if [ $? -ne 0 ]; then
    echo "错误: 依赖安装失败"
    exit 1
fi

# 构建应用
echo ""
echo "正在构建 React 应用..."
npm run build
if [ $? -ne 0 ]; then
    echo "错误: React 应用构建失败"
    exit 1
fi

# 检测操作系统并打包
echo ""
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "检测到 macOS，正在打包 macOS 版本..."
    npm run dist-mac
    if [ $? -ne 0 ]; then
        echo "错误: macOS 版本打包失败"
        exit 1
    fi
    
    echo ""
    echo "========================================"
    echo "打包完成！"
    echo "输出目录: dist/"
    echo "安装包: 日志分析工具-1.0.0.dmg"
    echo "========================================"
    
    if [ -f "dist/日志分析工具-1.0.0.dmg" ]; then
        echo "文件大小: $(ls -lh dist/日志分析工具-1.0.0.dmg | awk '{print $5}')"
        echo ""
        read -p "是否打开输出目录？ (y/n): " choice
        if [[ $choice == [Yy]* ]]; then
            open dist
        fi
    else
        echo "警告: 未找到预期的安装包文件"
    fi
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "检测到 Linux，正在打包 Linux 版本..."
    npm run dist
    if [ $? -ne 0 ]; then
        echo "错误: Linux 版本打包失败"
        exit 1
    fi
    
    echo ""
    echo "========================================"
    echo "打包完成！"
    echo "输出目录: dist/"
    echo "========================================"
    
    ls -la dist/
    
else
    echo "未知操作系统，尝试打包所有平台..."
    npm run dist
    if [ $? -ne 0 ]; then
        echo "错误: 打包失败"
        exit 1
    fi
    
    echo ""
    echo "========================================"
    echo "打包完成！"
    echo "输出目录: dist/"
    echo "========================================"
    
    ls -la dist/
fi

echo ""
echo "打包脚本执行完成！"
