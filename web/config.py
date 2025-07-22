"""
Web应用配置
"""

import os
from typing import Dict, Any

# Web应用配置
WEB_CONFIG = {
    # 应用基础配置
    'app_title': '媒体数据监控平台',
    'app_icon': '📊',
    'app_layout': 'wide',
    'sidebar_state': 'expanded',
    
    # 分页配置
    'default_page_size': 20,
    'max_page_size': 100,
    
    # 缓存配置
    'enable_cache': True,
    'cache_ttl': 300,  # 5分钟
    
    # 性能配置
    'max_results_per_query': 10000,
    'query_timeout': 30,
    
    # 显示配置
    'truncate_title_length': 80,
    'truncate_content_length': 150,
    'truncate_author_length': 10,
    
    # 颜色主题
    'platform_colors': {
        'xhs': '#FF2442',
        'douyin': '#000000',
        'kuaishou': '#FF6600', 
        'bilibili': '#FB7299',
        'weibo': '#E6162D',
        'tieba': '#4E6EF2',
        'zhihu': '#0084FF'
    },
    
    'sentiment_colors': {
        'positive': '#28a745',
        'negative': '#dc3545',
        'neutral': '#6c757d',
        'unknown': '#ffc107'
    }
}

# 环境配置
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# 日志配置
LOGGING_CONFIG = {
    'level': 'DEBUG' if DEBUG else 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'web_app.log' if not DEBUG else None
}

def get_config(key: str, default: Any = None) -> Any:
    """获取配置值"""
    return WEB_CONFIG.get(key, default)