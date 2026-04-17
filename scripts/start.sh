#!/bin/bash

# AI测试平台启动脚本

echo "启动AI测试平台..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: Python3未安装"
    exit 1
fi

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "错误: requirements.txt不存在"
    exit 1
fi

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 安装Playwright浏览器
echo "安装Playwright浏览器..."
python -m playwright install

# 检查配置文件
if [ ! -f "config/ai_config.yaml" ]; then
    echo "创建配置文件..."
    python setup.py
fi

# 启动测试
echo "启动测试..."
python main.py --action generate --description "测试网站登录功能"

echo "AI测试平台启动完成"