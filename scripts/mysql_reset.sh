#!/bin/bash

# MySQL 数据库重置脚本

echo "⚠️  警告: 这将删除所有爬取的数据！"
echo "是否确认重置数据库？(y/N): "
read -r confirmation

if [[ $confirmation =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔄 正在重置数据库..."
    
    # 确保 MySQL 服务运行
    if ! sudo service mysql status > /dev/null 2>&1; then
        echo "启动 MySQL 服务..."
        sudo service mysql start
        sleep 2
    fi
    
    # 删除并重新创建数据库
    echo "删除旧数据库..."
    mysql -u root -e "DROP DATABASE IF EXISTS media_crawler;"
    
    echo "创建新数据库..."
    mysql -u root -e "CREATE DATABASE media_crawler;"
    
    # 重新导入表结构
    echo "导入表结构..."
    if python db.py; then
        echo "✅ 数据库重置完成"
        echo ""
        echo "📊 数据库状态："
        mysql -u root -e "USE media_crawler; SHOW TABLES;"
    else
        echo "❌ 表结构导入失败"
    fi
    
else
    echo "❌ 操作已取消"
fi