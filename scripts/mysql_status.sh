#!/bin/bash

# MySQL 状态检查脚本

echo "📊 MySQL 服务状态："
echo "===================="

# 检查 MySQL 服务状态
if sudo service mysql status > /dev/null 2>&1; then
    echo "✅ MySQL 服务: 运行中"
    
    # 检查端口监听
    if sudo netstat -tlnp | grep :3306 > /dev/null 2>&1; then
        echo "✅ 端口 3306: 监听中"
    else
        echo "⚠️  端口 3306: 未监听"
    fi
    
    # 显示连接信息
    echo ""
    echo "🔗 连接信息："
    echo "   mysql -u root media_crawler"
    echo "   jdbc:mysql://localhost:3306/media_crawler"
    
else
    echo "❌ MySQL 服务: 未运行"
    echo ""
    echo "💡 启动服务: ./mysql_start.sh"
fi

echo ""
echo "📈 数据库列表："
mysql -u root -e "SHOW DATABASES;" 2>/dev/null || echo "无法连接到 MySQL"