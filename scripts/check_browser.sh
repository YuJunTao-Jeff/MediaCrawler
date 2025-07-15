#!/bin/bash

# Chrome 浏览器状态检查脚本

echo "🔍 检查 Chrome 浏览器 (CDP 模式) 状态"
echo "===================================="

# 检查 CDP 进程
CDP_PROCESSES=$(ps aux | grep "remote-debugging-port" | grep -v grep)

if [ -z "$CDP_PROCESSES" ]; then
    echo "❌ CDP 模式 Chrome 未运行"
    echo
    echo "💡 启动浏览器: ./start_browser.sh"
else
    echo "✅ CDP 模式 Chrome 正在运行"
    echo
    echo "📋 进程信息:"
    echo "$CDP_PROCESSES"
    echo
    
    # 提取进程 ID
    PID=$(echo "$CDP_PROCESSES" | awk '{print $2}' | head -1)
    echo "🆔 主进程 ID: $PID"
fi

echo
echo "🌐 网络状态:"

# 检查调试端口
if lsof -i:9222 > /dev/null 2>&1; then
    echo "✅ 调试端口 9222: 监听中"
    echo "🔗 调试地址: http://localhost:9222"
else
    echo "❌ 调试端口 9222: 未监听"
fi

echo
echo "📁 用户数据目录:"
USER_DATA_DIR="./browser_data/cdp_xhs_user_data_dir"
if [ -d "$USER_DATA_DIR" ]; then
    echo "✅ 目录存在: $USER_DATA_DIR"
    echo "📊 目录大小: $(du -sh "$USER_DATA_DIR" 2>/dev/null | cut -f1)"
else
    echo "❌ 目录不存在: $USER_DATA_DIR"
fi

echo
echo "📜 日志文件:"
if [ -f "/tmp/chrome_cdp.log" ]; then
    echo "✅ 日志文件: /tmp/chrome_cdp.log"
    echo "📄 最新日志 (最后10行):"
    echo "------------------------"
    tail -10 /tmp/chrome_cdp.log
else
    echo "❌ 日志文件不存在"
fi

echo
echo "🔧 管理命令:"
echo "   启动浏览器: ./start_browser.sh"
echo "   停止浏览器: ./stop_browser.sh"
echo "   查看完整日志: cat /tmp/chrome_cdp.log"
echo "   调试页面: firefox http://localhost:9222"