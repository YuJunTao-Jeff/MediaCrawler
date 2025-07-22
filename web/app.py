"""
MediaCrawler Web监控平台主应用
"""

import streamlit as st
import logging
import sys
import os
from datetime import datetime, timedelta
import time

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入组件和工具
from web.config import WEB_CONFIG, LOGGING_CONFIG
from web.database.connection import db_manager
from web.database.queries import SearchFilters
from web.components.filters import create_search_filters
from web.components.search import (
    render_search_box, render_keyword_suggestions, render_search_history,
    render_search_stats, render_search_tips, save_search_to_history,
    render_search_filters_summary
)
from web.components.data_display import (
    render_content_list, render_statistics_overview, render_empty_state
)
from web.utils.data_processor import get_data_processor

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG['level']),
    format=LOGGING_CONFIG['format']
)

logger = logging.getLogger(__name__)

def load_custom_css():
    """加载自定义CSS样式"""
    css = """
    <style>
    /* 主要样式 */
    .main {
        padding-top: 1rem;
    }
    
    /* 标题样式 */
    .main-header {
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        padding: 1rem;
        margin: -1rem -1rem 1rem -1rem;
        border-radius: 0 0 10px 10px;
        color: white;
        text-align: center;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: bold;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* 卡片样式 */
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border-left: 3px solid #1f77b4;
        margin-bottom: 0.8rem;
    }
    
    /* 搜索框样式 */
    .search-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
    }
    
    /* 筛选器样式 */
    .filter-section {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 0.8rem;
    }
    
    /* 内容卡片样式 */
    .content-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
        transition: box-shadow 0.3s ease;
    }
    
    .content-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* 平台标签样式 */
    .platform-tag {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        color: white;
        margin-right: 0.5rem;
    }
    
    /* 情感标签样式 */
    .sentiment-positive { color: #28a745; }
    .sentiment-negative { color: #dc3545; }
    .sentiment-neutral { color: #6c757d; }
    .sentiment-unknown { color: #ffc107; }
    
    /* 侧边栏样式 */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* 按钮样式 */
    .stButton > button {
        border-radius: 8px;
        border: none;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        color: white;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* 选择框样式 */
    .stSelectbox > div > div {
        border-radius: 8px;
    }
    
    /* 多选框样式 */
    .stMultiSelect > div > div {
        border-radius: 8px;
    }
    
    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 响应式设计 */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 1.8rem;
        }
        
        .main-header p {
            font-size: 1rem;
        }
    }
    </style>
    """
    return css

