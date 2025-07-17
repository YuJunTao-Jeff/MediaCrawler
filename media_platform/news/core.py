# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


from typing import Dict, List, Optional
from playwright.async_api import BrowserContext, BrowserType

import config
from base.base_crawler import AbstractCrawler
from media_platform.news.client import NewsSearchClient
from store import news as news_store
from tools import utils
from var import crawler_type_var


class NewsCrawler(AbstractCrawler):
    """新闻爬虫主类，集成DataHarvest和newspaper3k"""
    
    def __init__(self):
        super().__init__()
        self.news_client = NewsSearchClient()
        self.platform_name = "news"
    
    async def start(self):
        """启动新闻爬虫"""
        utils.logger.info("[NewsCrawler] 开始启动新闻爬虫")
        
        try:
            # 检查搜索引擎是否可用
            available_engines = self.news_client.get_available_engines()
            if not available_engines:
                utils.logger.error("[NewsCrawler] 没有可用的搜索引擎，请检查API密钥配置")
                return
            
            utils.logger.info(f"[NewsCrawler] 可用搜索引擎: {available_engines}")
            
            # 初始化断点续爬
            if config.ENABLE_RESUME_CRAWL:
                await self.init_resume_crawl(platform="news")
                utils.logger.info("[NewsCrawler] 断点续爬功能已启用")
            
            # 根据爬虫类型执行不同逻辑
            crawler_type_var.set(config.CRAWLER_TYPE)
            
            if config.CRAWLER_TYPE == "search":
                await self.search_news()
            elif config.CRAWLER_TYPE == "detail":
                await self.extract_articles()
            else:
                utils.logger.error(f"[NewsCrawler] 不支持的爬虫类型: {config.CRAWLER_TYPE}")
                
        except Exception as e:
            utils.logger.error(f"[NewsCrawler] 启动失败: {e}")
            raise e
        finally:
            if config.ENABLE_RESUME_CRAWL:
                await self.cleanup_crawl_progress()
            utils.logger.info("[NewsCrawler] 新闻爬虫已结束")
    
    async def search_news(self):
        """搜索新闻"""
        utils.logger.info("[NewsCrawler] 开始搜索新闻")
        
        # 支持断点续爬的搜索
        if config.ENABLE_RESUME_CRAWL:
            await self.search_with_resume()
        else:
            await self.search()
    
    async def search(self):
        """传统搜索方法"""
        utils.logger.info("[NewsCrawler] 使用传统搜索模式")
        
        keywords = config.KEYWORDS.split(',')
        for keyword in keywords:
            keyword = keyword.strip()
            if not keyword:
                continue
                
            try:
                utils.logger.info(f"[NewsCrawler] 搜索关键词: {keyword}")
                
                # 搜索并提取文章
                articles = await self.news_client.search_news(keyword)
                
                # 存储文章
                for article in articles:
                    await self.store_content(article)
                    
                utils.logger.info(f"[NewsCrawler] 关键词 '{keyword}' 处理完成，共 {len(articles)} 篇文章")
                
            except Exception as e:
                utils.logger.error(f"[NewsCrawler] 搜索关键词 '{keyword}' 失败: {e}")
                continue
    
    async def extract_articles(self):
        """提取指定文章详情"""
        utils.logger.info("[NewsCrawler] 开始提取指定文章详情")
        
        # 这里可以实现从配置或数据库读取URL列表进行提取
        # 暂时不实现，预留接口
        utils.logger.warning("[NewsCrawler] 详情提取功能尚未实现")
    
    async def get_page_content(self, keyword: str, page: int) -> List[Dict]:
        """
        获取指定页面的搜索结果
        
        Args:
            keyword: 搜索关键词
            page: 页码
            
        Returns:
            搜索到的文章列表
        """
        try:
            # 调用搜索客户端获取内容
            return await self.news_client.search_news(keyword, page)
        except Exception as e:
            utils.logger.error(f"[NewsCrawler] 获取页面内容失败 keyword={keyword}, page={page}: {e}")
            return []
    
    async def store_content(self, content: Dict) -> None:
        """
        存储新闻内容
        
        Args:
            content: 新闻内容字典
        """
        try:
            await news_store.update_news_article(content)
        except Exception as e:
            utils.logger.error(f"[NewsCrawler] 存储内容失败: {e}")
            raise e
    
    def extract_item_id(self, content: Dict) -> str:
        """从内容中提取唯一ID"""
        return content.get("article_id", "")
    
    def extract_item_timestamp(self, content: Dict) -> int:
        """从内容中提取时间戳"""
        publish_date = content.get("publish_date")
        if publish_date:
            return int(publish_date.timestamp())
        return 0
    
    async def launch_browser(self, chromium: BrowserType, playwright_proxy: Optional[Dict], 
                           user_agent: Optional[str], headless: bool = True) -> BrowserContext:
        """
        启动浏览器 (新闻爬虫不需要浏览器，返回None)
        
        Args:
            chromium: Chromium浏览器类型
            playwright_proxy: 代理配置
            user_agent: 用户代理
            headless: 无头模式
            
        Returns:
            None (新闻爬虫不使用浏览器)
        """
        # 新闻爬虫不需要浏览器，直接返回None
        utils.logger.info("[NewsCrawler] 新闻爬虫不需要浏览器，跳过浏览器启动")
        return None
    
    async def close(self):
        """关闭爬虫"""
        utils.logger.info("[NewsCrawler] 关闭新闻爬虫")
        # 新闻爬虫没有浏览器需要关闭
        pass