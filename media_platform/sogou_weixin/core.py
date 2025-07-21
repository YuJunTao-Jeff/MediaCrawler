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
import asyncio
import random
from asyncio import Task
from typing import Dict, List, Optional

from playwright.async_api import BrowserContext, BrowserType, Page, Playwright, async_playwright

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import sogou_weixin as sogou_weixin_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var
from model.m_weixin import WeixinArticle

from .client import SogouWeixinClient  
from .exception import DataFetchError, BrowserAutomationError, CaptchaDetectionError
from .field import SearchType, AntiDetectionLevel
from .login import SogouWeixinLogin


class SogouWeixinCrawler(AbstractCrawler):
    """搜狗微信爬虫（浏览器自动化+DOM解析）"""
    
    context_page: Page
    sogou_weixin_client: SogouWeixinClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]
    
    def __init__(self) -> None:
        super().__init__()
        self.index_url = "https://weixin.sogou.com"
        self.user_agent = config.UA if config.UA else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.cdp_manager = None
        
        # 搜狗微信配置
        self.sogou_weixin_config = {
            'enabled': getattr(config, 'SOGOU_WEIXIN_ENABLED', True),
            'search_type': getattr(config, 'SOGOU_WEIXIN_SEARCH_TYPE', 'article'),
            'max_pages': getattr(config, 'SOGOU_WEIXIN_MAX_PAGES', 10),
            'extract_original_content': getattr(config, 'SOGOU_WEIXIN_EXTRACT_ORIGINAL_CONTENT', True),
            'anti_detection_level': AntiDetectionLevel.MEDIUM,
        }
    
    async def start(self) -> None:
        """启动爬虫"""
        playwright_proxy_format, httpx_proxy_format = None, None
        
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)
            
        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[SogouWeixinCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright, playwright_proxy_format, self.user_agent,
                    headless=getattr(config, 'CDP_HEADLESS', config.HEADLESS)
                )
            else:
                utils.logger.info("[SogouWeixinCrawler] 使用标准模式启动浏览器")
                # 启动浏览器
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium, playwright_proxy_format, self.user_agent, 
                    headless=config.HEADLESS
                )
                
            # 创建页面
            self.context_page = await self.browser_context.new_page()
            await self.context_page.set_viewport_size({"width": 1920, "height": 1080})
            
            # 设置页面超时
            self.context_page.set_default_timeout(30000)
            
            # 初始化登录
            login_obj = SogouWeixinLogin(login_type=config.LOGIN_TYPE)
            await login_obj.begin(self.context_page)
            
            # 创建客户端
            cookie_dict = await self.browser_context.cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookie_dict}
            
            self.sogou_weixin_client = SogouWeixinClient(
                timeout=30,
                proxies=httpx_proxy_format,
                playwright_page=self.context_page,
                cookie_dict=cookie_dict
            )
            
            # 初始化断点续爬
            if config.ENABLE_RESUME_CRAWL:
                await self.init_resume_crawl(platform="sogou_weixin")
                utils.logger.info("[SogouWeixinCrawler] 断点续爬功能已启用")
            
            # 根据爬虫类型执行不同逻辑
            crawler_type_var.set(config.CRAWLER_TYPE)
            
            try:
                if config.CRAWLER_TYPE == "search":
                    await self._search_articles()
                elif config.CRAWLER_TYPE == "account":
                    await self._search_accounts()
                else:
                    utils.logger.error(f"[SogouWeixinCrawler] 不支持的爬虫类型: {config.CRAWLER_TYPE}")
                    
            except CaptchaDetectionError as e:
                utils.logger.error(f"[SogouWeixinCrawler] 遇到验证码，请人工处理: {e}")
                # 暂停等待用户处理验证码
                utils.logger.info("[SogouWeixinCrawler] 请在浏览器中手动处理验证码，然后按回车继续...")
                input("按回车继续...")
                
            except Exception as e:
                utils.logger.error(f"[SogouWeixinCrawler] 爬虫执行失败: {e}")
                raise
            
            finally:
                if self.cdp_manager:
                    await self.cdp_manager.close()
    
    async def _search_articles(self) -> None:
        """搜索文章模式"""
        utils.logger.info("[SogouWeixinCrawler] 开始搜索文章模式")
        
        # 获取搜索关键词
        keywords = config.KEYWORDS.split(",") if config.KEYWORDS else []
        if not keywords:
            utils.logger.error("[SogouWeixinCrawler] 未配置搜索关键词")
            return
        
        utils.logger.info(f"[SogouWeixinCrawler] 搜索关键词: {keywords}")
        
        for keyword in keywords:
            keyword = keyword.strip()
            if not keyword:
                continue
                
            try:
                source_keyword_var.set(keyword)
                utils.logger.info(f"[SogouWeixinCrawler] 开始搜索关键词: {keyword}")
                
                # 检查断点续爬
                if config.ENABLE_RESUME_CRAWL and self.progress_manager:
                    try:
                        if hasattr(self.progress_manager, 'is_keyword_completed'):
                            if await self.progress_manager.is_keyword_completed(keyword):
                                utils.logger.info(f"[SogouWeixinCrawler] 跳过已完成的关键词: {keyword}")
                                continue
                    except Exception as e:
                        utils.logger.warning(f"[SogouWeixinCrawler] 断点续爬检查失败: {e}")
                
                # 执行搜索
                articles = await self.sogou_weixin_client.search_articles(
                    keyword=keyword,
                    max_pages=self.sogou_weixin_config['max_pages']
                )
                
                utils.logger.info(f"[SogouWeixinCrawler] 关键词 '{keyword}' 搜索到 {len(articles)} 篇文章")
                
                # 处理文章数据
                await self._process_articles(articles, keyword)
                
                # 更新断点续爬进度
                if config.ENABLE_RESUME_CRAWL:
                    await self.update_crawl_progress(keyword, len(articles))
                
                # 关键词间延迟
                if len(keywords) > 1:
                    delay = random.uniform(10, 20)
                    utils.logger.info(f"[SogouWeixinCrawler] 关键词间延迟 {delay:.2f} 秒")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                utils.logger.error(f"[SogouWeixinCrawler] 搜索关键词 '{keyword}' 失败: {e}")
                continue
        
        utils.logger.info("[SogouWeixinCrawler] 文章搜索完成")
    
    async def _search_accounts(self) -> None:
        """搜索公众号模式"""
        utils.logger.info("[SogouWeixinCrawler] 开始搜索公众号模式")
        
        # 获取搜索关键词
        keywords = config.KEYWORDS.split(",") if config.KEYWORDS else []
        if not keywords:
            utils.logger.error("[SogouWeixinCrawler] 未配置搜索关键词")
            return
        
        for keyword in keywords:
            keyword = keyword.strip()
            if not keyword:
                continue
                
            try:
                utils.logger.info(f"[SogouWeixinCrawler] 开始搜索公众号: {keyword}")
                
                # 执行公众号搜索
                accounts = await self.sogou_weixin_client.search_accounts(
                    keyword=keyword,
                    max_pages=5
                )
                
                utils.logger.info(f"[SogouWeixinCrawler] 关键词 '{keyword}' 搜索到 {len(accounts)} 个公众号")
                
                # TODO: 处理公众号数据存储
                
            except Exception as e:
                utils.logger.error(f"[SogouWeixinCrawler] 搜索公众号 '{keyword}' 失败: {e}")
                continue
        
        utils.logger.info("[SogouWeixinCrawler] 公众号搜索完成")
    
    async def _process_articles(self, articles: List[WeixinArticle], keyword: str) -> None:
        """处理文章数据"""
        if not articles:
            return
        
        utils.logger.info(f"[SogouWeixinCrawler] 开始处理 {len(articles)} 篇文章")
        
        # 批量存储文章基本信息
        processed_count = 0
        for article in articles:
            try:
                # 提取文章正文内容（如果启用）
                if self.sogou_weixin_config['extract_original_content'] and article.original_url:
                    content = await self.sogou_weixin_client.extract_article_content(article.original_url)
                    if content:
                        article.content = content
                
                # 存储到数据库
                await sogou_weixin_store.update_weixin_article(article.model_dump())
                processed_count += 1
                
                # 批量处理时的延迟
                if processed_count % 5 == 0:
                    await asyncio.sleep(random.uniform(2, 5))
                    
            except Exception as e:
                utils.logger.warning(f"[SogouWeixinCrawler] 处理文章失败: {e}")
                continue
        
        utils.logger.info(f"[SogouWeixinCrawler] 成功处理 {processed_count}/{len(articles)} 篇文章")
    
    async def launch_browser_with_cdp(self, 
                                    playwright: Playwright,
                                    proxy_format: Optional[Dict] = None,
                                    user_agent: str = "",
                                    headless: bool = False) -> BrowserContext:
        """使用CDP模式启动浏览器"""
        try:
            self.cdp_manager = CDPBrowserManager()
            # 使用正确的方法启动并连接浏览器
            context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=proxy_format,
                user_agent=user_agent,
                headless=headless
            )
            
            utils.logger.info("[SogouWeixinCrawler] CDP模式浏览器启动成功")
            return context
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinCrawler] CDP模式浏览器启动失败: {e}")
            raise BrowserAutomationError(f"CDP浏览器启动失败: {e}")
    
    async def launch_browser(self,
                           browser_type: BrowserType,
                           proxy_format: Optional[Dict] = None,
                           user_agent: str = "",
                           headless: bool = False) -> BrowserContext:
        """启动标准浏览器"""
        try:
            launch_options = {
                "headless": headless,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions-http-throttling",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-gpu",
                    "--disable-gpu-sandbox",
                    "--disable-software-rasterizer",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
            }
            
            if proxy_format:
                launch_options["proxy"] = proxy_format
                
            browser = await browser_type.launch(**launch_options)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent or self.user_agent,
                ignore_https_errors=True,
            )
            
            utils.logger.info("[SogouWeixinCrawler] 标准模式浏览器启动成功")
            return context
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinCrawler] 标准模式浏览器启动失败: {e}")
            raise BrowserAutomationError(f"标准浏览器启动失败: {e}")
    
    # ==================== 抽象方法实现 ====================
    
    def extract_item_id(self, content_item: Dict) -> Optional[str]:
        """从内容项中提取唯一ID"""
        return content_item.get('article_id')
    
    def extract_item_timestamp(self, content_item: Dict) -> Optional[int]:
        """从内容项中提取时间戳"""
        return content_item.get('publish_timestamp')
    
    async def get_page_content(self, keyword: str, page: int) -> List[Dict]:
        """获取指定关键词和页码的内容列表"""
        try:
            # 使用搜狗微信客户端进行搜索
            articles = await self.sogou_weixin_client.search_articles(
                keyword=keyword,
                max_pages=1,  # 只获取单页
                start_page=page
            )
            
            # 转换为字典列表
            return [article.model_dump() for article in articles]
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinCrawler] 获取页面内容失败: {e}")
            return []
    
    async def store_content(self, content_item: Dict) -> None:
        """存储单个内容项"""
        try:
            await sogou_weixin_store.update_weixin_article(content_item)
            utils.logger.debug(f"[SogouWeixinCrawler] 文章存储成功: {content_item.get('title', 'Unknown')}")
        except Exception as e:
            utils.logger.error(f"[SogouWeixinCrawler] 文章存储失败: {e}")
            raise
    
    async def should_skip_keyword(self, keyword: str) -> bool:
        """判断是否应该跳过该关键词"""
        if not self.progress_manager:
            return False
        return await self.progress_manager.is_keyword_completed(keyword)