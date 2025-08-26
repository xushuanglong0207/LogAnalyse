#!/bin/bash

# 修复脚本 - 安装缺失的依赖
echo "🔧 修复日志分析平台环境"
echo "====================="

# 检查系统类型
if command -v apt &> /dev/null; then
    PACKAGE_MANAGER="apt"
elif command -v yum &> /dev/null; then
    PACKAGE_MANAGER="yum"
elif command -v dnf &> /dev/null; then
    PACKAGE_MANAGER="dnf"
else
    echo "❌ 不支持的系统，请手动安装python3-venv"
    exit 1
fi

echo "📦 检测到包管理器: $PACKAGE_MANAGER"

# 安装python3-venv
echo "🐍 安装Python虚拟环境支持..."
case $PACKAGE_MANAGER in
    "apt")
        sudo apt update
        sudo apt install -y python3-venv python3-pip
        ;;
    "yum")
        sudo yum install -y python3-venv python3-pip
        ;;
    "dnf")
        sudo dnf install -y python3-venv python3-pip
        ;;
esac

if [ $? -eq 0 ]; then
    echo "✅ Python虚拟环境支持安装成功"
else
    echo "❌ 安装失败，请手动安装"
    exit 1
fi

# 清理旧的虚拟环境
if [ -d "venv" ]; then
    echo "🧹 清理旧的虚拟环境..."
    rm -rf venv
fi

# 测试虚拟环境创建
echo "🧪 测试虚拟环境创建..."
python3 -m venv test_venv
if [ $? -eq 0 ]; then
    echo "✅ 虚拟环境测试成功"
    rm -rf test_venv
    echo "🎉 修复完成！现在可以运行 ./start.sh"
else
    echo "❌ 虚拟环境创建仍然失败"
    exit 1
fi