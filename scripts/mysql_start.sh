#!/bin/bash

# MySQL 启动脚本

echo "正在启动 MySQL 服务..."

# 启动 MySQL 服务
sudo service mysql start

# 检查启动状态
if sudo service mysql status > /dev/null 2>&1; then
    echo "✅ MySQL 服务启动成功"
    
    # 显示连接信息
    echo ""
    echo "📊 数据库连接信息："
    echo "   主机: localhost"
    echo "   端口: 3306"
    echo "   用户: root"
    echo "   密码: (空)"
    echo "   数据库: media_crawler"
    echo ""
    echo "🔗 DataGrip 连接 URL: jdbc:mysql://localhost:3306/media_crawler"
    
else
    echo "❌ MySQL 服务启动失败"
    echo "请检查 MySQL 是否正确安装"
fi