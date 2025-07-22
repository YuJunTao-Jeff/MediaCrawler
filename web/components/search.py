"""
搜索组件
"""

import streamlit as st
from typing import List, Optional
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def render_search_box() -> str:
    """渲染搜索框组件"""
    st.markdown("### 🔎 内容搜索")
    
    # 处理待添加的关键词
    initial_value = ""
    if 'pending_keyword' in st.session_state:
        current_keywords = st.session_state.get('search_keywords', '')
        pending_keyword = st.session_state.pending_keyword
        if pending_keyword not in current_keywords:
            initial_value = f"{current_keywords} {pending_keyword}".strip()
        else:
            initial_value = current_keywords
        # 清除pending_keyword
        del st.session_state.pending_keyword
    else:
        # 设置默认搜索关键词
        default_keywords = "澳鹏科技"
        initial_value = st.session_state.get('search_keywords', default_keywords)
    
    # 搜索框
    col1, col2 = st.columns([4, 1])
    
    with col1:
        keywords = st.text_input(
            "搜索关键词",
            value=initial_value,
            placeholder="搜索关键词 (默认: 澳鹏科技)",
            key="search_keywords",
            label_visibility="collapsed",
            help="💡 系统已预设澳鹏科技相关搜索，可直接点击搜索或修改关键词"
        )
    
    with col2:
        search_button = st.button("搜索", key="search_button", use_container_width=True)
    
    # 搜索选项
    search_type = st.radio(
        "搜索类型",
        options=["smart", "exact", "fuzzy"],
        format_func=lambda x: {
            "smart": "智能搜索",
            "exact": "精确匹配", 
            "fuzzy": "模糊匹配"
        }[x],
        horizontal=True,
        key="search_type"
    )
    
    # 搜索范围
    search_scope = st.multiselect(
        "搜索范围",
        options=["title", "content", "author"],
        default=["title", "content"],
        format_func=lambda x: {
            "title": "标题",
            "content": "内容",
            "author": "作者"
        }[x],
        key="search_scope"
    )
    
    return keywords if search_button or keywords else ""

def render_keyword_suggestions() -> List[str]:
    """渲染关键词建议"""
    
    # 热门关键词（优先显示澳鹏相关）
    hot_keywords = [
        "澳鹏科技", "澳鹏", "appen", "澳鹏数据", 
        "人工智能", "数据标注", "机器学习", "AI训练"
    ]
    
    st.caption("💡 热门关键词")
    
    # 以标签形式显示关键词
    keyword_cols = st.columns(4)
    selected_keywords = []
    
    # 使用session_state来处理关键词点击，避免直接修改widget的session_state
    for i, keyword in enumerate(hot_keywords):
        with keyword_cols[i % 4]:
            if st.button(f"#{keyword}", key=f"keyword_{i}", use_container_width=True):
                # 将选中的关键词保存到session_state中，在下次渲染时处理
                st.session_state.pending_keyword = keyword
                st.rerun()
    
    return selected_keywords

def render_search_history():
    """渲染搜索历史"""
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    
    if st.session_state.search_history:
        with st.expander("📝 搜索历史", expanded=False):
            for i, history_item in enumerate(reversed(st.session_state.search_history[-10:])):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.caption(f"🕐 {history_item['time']} - {history_item['keywords']}")
                with col2:
                    if st.button("重新搜索", key=f"history_{i}", use_container_width=True):
                        # 使用临时状态来避免直接修改search_keywords
                        st.session_state.temp_search_keywords = history_item['keywords']
                        st.session_state.trigger_search = True
                        st.rerun()

