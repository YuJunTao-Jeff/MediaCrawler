#!/bin/bash

# MediaCrawler Web监控平台启动脚本

echo "🚀 启动MediaCrawler Web监控平台..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装，请先安装Python3"
    exit 1
fi

# 检查依赖包
echo "📦 检查依赖包..."
pip3 list | grep -q streamlit
if [ $? -ne 0 ]; then
    echo "⚠️  依赖包未安装，正在安装..."
    pip3 install -r requirements.txt
fi

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(dirname $(dirname $(pwd)))"

# 检查数据库连接
echo "🔍 检查数据库连接..."
python3 -c "
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath('.'))))
from web.database.connection import db_manager
if db_manager.test_connection():
    print('✅ 数据库连接正常')
else:
    print('❌ 数据库连接失败，请检查配置')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "数据库连接测试失败，退出启动"
    exit 1
fi

# 启动Web应用
echo "🌐 启动Web应用..."
echo "📍 访问地址: http://localhost:8501"
echo "⏹️  停止应用: Ctrl+C"
echo ""

streamlit run app.py \
    --server.port 8501 \
    --server.address localhost \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --theme.base light \
    --theme.primaryColor "#1f77b4" \
    --theme.backgroundColor "#ffffff" \
    --theme.secondaryBackgroundColor "#f8f9fa" \
    --theme.textColor "#333333"