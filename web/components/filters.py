"""
筛选组件
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Tuple
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web.database.models import PLATFORM_NAMES
from web.database.queries import SearchFilters

def render_platform_filter() -> List[str]:
    """渲染平台筛选组件"""
    st.subheader("📱 平台筛选")
    
    # 获取平台统计（如果有的话）
    platform_stats = st.session_state.get('platform_stats', {})
    
    # 平台选项
    platform_options = []
    for platform_key, platform_name in PLATFORM_NAMES.items():
        count = platform_stats.get(platform_key, 0)
        if count > 0:
            platform_options.append(f"{platform_name}({count})")
        else:
            platform_options.append(platform_name)
    
    # 全选选项
    all_selected = st.checkbox("全选", key="platform_all")
    
    if all_selected:
        selected_platforms = st.multiselect(
            "选择平台",
            options=platform_options,
            default=platform_options,
            key="platform_multiselect"
        )
    else:
        selected_platforms = st.multiselect(
            "选择平台",
            options=platform_options,
            key="platform_multiselect"
        )
    
    # 转换回平台key
    selected_keys = []
    for selected in selected_platforms:
        for key, name in PLATFORM_NAMES.items():
            if selected.startswith(name):
                selected_keys.append(key)
                break
    
    return selected_keys

def render_time_filter() -> Tuple[datetime, datetime]:
    """渲染时间筛选组件"""
    st.subheader("⏰ 时间筛选")
    
    # 快捷时间选项
    time_range = st.selectbox(
        "时间范围",
        options=["自定义", "今天", "昨天", "最近3天", "最近7天", "最近30天"],
        index=4,  # 默认选择最近7天
        key="time_range_select"
    )
    
    now = datetime.now()
    
    if time_range == "今天":
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now
    elif time_range == "昨天":
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif time_range == "最近3天":
        start_time = now - timedelta(days=3)
        end_time = now
    elif time_range == "最近7天":
        start_time = now - timedelta(days=7)
        end_time = now
    elif time_range == "最近30天":
        start_time = now - timedelta(days=30)
        end_time = now
    else:  # 自定义
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "开始日期",
                value=now.date() - timedelta(days=7),
                key="start_date"
            )
            start_time_input = st.time_input(
                "开始时间",
                value=datetime.min.time(),
                key="start_time"
            )
        
        with col2:
            end_date = st.date_input(
                "结束日期",
                value=now.date(),
                key="end_date"
            )
            end_time_input = st.time_input(
                "结束时间",
                value=now.time(),
                key="end_time"
            )
        
        start_time = datetime.combine(start_date, start_time_input)
        end_time = datetime.combine(end_date, end_time_input)
    
    # 显示选择的时间范围
    st.caption(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}")
    
    return start_time, end_time

def render_sentiment_filter() -> str:
    """渲染情感筛选组件"""
    st.subheader("😊 情感筛选")
    
    # 获取情感分布统计（如果有的话）
    sentiment_stats = st.session_state.get('sentiment_stats', {})
    
    sentiment_options = {
        'all': '全部',
        'positive': '正面',
        'negative': '负面', 
        'neutral': '中性',
        'unknown': '未知'
    }
    
    # 构建选项显示
    display_options = []
    for key, name in sentiment_options.items():
        count = sentiment_stats.get(key, 0) if key != 'all' else sum(sentiment_stats.values())
        if count > 0:
            display_options.append(f"{name}({count})")
        else:
            display_options.append(name)
    
    selected_sentiment = st.selectbox(
        "情感类型",
        options=list(range(len(display_options))),
        format_func=lambda x: display_options[x],
        index=0,  # 默认选择全部
        key="sentiment_select"
    )
    
    # 返回对应的key
    sentiment_keys = list(sentiment_options.keys())
    return sentiment_keys[selected_sentiment]

def render_search_options() -> Tuple[str, str]:
    """渲染搜索选项"""
    st.subheader("🔍 排序和显示")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sort_by = st.selectbox(
            "排序方式",
            options=["time", "interaction"],
            format_func=lambda x: {"time": "时间", "interaction": "互动量"}[x],
            key="sort_by_select"
        )
    
    with col2:
        sort_order = st.selectbox(
            "排序顺序",
            options=["desc", "asc"],
            format_func=lambda x: {"desc": "降序", "asc": "升序"}[x],
            key="sort_order_select"
        )
    
    # 每页显示数量
    page_size = st.selectbox(
        "每页显示",
        options=[10, 20, 50, 100],
        index=1,  # 默认20
        key="page_size_select"
    )
    
    return sort_by, sort_order, page_size

def render_advanced_filters():
    """渲染高级筛选选项"""
    with st.expander("🔧 高级筛选", expanded=False):
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 互动量范围
            min_interaction = st.number_input(
                "最小互动量",
                min_value=0,
                value=0,
                key="min_interaction"
            )
        
        with col2:
            max_interaction = st.number_input(
                "最大互动量",
                min_value=0,
                value=100000,
                key="max_interaction"
            )
        
        # 作者筛选
        author_filter = st.text_input(
            "作者名称包含",
            placeholder="输入作者名称关键词",
            key="author_filter"
        )
        
        # 内容长度筛选
        content_length = st.selectbox(
            "内容长度",
            options=["all", "short", "medium", "long"],
            format_func=lambda x: {
                "all": "全部",
                "short": "短内容(<100字)",
                "medium": "中等内容(100-500字)",
                "long": "长内容(>500字)"
            }[x],
            key="content_length_select"
        )
        
        return {
            'min_interaction': min_interaction,
            'max_interaction': max_interaction,
            'author_filter': author_filter,
            'content_length': content_length
        }

def create_search_filters() -> SearchFilters:
    """创建搜索筛选条件对象"""
    
    # 获取筛选条件
    platforms = render_platform_filter()
    start_time, end_time = render_time_filter()
    sentiment = render_sentiment_filter()
    sort_by, sort_order, page_size = render_search_options()
    
    # 获取当前页码
    current_page = st.session_state.get('current_page', 1)
    
    return SearchFilters(
        platforms=platforms,
        start_time=start_time,
        end_time=end_time,
        sentiment=sentiment,
        page=current_page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )