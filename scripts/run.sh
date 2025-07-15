#!/bin/bash

# MediaCrawler 启动脚本
# 支持参数透传到 Python main.py

# 获取所有传入的参数
SCRIPT_ARGS="$@"

# 动态显示平台信息
if [[ "$SCRIPT_ARGS" == *"--platform"* ]]; then
    PLATFORM=$(echo "$SCRIPT_ARGS" | grep -o -- '--platform [^ ]*' | cut -d' ' -f2)
    echo "🚀 启动 MediaCrawler (${PLATFORM} 爬虫)"
else
    echo "🚀 启动 MediaCrawler (默认配置)"
fi
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


# 启动 MySQL 数据库
echo "🗄️ 启动 MySQL 数据库..."
if ! sudo service mysql status > /dev/null 2>&1; then
    sudo service mysql start
    sleep 2
    echo "✅ MySQL 服务已启动"
else
    echo "✅ MySQL 服务已运行"
fi
echo

echo "🔧 配置信息:"
if [[ -n "$SCRIPT_ARGS" ]]; then
    echo "   - 使用参数: $SCRIPT_ARGS"
else
    echo "   - 平台: 小红书 (xhs)"
    echo "   - 登录方式: 二维码登录"
    echo "   - 爬取类型: 关键词搜索"
    echo "   - 关键词: appen,澳鹏,田小鹏,爱普恩,澳鹏大连,澳鹏无锡,澳鹏科技,澳鹏中国,澳鹏数据,澳鹏重庆"
    echo "   - 数据保存: MySQL 数据库"
fi
echo

# 检查浏览器是否已启动
echo "🌐 检查浏览器状态..."
if ! lsof -i:9222 > /dev/null 2>&1; then
    echo "❌ CDP 模式浏览器未启动"
    echo
    echo "🚀 自动启动浏览器..."
    ./scripts/start_browser.sh
    echo
    echo "⏳ 等待浏览器完全启动..."
    sleep 5
    
    # 等待用户登录确认
    echo "📋 请在浏览器中完成以下操作:"
    echo "1. 浏览器会自动打开网站"
    echo "2. 完成登录（扫码或账号密码）"
    echo "3. 确保登录成功后，按 Enter 继续"
    echo
    read -p "✅ 已完成登录？按 Enter 继续..." dummy
else
    echo "✅ CDP 模式浏览器已运行"
    echo
    read -p "🔍 请确认已登录，按 Enter 继续..." dummy
fi

echo
echo "🚀 启动 MediaCrawler..."


# 启动爬虫
if [[ -n "$SCRIPT_ARGS" ]]; then
    echo "🔧 使用自定义参数启动..."
    python main.py $SCRIPT_ARGS
else
    echo "🔧 使用默认配置启动..."
    python main.py --platform xhs --lt qrcode --type search
fi
CRAWLER_EXIT_CODE=$?

echo
if [ $CRAWLER_EXIT_CODE -eq 0 ]; then
    echo "✅ MediaCrawler 运行完成"
    
    # 显示爬取统计
    echo "📊 爬取统计:"
    mysql -u root -e "USE media_crawler; SELECT COUNT(*) as '笔记数量' FROM xhs_note;" 2>/dev/null || echo "   无法获取统计信息"
    mysql -u root -e "USE media_crawler; SELECT COUNT(*) as '评论数量' FROM xhs_note_comment;" 2>/dev/null || echo "   无法获取评论统计"
    
else
    echo "❌ MediaCrawler 运行出错 (退出码: $CRAWLER_EXIT_CODE)"
fi

echo "📁 数据保存位置: MySQL 数据库 (media_crawler)"
echo "🔗 使用 DataGrip 查看: jdbc:mysql://localhost:3306/media_crawler"
echo "⏰ 结束时间: $(date)"

# 询问是否保持浏览器运行
echo
read -p "🌐 是否关闭浏览器？(y/N): " close_browser
if [[ $close_browser =~ ^[Yy]$ ]]; then
    ./scripts/stop_browser.sh
fi