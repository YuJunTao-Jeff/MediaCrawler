#!/bin/bash

# MySQL 停止脚本

echo "正在停止 MySQL 服务..."

# 停止 MySQL 服务
sudo service mysql stop

# 检查停止状态
if ! sudo service mysql status > /dev/null 2>&1; then
    echo "✅ MySQL 服务已停止"
else
    echo "❌ MySQL 服务停止失败"
fi