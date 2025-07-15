#!/bin/bash

# Chrome 浏览器启动脚本 (CDP 模式)

echo "🌐 启动 Chrome 浏览器 (CDP 模式)"
echo "================================"

# 检查 Chrome 是否已安装
CHROME_PATH=""
if command -v google-chrome &> /dev/null; then
    CHROME_PATH="google-chrome"
elif command -v chromium-browser &> /dev/null; then
    CHROME_PATH="chromium-browser"
elif command -v chromium &> /dev/null; then
    CHROME_PATH="chromium"
elif [ -f "/home/jeff/.cache/ms-playwright/chromium-1124/chrome-linux/chrome" ]; then
    CHROME_PATH="/home/jeff/.cache/ms-playwright/chromium-1124/chrome-linux/chrome"
else
    echo "❌ 错误: 未找到 Chrome/Chromium 浏览器"
    echo "请安装 Chrome 或 Chromium:"
    echo "  sudo apt install google-chrome-stable"
    echo "  # 或"
    echo "  sudo apt install chromium-browser"
    exit 1
fi

echo "✅ 找到浏览器: $CHROME_PATH"

# 设置 CDP 调试端口
CDP_PORT=9222

# 检查端口是否被占用
if lsof -i:$CDP_PORT > /dev/null 2>&1; then
    echo "⚠️  端口 $CDP_PORT 已被占用"
    echo "正在终止占用端口的进程..."
    pkill -f "remote-debugging-port=$CDP_PORT"
    sleep 2
fi

# 设置用户数据目录
USER_DATA_DIR="./browser_data/cdp_xhs_user_data_dir"
mkdir -p "$USER_DATA_DIR"

echo "🚀 启动 Chrome 浏览器..."
echo "   调试端口: $CDP_PORT"
echo "   用户数据目录: $USER_DATA_DIR"
echo

# 启动 Chrome 并在后台运行
nohup $CHROME_PATH \
  --remote-debugging-port=$CDP_PORT \
  --user-data-dir="$USER_DATA_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --disable-background-timer-throttling \
  --disable-backgrounding-occluded-windows \
  --disable-renderer-backgrounding \
  --disable-features=TranslateUI \
  --disable-ipc-flooding-protection \
  "https://www.xiaohongshu.com" \
  > /tmp/chrome_cdp.log 2>&1 &

CHROME_PID=$!

echo "✅ Chrome 浏览器已启动"
echo "   进程 ID: $CHROME_PID"
echo "   调试地址: http://localhost:$CDP_PORT"
echo

echo "📋 接下来请执行以下步骤:"
echo "1. 浏览器会自动打开小红书网站"
echo "2. 完成登录（扫码或账号密码）"
echo "3. 确保登录成功后，保持浏览器开启"
echo "4. 然后运行: ./run.sh"
echo

echo "🔧 管理命令:"
echo "   查看浏览器日志: tail -f /tmp/chrome_cdp.log"
echo "   查看调试页面: firefox http://localhost:$CDP_PORT"
echo "   停止浏览器: kill $CHROME_PID"
echo

# 等待浏览器完全启动
sleep 3

# 检查浏览器是否成功启动
if ps -p $CHROME_PID > /dev/null; then
    echo "✅ 浏览器启动成功！"
    echo "💡 提示: 完成登录后运行 './run.sh' 开始爬取"
else
    echo "❌ 浏览器启动失败，请检查日志: /tmp/chrome_cdp.log"
fi