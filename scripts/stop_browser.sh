#!/bin/bash

# Chrome 浏览器停止脚本

echo "🔴 停止 Chrome 浏览器 (CDP 模式)"
echo "==============================="

# 查找并终止 Chrome CDP 进程
CDP_PROCESSES=$(ps aux | grep "remote-debugging-port" | grep -v grep)

if [ -z "$CDP_PROCESSES" ]; then
    echo "ℹ️  未找到运行中的 CDP 模式 Chrome 进程"
else
    echo "📋 找到以下 CDP 进程:"
    echo "$CDP_PROCESSES"
    echo
    
    echo "🔄 正在终止进程..."
    pkill -f "remote-debugging-port"
    sleep 2
    
    # 强制终止如果还有残留进程
    if ps aux | grep "remote-debugging-port" | grep -v grep > /dev/null; then
        echo "⚠️  强制终止残留进程..."
        pkill -9 -f "remote-debugging-port"
    fi
    
    echo "✅ Chrome CDP 进程已停止"
fi

# 清理临时文件
if [ -f "/tmp/chrome_cdp.log" ]; then
    echo "🧹 清理日志文件..."
    rm -f /tmp/chrome_cdp.log
fi

# 检查端口是否释放
if lsof -i:9222 > /dev/null 2>&1; then
    echo "⚠️  端口 9222 仍被占用"
    echo "请手动检查: lsof -i:9222"
else
    echo "✅ 端口 9222 已释放"
fi

echo
echo "✅ 浏览器停止完成"