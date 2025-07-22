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

def truncate_text(text: str, max_length: int = 200) -> str:
    """截断文本"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def render_content_card(item: ContentItem, index: int):
    """渲染单个内容卡片 - 简洁风格"""
    
    with st.container():
        # 标题行 - 占满整行
        if item.title:
            st.markdown(f"""
            <h3 style="margin: 0; color: #1a73e8; font-size: 16px; font-weight: 600; line-height: 1.4;">
                <a href="{item.url}" target="_blank" style="color: #1a73e8; text-decoration: none;">
                    {truncate_text(item.title, 120)}
                </a>
            </h3>
            """, unsafe_allow_html=True)
        
        # 内容摘要 - 增加更多预览文字
        if item.content:
            st.markdown(f"""
            <p style="color: #5f6368; font-size: 14px; line-height: 1.5; margin: 8px 0 12px 0;">
                {truncate_text(item.content, 350)}
            </p>
            """, unsafe_allow_html=True)
        
        # 底部元信息行 - 所有次要信息放在一行，适当使用emoji增强可读性
        metadata_parts = []
        
        # 发布日期
        metadata_parts.append(f"🕒 {item.publish_time.strftime('%Y-%m-%d %H:%M')}")
        
        # 来源平台  
        metadata_parts.append(f"📱 {item.platform_name}")
        
        # 作者
        if item.author_name:
            metadata_parts.append(f"👤 {truncate_text(item.author_name, 15)}")
        
        # 情感分析 - 使用简单的emoji
        sentiment_emoji = get_sentiment_emoji(item.sentiment)
        sentiment_text = {
            'positive': '正面', 'negative': '负面', 
            'neutral': '中性', 'unknown': '未知'
        }.get(item.sentiment, '未知')
        metadata_parts.append(f"{sentiment_emoji} {sentiment_text}")
        
        # 互动数量
        if item.interaction_count > 0:
            metadata_parts.append(f"💬 {format_number(item.interaction_count)}")
        
        # AI相关性评分（如果有）
        if hasattr(item, '_model_instance') and item._model_instance:
            analysis_info = item._model_instance.get_analysis_info()
            if analysis_info and 'relevance_score' in analysis_info:
                try:
                    relevance = float(analysis_info['relevance_score'])
                    metadata_parts.append(f"🎯 {relevance:.0%}")
                except:
                    pass
        
        # 渲染元信息行
        metadata_text = " | ".join(metadata_parts)
        st.markdown(f"""
        <div style="color: #70757a; font-size: 12px; margin: 8px 0; line-height: 1.3;">
            {metadata_text}
        </div>
        """, unsafe_allow_html=True)
        
        # AI分析信息展示（如果有analysis_info数据）
        if hasattr(item, '_model_instance') and item._model_instance:
            analysis_info = item._model_instance.get_analysis_info()
            if analysis_info:
                analysis_lines = []
                
                # 内容摘要
                if 'summary' in analysis_info and analysis_info['summary']:
                    analysis_lines.append(f"• 摘要: {analysis_info['summary']}")
                
                # 关键词
                if 'keywords' in analysis_info and analysis_info['keywords']:
                    keywords_text = ", ".join(analysis_info['keywords']) if isinstance(analysis_info['keywords'], list) else str(analysis_info['keywords'])
                    analysis_lines.append(f"• 关键词: {keywords_text}")
                
                # 内容分类
                if 'category' in analysis_info and analysis_info['category']:
                    analysis_lines.append(f"• 分类: {analysis_info['category']}")
                
                # 展开按钮和AI分析信息
                if analysis_lines:
                    # 简单的展开/收起按钮
                    expand_key = f"expand_analysis_{item.id}"
                    is_expanded = st.session_state.get(expand_key, False)
                    
                    if st.button(f"{'↑收起' if is_expanded else '↓展开'} AI分析", key=expand_key, use_container_width=False):
                        st.session_state[expand_key] = not is_expanded
                        st.rerun()
                    
                    # 根据展开状态显示分析信息
                    if is_expanded:
                        analysis_text = "<br>".join(analysis_lines)
                        st.markdown(f"""
                        <div style="color: #70757a; font-size: 12px; margin: 8px 0; line-height: 1.4; background-color: #f8f9fa; padding: 8px; border-radius: 4px;">
                            {analysis_text}
                        </div>
                        """, unsafe_allow_html=True)
        
        # 简单分隔线
        st.markdown('<hr style="margin: 16px 0; border: 0; border-top: 1px solid #e8eaed;">', unsafe_allow_html=True)

def show_content_analysis(item: ContentItem):
    """显示内容详细分析"""
    # 使用container替代expander，获得更宽的展示空间
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 12px; margin: 20px 0;">
        <h3 style="color: white; margin: 0; text-align: center;">📊 内容分析 - {truncate_text(item.title, 50)}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        # 基础信息区域 - 紧凑展示
        st.markdown("#### 📋 基础信息")
        info_col1, info_col2, info_col3, info_col4 = st.columns(4)
        
        with info_col1:
            st.metric("平台", item.platform_name)
        with info_col2:
            st.metric("作者", truncate_text(item.author_name, 15))
        with info_col3:
            st.metric("互动量", format_number(item.interaction_count))
        with info_col4:
            st.metric("发布时间", item.publish_time.strftime('%Y-%m-%d'))
        
        st.markdown("---")
        
        # 情感分析区域 - 简化布局
        st.markdown("#### 😊 情感分析")
        sentiment_col1, sentiment_col2 = st.columns([1, 2])
        
        with sentiment_col1:
            sentiment_color = get_sentiment_color(item.sentiment)
            sentiment_emoji = get_sentiment_emoji(item.sentiment)
            st.markdown(f"""
            <div style="text-align: center; padding: 12px; background-color: {sentiment_color}20; border-radius: 8px; border: 2px solid {sentiment_color}40;">
                <div style="font-size: 24px; margin-bottom: 5px;">{sentiment_emoji}</div>
                <div style="color: {sentiment_color}; font-weight: bold; font-size: 14px;">{item.sentiment}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with sentiment_col2:
            if item.sentiment_score > 0:
                st.metric("情感评分", f"{item.sentiment_score:.2f}", help="AI分析得出的情感倾向评分")
            else:
                st.metric("情感评分", "暂无数据")
        
        # AI分析信息展示
        analysis_info = None
        if hasattr(item, '_model_instance') and item._model_instance:
            analysis_info = item._model_instance.get_analysis_info()
        
        if analysis_info:
            st.markdown("---")
            st.markdown("#### 🤖 AI分析结果")
            
            # 内容摘要 - 全宽显示
            if 'summary' in analysis_info and analysis_info['summary']:
                st.markdown("**📝 内容摘要**")
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 4px solid #28a745; margin-bottom: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                    <div style="font-size: 13px; line-height: 1.5; color: #333;">{analysis_info['summary']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 分析标签 - 3列布局
            tags_col1, tags_col2, tags_col3 = st.columns(3)
            
            with tags_col1:
                if 'keywords' in analysis_info and analysis_info['keywords']:
                    st.markdown("**🏷️ 关键词**")
                    keywords_text = ", ".join(analysis_info['keywords']) if isinstance(analysis_info['keywords'], list) else str(analysis_info['keywords'])
                    st.markdown(f"""
                    <div style="background-color: #e3f2fd; padding: 10px; border-radius: 6px; font-size: 12px; min-height: 50px; border: 1px solid #bbdefb; line-height: 1.4; overflow-wrap: break-word;">
                        {keywords_text}
                    </div>
                    """, unsafe_allow_html=True)
            
            with tags_col2:
                if 'category' in analysis_info and analysis_info['category']:
                    st.markdown("**📂 内容分类**")
                    st.markdown(f"""
                    <div style="background-color: #f3e5f5; padding: 10px; border-radius: 6px; font-size: 12px; min-height: 50px; text-align: center; display: flex; align-items: center; justify-content: center; border: 1px solid #e1bee7;">
                        <strong style="color: #6a1b9a;">{analysis_info['category']}</strong>
                    </div>
                    """, unsafe_allow_html=True)
            
            with tags_col3:
                if 'relevance_score' in analysis_info:
                    relevance = float(analysis_info['relevance_score'])
                    st.markdown("**🎯 相关性评分**")
                    # 创建相关性可视化
                    color = "#28a745" if relevance >= 0.7 else "#ffc107" if relevance >= 0.4 else "#dc3545"
                    bg_color = "#d4edda" if relevance >= 0.7 else "#fff3cd" if relevance >= 0.4 else "#f8d7da"
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; padding: 10px; border-radius: 6px; font-size: 12px; min-height: 50px; text-align: center; display: flex; align-items: center; justify-content: center; border: 1px solid {color}40;">
                        <div style="color: {color}; font-weight: bold; font-size: 16px;">{relevance:.1%}</div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("📋 该内容暂无AI分析数据")
    
    # 添加关闭按钮
    if st.button("❌ 关闭分析", key=f"close_analysis_{item.id}", use_container_width=True):
        st.rerun()

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