def render_search_stats(total_results: int, search_time: float, content_items=None):
    """渲染搜索统计信息"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("搜索结果", f"{total_results:,} 条")
    
    with col2:
        st.metric("搜索用时", f"{search_time:.2f} 秒")
    
    with col3:
        if total_results > 0 and content_items:
            # 计算实际的平均相关度
            relevance_scores = []
            for item in content_items:
                if hasattr(item, '_model_instance') and item._model_instance:
                    analysis_info = item._model_instance.get_analysis_info()
                    if analysis_info and 'relevance_score' in analysis_info:
                        try:
                            score = float(analysis_info['relevance_score'])
                            relevance_scores.append(score)
                        except:
                            pass
            
            if relevance_scores:
                avg_relevance = sum(relevance_scores) / len(relevance_scores)
                st.metric("平均相关度", f"{avg_relevance:.1%}")
            else:
                st.metric("平均相关度", "暂无")
        else:
            st.metric("平均相关度", "-")

def render_search_tips():
    """渲染搜索提示"""
    with st.expander("💡 搜索提示", expanded=False):
        st.markdown("""
        ### 搜索技巧
        
        **基础搜索：**
        - 直接输入关键词，如：`澳鹏科技`
        - 多个关键词用空格分隔，如：`澳鹏 AI 数据`
        
        **高级搜索：**
        - **精确匹配**：完全匹配输入的关键词
        - **模糊匹配**：包含关键词的相关内容
        - **智能搜索**：AI增强的智能匹配（推荐）
        
        **搜索范围：**
        - **标题**：仅在标题中搜索
        - **内容**：在正文内容中搜索
        - **作者**：在作者名称中搜索
        
        **使用示例：**
        - 搜索公司相关：`澳鹏科技 OR 澳鹏数据`
        - 搜索技术话题：`人工智能 数据标注`
        - 搜索特定作者：选择"作者"范围，输入作者名
        """)

def save_search_to_history(keywords: str):
    """保存搜索到历史记录"""
    if not keywords.strip():
        return
    
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    
    from datetime import datetime
    
    # 避免重复的搜索记录
    existing_keywords = [item['keywords'] for item in st.session_state.search_history]
    if keywords not in existing_keywords:
        st.session_state.search_history.append({
            'keywords': keywords,
            'time': datetime.now().strftime('%H:%M:%S'),
            'timestamp': datetime.now()
        })
        
        # 只保留最近20条搜索记录
        if len(st.session_state.search_history) > 20:
            st.session_state.search_history = st.session_state.search_history[-20:]

def render_search_export():
    """渲染搜索结果导出功能"""
    st.subheader("📤 导出搜索结果")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("导出为Excel", key="export_excel", use_container_width=True):
            st.info("Excel导出功能开发中...")
    
    with col2:
        if st.button("导出为CSV", key="export_csv", use_container_width=True):
            st.info("CSV导出功能开发中...")
    
    with col3:
        if st.button("生成报告", key="export_report", use_container_width=True):
            st.info("报告生成功能开发中...")

def render_search_filters_summary(filters):
    """渲染当前搜索筛选条件摘要"""
    if not filters:
        return
    
    with st.expander("📋 当前筛选条件", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if filters.platforms:
                from web.database.models import PLATFORM_NAMES
                platform_names = [PLATFORM_NAMES.get(p, p) for p in filters.platforms]
                st.caption(f"**平台：** {', '.join(platform_names)}")
            else:
                st.caption("**平台：** 全部")
            
            if filters.keywords:
                st.caption(f"**关键词：** {filters.keywords}")
            
            if filters.sentiment != 'all':
                sentiment_map = {
                    'positive': '正面', 'negative': '负面', 
                    'neutral': '中性', 'unknown': '未知'
                }
                st.caption(f"**情感：** {sentiment_map.get(filters.sentiment, filters.sentiment)}")
        
        with col2:
            st.caption(f"**时间：** {filters.start_time.strftime('%Y-%m-%d')} 至 {filters.end_time.strftime('%Y-%m-%d')}")
            sort_by_dict = {'time': '时间', 'interaction': '互动量'}
            sort_order_dict = {'desc': '降序', 'asc': '升序'}
            st.caption(f"**排序：** {sort_by_dict[filters.sort_by]} {sort_order_dict[filters.sort_order]}")
            st.caption(f"**每页：** {filters.page_size} 条")
        
        # 清除筛选条件按钮
        if st.button("🗑️ 清除所有筛选条件", key="clear_filters"):
            # 重置会话状态
            for key in ['search_keywords', 'platform_multiselect', 'sentiment_select', 'current_page']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()