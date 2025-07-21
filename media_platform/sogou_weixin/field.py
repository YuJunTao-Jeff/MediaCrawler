# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


# -*- coding: utf-8 -*-
from enum import Enum


class SearchType(Enum):
    """搜索类型"""
    ARTICLE = "2"  # 文章搜索
    ACCOUNT = "1"  # 公众号搜索


class InterceptType(Enum):
    """网络拦截类型"""
    SEARCH_RESULT = "search_result"  # 搜索结果页面
    ARTICLE_CONTENT = "article_content"  # 文章内容页面


class AntiDetectionLevel(Enum):
    """反检测级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ExtractionStatus(Enum):
    """内容提取状态"""
    PENDING = "pending"  # 待提取
    SUCCESS = "success"  # 提取成功
    FAILED = "failed"    # 提取失败


# 搜狗微信搜索相关的选择器（基于真实页面结构分析）
SOGOU_WEIXIN_SELECTORS = {
    # 搜索结果页面
    'search_results_container': '.news-box .news-list',
    'search_result_item': '.news-list li',
    'article_title': 'h3 a',
    'article_summary': 'p.txt-info', 
    'account_name': '.s-p .all-time-y2',
    'publish_time': '.s-p .s2',
    'article_url': 'h3 a',
    'cover_image': '.img-box img',
    
    # 分页相关
    'pagination_container': '.p-fy',
    'next_page_link': '#sogou_next',
    'page_links': '.p-fy a[id^="sogou_page_"]',
    
    # 验证码相关
    'captcha_container': '.vcode-wrap',
    'captcha_image': '.vcode-img',
    
    # 加载状态
    'loading_indicator': '.loading',
    'no_results': '.no-result',
    'result_count': '.mun',
}


# 搜狗微信URL模板
SOGOU_WEIXIN_URLS = {
    'search_base': 'https://weixin.sogou.com/weixin',
    'article_search': 'https://weixin.sogou.com/weixin?type=2&query={keyword}&page={page}',
    'account_search': 'https://weixin.sogou.com/weixin?type=1&query={keyword}&page={page}',
}