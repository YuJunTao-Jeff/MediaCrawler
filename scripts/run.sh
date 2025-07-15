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
echo "   - 平台: 小红书 (xhs)"
echo "   - 登录方式: 二维码登录"
echo "   - 爬取类型: 关键词搜索"
echo "   - 关键词: appen,澳鹏,田小鹏,爱普恩,澳鹏大连,澳鹏无锡,澳鹏科技,澳鹏中国,澳鹏数据,澳鹏重庆"
echo "   - CDP 模式: 已启用"
echo "   - 数据保存: MySQL 数据库"
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
    echo "1. 浏览器会自动打开小红书网站"
    echo "2. 完成登录（扫码或账号密码）"
    echo "3. 确保登录成功后，按 Enter 继续"
    echo
    read -p "✅ 已完成小红书登录？按 Enter 继续..." dummy
else
    echo "✅ CDP 模式浏览器已运行"
    echo
    read -p "🔍 请确认已登录小红书，按 Enter 继续..." dummy
fi

echo
echo "🚀 启动 MediaCrawler..."

# # 初始化数据库表结构（如果需要）
# if ! mysql -u root -e "USE media_crawler; SHOW TABLES;" 2>/dev/null | grep -q "xhs_note"; then
#     echo "🗄️ 初始化数据库表结构..."
#     python db.py
# fi

# 启动爬虫
python main.py --platform xhs --lt qrcode --type search
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