#!/bin/bash

# MediaCrawler 启动脚本
# 使用 CDP 模式爬取小红书数据

echo "🚀 启动 MediaCrawler (小红书爬虫)"
echo "📍 当前目录: $(pwd)"
echo "⏰ 启动时间: $(date)"
echo

# 设置显示环境变量 (WSL 环境需要)
export DISPLAY=:0

# 检查是否在正确的目录
if [ ! -f "main.py" ]; then
    echo "❌ 错误: 请在 MediaCrawler 项目根目录下运行此脚本"
    exit 1
fi

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 错误: 未找到虚拟环境，请先运行 'uv sync'"
    exit 1
fi

echo "🔧 配置信息:"
echo "   - 平台: 小红书 (xhs)"
echo "   - 登录方式: 二维码登录"
echo "   - 爬取类型: 关键词搜索"
echo "   - CDP 模式: 已启用"
echo "   - 数据保存: JSON 格式"
echo

echo "🌐 启动 MediaCrawler..."
python main.py --platform xhs --lt qrcode --type search

echo
echo "✅ MediaCrawler 运行完成"
echo "📁 数据保存位置: ./data/xhs/json/"
echo "⏰ 结束时间: $(date)"