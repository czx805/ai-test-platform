@echo off

REM AI测试平台启动脚本（Windows）

echo 启动AI测试平台...

REM 检查Python环境
python --version
if errorlevel 1 (
    echo 错误: Python未安装
    exit /b 1
)

REM 检查依赖
if not exist "requirements.txt" (
    echo 错误: requirements.txt不存在
    exit /b 1
)

REM 安装依赖
echo 安装依赖...
pip install -r requirements.txt

REM 安装Playwright浏览器
echo 安装Playwright浏览器...
python -m playwright install

REM 检查配置文件
if not exist "config\ai_config.yaml" (
    echo 创建配置文件...
    python setup.py
)

REM 启动测试
echo 启动测试...
python main.py --action generate --description "测试网站登录功能"

echo AI测试平台启动完成