def init_session_state():
    """初始化会话状态"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    
    if 'platform_stats' not in st.session_state:
        st.session_state.platform_stats = {}
    
    if 'sentiment_stats' not in st.session_state:
        st.session_state.sentiment_stats = {}
    
    if 'last_search_time' not in st.session_state:
        st.session_state.last_search_time = 0

def render_header():
    """渲染页面头部"""
    st.markdown("""
    <div class="main-header">
        <h1>📊 媒体数据监控平台</h1>
        <p>多平台社交媒体数据监控与分析系统</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        # st.markdown("## 🎛️ 控制面板")
        
        # 数据库连接状态检查（后台进行，不显示UI）
        # if db_manager.test_connection():
        #     st.success("🟢 数据库连接正常")
        # else:
        #     st.error("🔴 数据库连接异常")
        
        # 获取并显示平台统计
        data_processor = get_data_processor()
        try:
            platform_stats = data_processor.get_platform_statistics()
            st.session_state.platform_stats = platform_stats
            
            if platform_stats:
                st.markdown("### 📈 平台数据统计")
                from web.database.models import PLATFORM_NAMES
                
                # 提取实际的统计数据（排除调试信息）
                actual_stats = {k: v for k, v in platform_stats.items() if not k.startswith('_')}
                debug_info = platform_stats.get('_summary', {})
                platform_status = platform_stats.get('_platform_status', {})
                
                total_count = debug_info.get('total_count', sum(actual_stats.values()))
                successful_platforms = debug_info.get('successful_platforms', [])
                failed_platforms = debug_info.get('failed_platforms', [])
                
                # 显示总数据量
                st.metric("总数据量", f"{total_count:,}", f"成功: {len(successful_platforms)}/{len(actual_stats)}")
                
                # 显示各平台统计
                for platform, count in actual_stats.items():
                    platform_name = PLATFORM_NAMES.get(platform, platform)
                    status = platform_status.get(platform, "未知状态")
                    
                    if count > 0:
                        percentage = (count / total_count * 100) if total_count > 0 else 0
                        # 成功的平台显示绿色指示
                        st.metric(
                            f"🟢 {platform_name}", 
                            f"{count:,}", 
                            f"{percentage:.1f}%"
                        )
                    else:
                        # 失败的平台显示红色指示和错误原因
                        if "表不存在" in status:
                            indicator = "🔴"
                            error_hint = "表不存在"
                        elif "查询失败" in status:
                            indicator = "🟡"  
                            error_hint = "查询失败"
                        else:
                            indicator = "⚪"
                            error_hint = "无数据"
                        
                        st.metric(
                            f"{indicator} {platform_name}",
                            "0",
                            error_hint
                        )
                
                # 添加调试信息展开面板
                if st.checkbox("🔍 显示详细调试信息", value=False, key="show_debug"):
                    st.markdown("#### 🛠️ 调试信息")
                    
                    # 平台状态详情
                    for platform, status in platform_status.items():
                        platform_name = PLATFORM_NAMES.get(platform, platform)
                        if "查询成功" in status:
                            st.success(f"✅ {platform_name}: {status}")
                        else:
                            st.error(f"❌ {platform_name}: {status}")
                    
                    # 总结信息
                    if debug_info:
                        st.json({
                            "统计总结": {
                                "总数据量": debug_info.get('total_count', 0),
                                "成功平台数": len(successful_platforms),
                                "失败平台数": len(failed_platforms),
                                "成功平台": successful_platforms,
                                "失败平台": failed_platforms
                            }
                        })
        except Exception as e:
            logger.error(f"获取平台统计失败: {e}")
            st.error("🔴 平台统计数据获取失败")
            st.exception(e)
        
        # 系统信息
        st.markdown("### ℹ️ 系统信息")
        st.caption(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 缓存控制
        if st.button("🗑️ 清除缓存"):
            data_processor.clear_cache()
            st.success("缓存已清除")
            st.rerun()

def main():
    """主函数"""
    # 页面配置
    st.set_page_config(
        page_title=WEB_CONFIG['app_title'],
        page_icon=WEB_CONFIG['app_icon'],
        layout=WEB_CONFIG['app_layout'],
        initial_sidebar_state=WEB_CONFIG['sidebar_state']
    )
    
    # 加载自定义样式
    st.markdown(load_custom_css(), unsafe_allow_html=True)
    
    # 初始化会话状态
    init_session_state()
    
    # 渲染页面结构
    render_header()
    render_sidebar()
    
    # 主内容区域
    main_container = st.container()
    
    with main_container:
        # 搜索区域
        search_col1, search_col2 = st.columns([3, 1])
        
        with search_col1:
            # 处理历史搜索的临时状态
            if hasattr(st.session_state, 'trigger_search') and st.session_state.trigger_search:
                # 清除触发标志
                st.session_state.trigger_search = False
                # 使用临时关键词
                temp_keywords = st.session_state.get('temp_search_keywords', '')
                if temp_keywords:
                    st.session_state.search_keywords = temp_keywords
                    del st.session_state.temp_search_keywords
            
            # 搜索框
            search_keywords = render_search_box()
        
        with search_col2:
            # 搜索提示
            render_search_tips()
        
        # # 关键词建议
        # render_keyword_suggestions()
        
        # 筛选器区域
        st.markdown("## 🎯 筛选条件")
        
        filter_col1, filter_col2 = st.columns([2, 1])
        
        with filter_col1:
            # 创建筛选条件
            filters = create_search_filters()
            
            # 添加搜索关键词
            if search_keywords:
                filters.keywords = search_keywords
                save_search_to_history(search_keywords)
        
        with filter_col2:
            # 显示当前筛选条件摘要
            render_search_filters_summary(filters)
        
        # 搜索历史
        render_search_history()
        
        # 执行搜索和显示结果
        if filters.platforms or filters.keywords:
            # 验证筛选条件
            data_processor = get_data_processor()
            is_valid, error_msg = data_processor.validate_search_filters(filters)
            
            if not is_valid:
                st.error(f"❌ 筛选条件错误: {error_msg}")
                return
            
            # 显示加载状态
            with st.spinner("🔍 搜索中..."):
                try:
                    # 执行搜索
                    results, total_count, query_time = data_processor.search_with_cache(filters)
                    
                    # 获取情感统计
                    sentiment_stats = data_processor.get_sentiment_statistics(filters)
                    st.session_state.sentiment_stats = sentiment_stats
                    
                    # 显示搜索统计
                    render_search_stats(total_count, query_time, results)
                    
                    # 显示统计概览
                    if results:
                        render_statistics_overview(results)
                    
                    # 显示搜索结果
                    render_content_list(results, total_count, filters.page, filters.page_size)
                    
                except Exception as e:
                    logger.error(f"搜索执行失败: {e}")
                    st.error(f"❌ 搜索失败: {str(e)}")
                    st.info("请检查数据库连接或联系系统管理员")
        
        else:
            # 显示空状态页面
            render_empty_state()
    
    # 页脚信息
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>🚀 MediaCrawler Web监控平台 | 多平台社交媒体数据分析系统</p>
        <p style="font-size: 12px;">仅供学习研究使用，请遵守相关平台使用条款</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        st.error("应用启动失败，请检查配置和数据库连接")
        st.exception(e)