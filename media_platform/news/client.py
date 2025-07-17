# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import asyncio
import sys
import os
from typing import Dict, List, Optional

# 添加dataharvest到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'libs'))

from dataharvest.searcher import TavilySearcher
from dataharvest.searcher.sky_searcher import SkySearcher
from media_platform.news.extractor import NewsArticleExtractor
from tools import utils
import config


class NewsSearchClient:
    """新闻搜索客户端，集成多个搜索引擎"""
    
    def __init__(self):
        self.searchers = self._init_searchers()
        self.extractor = NewsArticleExtractor()
    
    def _init_searchers(self) -> Dict:
        """初始化搜索引擎"""
        searchers = {}
        
        # 初始化Tavily搜索
        if hasattr(config, 'TAVILY_API_KEY') and config.TAVILY_API_KEY:
            try:
                searchers['tavily'] = TavilySearcher(config.TAVILY_API_KEY)
                utils.logger.info("[NewsSearchClient] Tavily搜索引擎初始化成功")
            except Exception as e:
                utils.logger.error(f"[NewsSearchClient] Tavily搜索引擎初始化失败: {e}")
        
        # 初始化天工搜索
        if hasattr(config, 'TIANGONG_API_KEY') and config.TIANGONG_API_KEY:
            try:
                searchers['tiangong'] = SkySearcher(config.TIANGONG_API_KEY)
                utils.logger.info("[NewsSearchClient] 天工搜索引擎初始化成功")
            except Exception as e:
                utils.logger.error(f"[NewsSearchClient] 天工搜索引擎初始化失败: {e}")
        
        if not searchers:
            utils.logger.warning("[NewsSearchClient] 没有可用的搜索引擎")
        
        return searchers
    
    async def search_news(self, keyword: str, page: int = 1) -> List[Dict]:
        """
        搜索新闻并提取内容
        
        Args:
            keyword: 搜索关键词
            page: 页码（暂未使用，预留）
            
        Returns:
            提取的新闻文章列表
        """
        results = []
        
        for engine_name, searcher in self.searchers.items():
            try:
                utils.logger.info(f"[NewsSearchClient] 使用{engine_name}搜索: {keyword}")
                
                # 1. 搜索获取结果列表
                max_results = getattr(config, 'NEWS_MAX_RESULTS_PER_KEYWORD', 10)
                search_result = searcher.search(keyword, max_results=max_results)
                
                utils.logger.info(f"[NewsSearchClient] {engine_name}搜索到 {len(search_result.items)} 个结果")
                
                # 2. 并发提取文章内容
                tasks = []
                for item in search_result.items:
                    task = self._extract_article_with_search_info(item, keyword, engine_name)
                    tasks.append(task)
                
                # 控制并发数量
                max_concurrent = getattr(config, 'NEWS_MAX_CONCURRENT_EXTRACTIONS', 10)
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def limited_extract(task):
                    async with semaphore:
                        return await task
                
                limited_tasks = [limited_extract(task) for task in tasks]
                articles = await asyncio.gather(*limited_tasks, return_exceptions=True)
                
                # 3. 过滤成功的结果
                success_count = 0
                for article in articles:
                    if isinstance(article, dict) and article is not None:
                        results.append(article)
                        success_count += 1
                    elif isinstance(article, Exception):
                        utils.logger.error(f"[NewsSearchClient] 文章提取异常: {article}")
                
                utils.logger.info(f"[NewsSearchClient] {engine_name}成功提取 {success_count} 篇文章")
                
            except Exception as e:
                utils.logger.error(f"[NewsSearchClient] 搜索引擎 {engine_name} 出错: {e}")
                continue
        
        utils.logger.info(f"[NewsSearchClient] 关键词 '{keyword}' 共提取 {len(results)} 篇文章")
        return results
    
    async def _extract_article_with_search_info(self, search_item, keyword: str, engine_name: str) -> Optional[Dict]:
        """
        提取文章并添加搜索信息
        
        Args:
            search_item: 搜索结果项
            keyword: 搜索关键词
            engine_name: 搜索引擎名称
            
        Returns:
            包含搜索信息的文章数据
        """
        try:
            # 提取文章内容
            article = await self.extractor.extract_article(search_item.url)
            
            if article:
                # 添加搜索相关信息
                article['search_keyword'] = keyword
                article['search_engine'] = engine_name
                article['search_title'] = search_item.title
                article['search_description'] = search_item.description
                article['search_score'] = search_item.score
                
                return article
            else:
                return None
                
        except Exception as e:
            utils.logger.error(f"[NewsSearchClient] 提取文章失败 {search_item.url}: {e}")
            return None
    
    def get_available_engines(self) -> List[str]:
        """获取可用的搜索引擎列表"""
        return list(self.searchers.keys())
    
    def is_engine_available(self, engine_name: str) -> bool:
        """检查搜索引擎是否可用"""
        return engine_name in self.searchers