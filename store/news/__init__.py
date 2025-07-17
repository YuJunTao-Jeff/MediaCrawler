# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


from typing import Dict, List
from store.news.news_store_impl import NewsStoreImpl
from tools import utils


# 全局新闻存储实例
news_store_instance = NewsStoreImpl()


async def update_news_article(article_data: Dict) -> None:
    """
    更新新闻文章
    
    Args:
        article_data: 文章数据字典
    """
    if not article_data:
        return
    
    utils.logger.info(f"[store.news.update_news_article] 更新文章: {article_data.get('title', 'Unknown')}")
    await news_store_instance.update_news_article(article_data)


async def get_articles_by_keyword(keyword: str, limit: int = 100) -> List:
    """
    根据关键词获取文章
    
    Args:
        keyword: 搜索关键词
        limit: 返回数量限制
        
    Returns:
        文章列表
    """
    utils.logger.info(f"[store.news.get_articles_by_keyword] 查询关键词: {keyword}")
    return await news_store_instance.get_articles_by_keyword(keyword, limit)


async def get_article_by_id(article_id: str):
    """
    根据文章ID获取文章
    
    Args:
        article_id: 文章ID
        
    Returns:
        文章对象或None
    """
    utils.logger.info(f"[store.news.get_article_by_id] 查询文章ID: {article_id}")
    return await news_store_instance.get_article_by_id(article_id)


async def get_article_count() -> int:
    """
    获取文章总数
    
    Returns:
        文章总数
    """
    return await news_store_instance.get_article_count()


async def get_latest_articles(limit: int = 50) -> List:
    """
    获取最新文章
    
    Args:
        limit: 返回数量限制
        
    Returns:
        最新文章列表
    """
    utils.logger.info(f"[store.news.get_latest_articles] 获取最新文章，限制: {limit}")
    return await news_store_instance.get_latest_articles(limit)