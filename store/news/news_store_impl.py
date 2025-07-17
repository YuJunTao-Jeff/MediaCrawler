# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import json
import time
from typing import List, Optional, Dict
from datetime import datetime

from model.m_news import NewsArticle, NewsSearchResult, NewsSearchTask
from store.news.news_store_sql import NewsStoreSql
from tools import utils
from var import media_crawler_db_var


class NewsStoreImpl:
    """新闻存储实现"""
    
    def __init__(self):
        self.mysql_db_var = media_crawler_db_var
    
    async def update_news_article(self, article_data: Dict) -> None:
        """
        更新新闻文章
        
        Args:
            article_data: 文章数据字典
        """
        try:
            current_ts = int(time.time() * 1000)
            
            # 处理JSON字段
            keywords_json = json.dumps(article_data.get('keywords'), ensure_ascii=False) if article_data.get('keywords') else None
            authors_json = json.dumps(article_data.get('authors'), ensure_ascii=False) if article_data.get('authors') else None
            metadata_json = json.dumps(article_data.get('metadata'), ensure_ascii=False) if article_data.get('metadata') else None
            
            # 处理发布时间
            publish_date = article_data.get('publish_date')
            if publish_date and not isinstance(publish_date, datetime):
                publish_date = None
            
            # 执行SQL
            await self.mysql_db_var.get().execute(
                NewsStoreSql.UPSERT_NEWS_ARTICLE,
                article_data.get('article_id') or '',
                article_data.get('source_url') or '',
                article_data.get('title') or '未知标题',
                article_data.get('content') or '',
                article_data.get('summary') or '',
                keywords_json or '[]',
                authors_json or '[]',
                publish_date,
                article_data.get('source_domain') or '',
                article_data.get('source_site') or '',
                article_data.get('top_image') or '',
                article_data.get('word_count') or 0,
                article_data.get('language', 'zh'),
                metadata_json or '{}',
                current_ts,
                current_ts
            )
            
            # 如果有搜索信息，同时保存搜索结果
            if article_data.get('search_keyword') and article_data.get('search_engine'):
                await self.save_search_result_data(article_data)
            
            utils.logger.info(f"[NewsStoreImpl] 成功存储文章: {article_data.get('title', 'Unknown')}")
            
        except Exception as e:
            utils.logger.error(f"[NewsStoreImpl] 存储文章失败: {e}")
            raise
    
    async def save_search_result_data(self, article_data: Dict) -> None:
        """
        保存搜索结果数据
        
        Args:
            article_data: 包含搜索信息的文章数据
        """
        try:
            current_ts = int(time.time() * 1000)
            
            await self.mysql_db_var.get().execute(
                NewsStoreSql.INSERT_SEARCH_RESULT,
                article_data.get('search_keyword') or '',
                article_data.get('search_engine') or '',
                article_data.get('search_title', article_data.get('title')) or '未知标题',
                article_data.get('source_url') or '',
                article_data.get('search_score') or 0.0,
                article_data.get('search_description') or '',
                article_data.get('article_id') or '',
                current_ts,
                current_ts
            )
            
        except Exception as e:
            utils.logger.error(f"[NewsStoreImpl] 保存搜索结果失败: {e}")
            # 搜索结果保存失败不抛出异常，不影响文章保存
    
    async def get_articles_by_keyword(self, keyword: str, limit: int = 100) -> List[NewsArticle]:
        """
        根据关键词获取文章
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            文章列表
        """
        try:
            results = await self.mysql_db_var.get().query(
                NewsStoreSql.SELECT_ARTICLES_BY_KEYWORD,
                keyword, limit
            )
            
            articles = []
            for row in results:
                article = self._row_to_article(row)
                if article:
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            utils.logger.error(f"[NewsStoreImpl] 根据关键词获取文章失败: {e}")
            return []
    
    async def get_article_by_id(self, article_id: str) -> Optional[NewsArticle]:
        """
        根据文章ID获取文章
        
        Args:
            article_id: 文章ID
            
        Returns:
            文章对象或None
        """
        try:
            results = await self.mysql_db_var.get().query(
                NewsStoreSql.SELECT_ARTICLE_BY_ID,
                article_id
            )
            
            if results:
                return self._row_to_article(results[0])
            return None
            
        except Exception as e:
            utils.logger.error(f"[NewsStoreImpl] 根据ID获取文章失败: {e}")
            return None
    
    async def get_article_count(self) -> int:
        """
        获取文章总数
        
        Returns:
            文章总数
        """
        try:
            results = await self.mysql_db_var.get().query(
                NewsStoreSql.SELECT_ARTICLE_COUNT
            )
            return results[0]['count'] if results else 0
            
        except Exception as e:
            utils.logger.error(f"[NewsStoreImpl] 获取文章总数失败: {e}")
            return 0
    
    async def get_latest_articles(self, limit: int = 50) -> List[NewsArticle]:
        """
        获取最新文章
        
        Args:
            limit: 返回数量限制
            
        Returns:
            最新文章列表
        """
        try:
            results = await self.mysql_db_var.get().query(
                NewsStoreSql.SELECT_LATEST_ARTICLES,
                limit
            )
            
            articles = []
            for row in results:
                article = self._row_to_article(row)
                if article:
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            utils.logger.error(f"[NewsStoreImpl] 获取最新文章失败: {e}")
            return []
    
    def _row_to_article(self, row: Dict) -> Optional[NewsArticle]:
        """
        将数据库行转换为NewsArticle对象
        
        Args:
            row: 数据库行数据
            
        Returns:
            NewsArticle对象或None
        """
        try:
            # 解析JSON字段
            keywords = json.loads(row.get('keywords', '[]')) if row.get('keywords') else []
            authors = json.loads(row.get('authors', '[]')) if row.get('authors') else []
            metadata = json.loads(row.get('metadata', '{}')) if row.get('metadata') else {}
            
            article = NewsArticle(
                article_id=row.get('article_id', ''),
                source_url=row.get('source_url', ''),
                title=row.get('title', '未知标题'),
                content=row.get('content'),
                summary=row.get('summary'),
                keywords=keywords,
                authors=authors,
                publish_date=row.get('publish_date'),
                source_domain=row.get('source_domain'),
                source_site=row.get('source_site'),
                top_image=row.get('top_image'),
                word_count=row.get('word_count'),
                language=row.get('language', 'zh'),
                metadata=metadata
            )
            
            return article
            
        except Exception as e:
            utils.logger.error(f"[NewsStoreImpl] 转换文章数据失败: {e}")
            return None