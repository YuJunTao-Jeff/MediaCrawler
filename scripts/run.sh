#!/bin/bash

# MediaCrawler 启动脚本
# 支持平台配置文件和参数透传到 Python main.py

# 获取所有传入的参数
SCRIPT_ARGS="$@"

# 默认平台
DEFAULT_PLATFORM="xhs"

# 平台配置加载函数
load_platform_config() {
    local platform=$1
    local config_file="scripts/config/${platform}.json"
    
    if [ -f "$config_file" ]; then
        echo "📋 加载平台配置: $config_file"
        
        # 检查 jq 是否安装
        if ! command -v jq &> /dev/null; then
            echo "⚠️  警告: jq 未安装，无法解析配置文件，使用默认配置"
            return 1
        fi
        
        # 读取CDP模式设置
        CDP_MODE=$(jq -r '.cdp_mode' "$config_file" 2>/dev/null || echo "false")
        # 读取默认参数
        DEFAULT_ARGS=$(jq -r '.default_args' "$config_file" 2>/dev/null || echo "")
        # 读取配置描述
        DESCRIPTION=$(jq -r '.description' "$config_file" 2>/dev/null || echo "")
        
        echo "   - 配置说明: $DESCRIPTION"
        echo "   - CDP模式: $CDP_MODE"
        echo "   - 默认参数: $DEFAULT_ARGS"
        
        return 0
    else
        echo "⚠️  警告: 配置文件 $config_file 不存在，使用默认配置"
        return 1
    fi
}

# 从参数中提取平台
extract_platform() {
    local args="$1"
    if [[ "$args" == *"--platform"* ]]; then
        echo "$args" | grep -o -- '--platform [^ ]*' | cut -d' ' -f2
    else
        echo "$DEFAULT_PLATFORM"
    fi
}

# 检查是否为帮助请求
if [[ "$SCRIPT_ARGS" == *"--help"* ]] || [[ "$SCRIPT_ARGS" == *"-h"* ]]; then
    echo "MediaCrawler 启动脚本"
    echo "用法: $0 [选项]"
    echo ""
    echo "支持的平台配置:"
    echo "  --platform xhs      小红书 (默认，CDP模式)"
    echo "  --platform bili     B站 (CDP模式)"
    echo "  --platform zhihu    知乎 (标准模式)"
    echo "  --platform wb       微博 (标准模式)"
    echo "  --platform dy       抖音 (标准模式)"
    echo "  --platform ks       快手 (标准模式)"
    echo "  --platform tieba    贴吧 (标准模式)"
    echo ""
    echo "特殊参数:"
    echo "  --show-config       显示平台配置信息"
    echo "  --help, -h          显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --platform xhs"
    echo "  $0 --platform zhihu --keywords \"澳鹏科技\""
    echo "  $0 --platform xhs --show-config"
    exit 0
fi

# 提取平台信息
PLATFORM=$(extract_platform "$SCRIPT_ARGS")

# 显示配置信息
if [[ "$SCRIPT_ARGS" == *"--show-config"* ]]; then
    echo "🔍 显示平台配置: $PLATFORM"
    echo "=========================="
    load_platform_config "$PLATFORM"
    echo "=========================="
    echo "📁 配置文件位置: scripts/config/${PLATFORM}.json"
    exit 0
fi

# 加载平台配置
echo "🚀 启动 MediaCrawler (${PLATFORM} 爬虫)"
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

# 加载平台配置
load_platform_config "$PLATFORM"

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

# 构建最终参数
FINAL_ARGS=""

# 添加平台参数
FINAL_ARGS="$FINAL_ARGS --platform $PLATFORM"

# 添加CDP模式参数
if [[ -n "$CDP_MODE" ]]; then
    FINAL_ARGS="$FINAL_ARGS --cdp_mode $CDP_MODE"
fi

# 添加平台默认参数
if [[ -n "$DEFAULT_ARGS" ]]; then
    FINAL_ARGS="$FINAL_ARGS $DEFAULT_ARGS"
fi

# 添加用户自定义参数（会覆盖默认参数）
if [[ -n "$SCRIPT_ARGS" ]]; then
    # 移除 --show-config 参数
    USER_ARGS=$(echo "$SCRIPT_ARGS" | sed 's/--show-config//g')
    FINAL_ARGS="$FINAL_ARGS $USER_ARGS"
fi

echo "🔧 配置信息:"
echo "   - 平台: $PLATFORM"
echo "   - CDP模式: $CDP_MODE"
echo "   - 最终参数: $FINAL_ARGS"
echo

# 检查浏览器是否需要启动（仅CDP模式）
if [[ "$CDP_MODE" == "true" ]]; then
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
else
    echo "🌐 使用标准模式，无需启动CDP浏览器"
fi

echo
echo "🚀 启动 MediaCrawler..."

# 启动爬虫
echo "🔧 使用配置启动..."
python main.py $FINAL_ARGS
CRAWLER_EXIT_CODE=$?

echo
if [ $CRAWLER_EXIT_CODE -eq 0 ]; then
    echo "✅ MediaCrawler 运行完成"
    
    # 显示爬取统计
    echo "📊 爬取统计:"
    case "$PLATFORM" in
        "xhs")
            sudo mysql -u root -e "USE media_crawler; SELECT COUNT(*) as '笔记数量' FROM xhs_note;" 2>/dev/null || echo "   无法获取统计信息"
            sudo mysql -u root -e "USE media_crawler; SELECT COUNT(*) as '评论数量' FROM xhs_note_comment;" 2>/dev/null || echo "   无法获取评论统计"
            ;;
        "zhihu")
            sudo mysql -u root -e "USE media_crawler; SELECT COUNT(*) as '内容数量' FROM zhihu_content;" 2>/dev/null || echo "   无法获取统计信息"
            sudo mysql -u root -e "USE media_crawler; SELECT COUNT(*) as '评论数量' FROM zhihu_comment;" 2>/dev/null || echo "   无法获取评论统计"
            ;;
        "wb")
            sudo mysql -u root -e "USE media_crawler; SELECT COUNT(*) as '微博数量' FROM weibo_note;" 2>/dev/null || echo "   无法获取统计信息"
            sudo mysql -u root -e "USE media_crawler; SELECT COUNT(*) as '评论数量' FROM weibo_comment;" 2>/dev/null || echo "   无法获取评论统计"
            ;;
        *)
            echo "   平台: $PLATFORM"
            ;;
    esac
    
else
    echo "❌ MediaCrawler 运行出错 (退出码: $CRAWLER_EXIT_CODE)"
fi

echo "📁 数据保存位置: MySQL 数据库 (media_crawler)"
echo "🔗 使用 DataGrip 查看: jdbc:mysql://localhost:3306/media_crawler"
echo "⏰ 结束时间: $(date)"

# 询问是否保持浏览器运行（仅CDP模式）
if [[ "$CDP_MODE" == "true" ]]; then
    echo
    read -p "🌐 是否关闭浏览器？(y/N): " close_browser
    if [[ $close_browser =~ ^[Yy]$ ]]; then
        ./scripts/stop_browser.sh
    fi
fi