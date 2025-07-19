"""
数据展示组件
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web.database.queries import ContentItem

def format_number(num: int) -> str:
    """格式化数字显示"""
    if num >= 10000:
        return f"{num/10000:.1f}万"
    elif num >= 1000:
        return f"{num/1000:.1f}k"
    return str(num)

def format_time_ago(publish_time: datetime) -> str:
    """格式化时间显示为相对时间"""
    now = datetime.now()
    diff = now - publish_time
    
    if diff.days > 30:
        return publish_time.strftime("%Y-%m-%d")
    elif diff.days > 0:
        return f"{diff.days}天前"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}小时前"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}分钟前"
    else:
        return "刚刚"

def get_sentiment_color(sentiment: str) -> str:
    """获取情感对应的颜色"""
    colors = {
        'positive': '#28a745',  # 绿色
        'negative': '#dc3545',  # 红色
        'neutral': '#6c757d',   # 灰色
        'unknown': '#ffc107'    # 黄色
    }
    return colors.get(sentiment, '#6c757d')

def get_sentiment_emoji(sentiment: str) -> str:
    """获取情感对应的emoji"""
    emojis = {
        'positive': '😊',
        'negative': '😔', 
        'neutral': '😐',
        'unknown': '❓'
    }
    return emojis.get(sentiment, '❓')

def truncate_text(text: str, max_length: int = 100) -> str:
    """截断文本"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def render_content_card(item: ContentItem, index: int):
    """渲染单个内容卡片"""
    
    # 创建卡片容器
    with st.container():
        # 顶部信息栏
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            # 平台标签和标题
            platform_color = {
                'xhs': '#FF2442',
                'douyin': '#000000', 
                'kuaishou': '#FF6600',
                'bilibili': '#FB7299',
                'weibo': '#E6162D',
                'tieba': '#4E6EF2',
                'zhihu': '#0084FF'
            }.get(item.platform, '#6c757d')
            
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <span style="background-color: {platform_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-right: 8px;">
                    {item.platform_name}
                </span>
                <span style="color: #666; font-size: 12px;">
                    {format_time_ago(item.publish_time)}
                </span>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # 情感标签
            sentiment_color = get_sentiment_color(item.sentiment)
            sentiment_emoji = get_sentiment_emoji(item.sentiment)
            sentiment_text = {
                'positive': '正面',
                'negative': '负面',
                'neutral': '中性', 
                'unknown': '未知'
            }.get(item.sentiment, '未知')
            
            st.markdown(f"""
            <div style="text-align: center;">
                <span style="color: {sentiment_color}; font-size: 16px;">{sentiment_emoji}</span>
                <br>
                <span style="color: {sentiment_color}; font-size: 12px;">{sentiment_text}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            # 互动数据
            st.markdown(f"""
            <div style="text-align: center;">
                <span style="font-size: 18px; font-weight: bold; color: #FF6B6B;">❤️</span>
                <br>
                <span style="font-size: 12px; color: #666;">{format_number(item.interaction_count)}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            # 作者信息
            st.markdown(f"""
            <div style="text-align: center;">
                <span style="font-size: 16px;">👤</span>
                <br>
                <span style="font-size: 12px; color: #666;">{truncate_text(item.author_name, 10)}</span>
            </div>
            """, unsafe_allow_html=True)
        
        # 标题
        if item.title:
            st.markdown(f"""
            <h4 style="margin: 10px 0; color: #333; font-size: 16px; line-height: 1.4;">
                {truncate_text(item.title, 80)}
            </h4>
            """, unsafe_allow_html=True)
        
        # 内容摘要
        if item.content:
            st.markdown(f"""
            <p style="color: #666; font-size: 14px; line-height: 1.5; margin: 8px 0;">
                {truncate_text(item.content, 150)}
            </p>
            """, unsafe_allow_html=True)
        
        # 底部操作栏
        bottom_col1, bottom_col2, bottom_col3 = st.columns([2, 1, 1])
        
        with bottom_col1:
            if item.url:
                st.markdown(f"""
                <a href="{item.url}" target="_blank" style="color: #007bff; text-decoration: none; font-size: 12px;">
                    🔗 查看原文
                </a>
                """, unsafe_allow_html=True)
        
        with bottom_col2:
            if st.button("📊 分析", key=f"analyze_{item.id}", use_container_width=True):
                show_content_analysis(item)
        
        with bottom_col3:
            if st.button("⭐ 收藏", key=f"favorite_{item.id}", use_container_width=True):
                st.success("已收藏！")
        
        # 分隔线
        st.markdown("---")

def show_content_analysis(item: ContentItem):
    """显示内容详细分析"""
    with st.expander(f"📊 详细分析 - {truncate_text(item.title, 30)}", expanded=True):
        
        # 基础信息
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**基础信息**")
            st.write(f"平台：{item.platform_name}")
            st.write(f"发布时间：{item.publish_time.strftime('%Y-%m-%d %H:%M')}")
            st.write(f"作者：{item.author_name}")
            st.write(f"互动量：{format_number(item.interaction_count)}")
        
        with col2:
            st.markdown("**情感分析**")
            st.write(f"情感倾向：{get_sentiment_emoji(item.sentiment)} {item.sentiment}")
            if item.sentiment_score > 0:
                st.write(f"情感评分：{item.sentiment_score:.2f}")
            else:
                st.write("情感评分：暂无")
        
        # 完整内容
        if item.content:
            st.markdown("**完整内容**")
            st.text_area("", value=item.content, height=150, disabled=True, key=f"full_content_{item.id}")

def render_content_list(content_items: List[ContentItem], total_count: int, current_page: int, page_size: int):
    """渲染内容列表"""
    
    if not content_items:
        st.warning("😕 没有找到符合条件的内容")
        st.markdown("""
        **建议：**
        - 尝试调整筛选条件
        - 扩大时间范围
        - 使用不同的关键词
        - 选择更多平台
        """)
        return
    
    # 显示结果统计
    st.markdown(f"""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <h3 style="margin: 0; color: #333;">📊 搜索结果</h3>
        <p style="margin: 5px 0 0 0; color: #666;">
            共找到 <strong>{total_count:,}</strong> 条内容，当前显示第 <strong>{current_page}</strong> 页
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 渲染内容卡片
    for i, item in enumerate(content_items):
        render_content_card(item, i)
    
    # 分页控制
    render_pagination(total_count, current_page, page_size)

def render_pagination(total_count: int, current_page: int, page_size: int):
    """渲染分页控制"""
    total_pages = (total_count - 1) // page_size + 1
    
    if total_pages <= 1:
        return
    
    st.markdown("### 📄 翻页")
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("⏮️ 首页", disabled=(current_page == 1), key="first_page"):
            st.session_state.current_page = 1
            st.rerun()
    
    with col2:
        if st.button("⬅️ 上页", disabled=(current_page == 1), key="prev_page"):
            st.session_state.current_page = current_page - 1
            st.rerun()
    
    with col3:
        # 页码选择
        page_options = list(range(1, min(total_pages + 1, 101)))  # 最多显示100页
        selected_page = st.selectbox(
            f"第 {current_page} / {total_pages} 页",
            options=page_options,
            index=current_page - 1,
            key="page_selector"
        )
        
        if selected_page != current_page:
            st.session_state.current_page = selected_page
            st.rerun()
    
    with col4:
        if st.button("➡️ 下页", disabled=(current_page == total_pages), key="next_page"):
            st.session_state.current_page = current_page + 1
            st.rerun()
    
    with col5:
        if st.button("⏭️ 末页", disabled=(current_page == total_pages), key="last_page"):
            st.session_state.current_page = total_pages
            st.rerun()

def render_statistics_overview(content_items: List[ContentItem]):
    """渲染统计概览"""
    if not content_items:
        return
    
    st.markdown("### 📈 数据概览")
    
    # 计算统计数据
    platform_stats = {}
    sentiment_stats = {'positive': 0, 'negative': 0, 'neutral': 0, 'unknown': 0}
    total_interaction = 0
    
    for item in content_items:
        # 平台统计
        platform_stats[item.platform_name] = platform_stats.get(item.platform_name, 0) + 1
        
        # 情感统计
        sentiment_stats[item.sentiment] = sentiment_stats.get(item.sentiment, 0) + 1
        
        # 互动统计
        total_interaction += item.interaction_count
    
    # 显示统计卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总内容数", f"{len(content_items):,}")
    
    with col2:
        st.metric("总互动量", format_number(total_interaction))
    
    with col3:
        if sentiment_stats['positive'] > 0:
            positive_rate = sentiment_stats['positive'] / len(content_items) * 100
            st.metric("正面内容比例", f"{positive_rate:.1f}%")
        else:
            st.metric("正面内容比例", "0%")
    
    with col4:
        avg_interaction = total_interaction / len(content_items) if content_items else 0
        st.metric("平均互动量", format_number(int(avg_interaction)))

def render_empty_state():
    """渲染空状态页面"""
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px; color: #666;">
        <div style="font-size: 64px; margin-bottom: 20px;">🔍</div>
        <h2 style="color: #333; margin-bottom: 10px;">开始您的数据探索之旅</h2>
        <p style="font-size: 16px; margin-bottom: 30px;">
            选择平台、设置时间范围，或输入关键词开始搜索
        </p>
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h4 style="color: #333; margin-bottom: 15px;">💡 使用提示</h4>
            <div style="text-align: left; max-width: 500px; margin: 0 auto;">
                <p>• 在左侧边栏选择要查看的平台</p>
                <p>• 设置时间范围缩小搜索范围</p>
                <p>• 输入关键词进行精确搜索</p>
                <p>• 使用情感筛选查看特定情感倾向的内容</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)