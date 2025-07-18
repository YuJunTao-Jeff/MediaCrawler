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
import os
import random
import time
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import BrowserContext, BrowserType, Page, Playwright, async_playwright
from tenacity import RetryError

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import tieba as tieba_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import TiebaSimulationClient
from .exception import DataFetchError, BrowserAutomationError
from .field import SearchSortType, SearchNoteType, AntiDetectionLevel
from .help import NetworkInterceptor, UserBehaviorSimulator, AntiDetectionHelper
from .login import TiebaSimulationLogin


class TiebaSimulationCrawler(AbstractCrawler):
    """贴吧模拟爬虫（浏览器自动化+网络拦截）"""
    
    context_page: Page
    tieba_client: TiebaSimulationClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]
    
    def __init__(self) -> None:
        super().__init__()
        self.index_url = "https://tieba.baidu.com"
        self.user_agent = config.UA if config.UA else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.cdp_manager = None
        
        # 模拟相关配置
        self.simulation_config = {
            'enable_user_behavior': getattr(config, 'TIEBA_SIMULATION_USER_BEHAVIOR', True),
            'enable_anti_detection': getattr(config, 'TIEBA_SIMULATION_ANTI_DETECTION', True),
            'anti_detection_level': getattr(config, 'TIEBA_SIMULATION_ANTI_DETECTION_LEVEL', 'medium'),
            'behavior_delay_range': getattr(config, 'TIEBA_SIMULATION_BEHAVIOR_DELAY', (1.0, 3.0)),
            'scroll_count_range': getattr(config, 'TIEBA_SIMULATION_SCROLL_COUNT', (2, 5)),
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
                utils.logger.info("[TiebaSimulationCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright, playwright_proxy_format, self.user_agent,
                    headless=getattr(config, 'CDP_HEADLESS', config.HEADLESS)
                )
            else:
                utils.logger.info("[TiebaSimulationCrawler] 使用标准模式启动浏览器")
                # 启动浏览器
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=config.HEADLESS
                )
            
            # 创建页面
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)
            
            # 初始化客户端
            cookie_dict = await self.browser_context.cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookie_dict}
            
            self.tieba_client = TiebaSimulationClient(
                timeout=30,
                proxies=httpx_proxy_format,
                playwright_page=self.context_page,
                cookie_dict=cookie_dict
            )
            
            # 设置反检测
            if self.simulation_config['enable_anti_detection']:
                anti_detection = AntiDetectionHelper(self.context_page)
                level_map = {
                    'low': AntiDetectionLevel.LOW,
                    'medium': AntiDetectionLevel.MEDIUM,
                    'high': AntiDetectionLevel.HIGH,
                    'extreme': AntiDetectionLevel.EXTREME
                }
                level = level_map.get(self.simulation_config['anti_detection_level'], AntiDetectionLevel.MEDIUM)
                await anti_detection.setup_stealth_mode(level)
            
            # 登录处理
            await self.login()
            
            # 启动断点续爬
            if config.ENABLE_RESUME_CRAWL:
                await self.init_resume_crawl("tieba_simulation", config.RESUME_TASK_ID)
            
            # 根据爬取类型执行对应功能
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                await self.get_specified_posts()
            elif config.CRAWLER_TYPE == "creator":
                await self.get_creator_posts()
            else:
                utils.logger.error("[TiebaSimulationCrawler] 不支持的爬取类型")
                
            # 清理断点续爬
            if config.ENABLE_RESUME_CRAWL:
                await self.cleanup_crawl_progress()
                
            await self.close()
    
    async def search(self) -> None:
        """搜索模式"""
        utils.logger.info("[TiebaSimulationCrawler] 开始搜索模式")
        
        if config.ENABLE_RESUME_CRAWL:
            await self.search_with_resume()
        else:
            # 普通搜索模式
            for keyword in config.KEYWORDS.split(","):
                source_keyword_var.set(keyword)
                utils.logger.info(f"[TiebaSimulationCrawler] 当前搜索关键词: {keyword}")
                
                # 模拟搜索行为
                await self._simulate_search_behavior(keyword)
                
                page = 1
                max_pages = getattr(config, 'PAGE_LIMIT', 20)
                
                while page <= max_pages:
                    try:
                        utils.logger.info(f"[TiebaSimulationCrawler] 搜索关键词: {keyword}, 页码: {page}")
                        
                        posts_result = await self.tieba_client.get_posts_by_keyword(
                            keyword=keyword,
                            page=page,
                            sort=SearchSortType.TIME_DESC,
                            note_type=SearchNoteType.ALL
                        )
                        
                        posts = posts_result.get('posts', [])
                        if not posts:
                            utils.logger.info(f"[TiebaSimulationCrawler] 关键词 {keyword} 第 {page} 页无数据")
                            break
                        
                        utils.logger.info(f"[TiebaSimulationCrawler] 获取到 {len(posts)} 个帖子")
                        
                        # 保存搜索结果
                        for post in posts:
                            await self._save_post_data(post)
                        
                        # 模拟用户行为延迟
                        if self.simulation_config['enable_user_behavior']:
                            delay = random.uniform(*self.simulation_config['behavior_delay_range'])
                            await asyncio.sleep(delay)
                        
                        page += 1
                        
                    except Exception as e:
                        utils.logger.error(f"[TiebaSimulationCrawler] 搜索失败 {keyword} 第 {page} 页: {e}")
                        break
    
    async def get_specified_posts(self) -> None:
        """获取指定帖子详情"""
        utils.logger.info("[TiebaSimulationCrawler] 开始获取指定帖子详情")
        
        post_urls = getattr(config, 'TIEBA_SPECIFIED_ID_LIST', [])
        if not post_urls:
            utils.logger.warning("[TiebaSimulationCrawler] 未配置指定帖子ID列表")
            return
        
        for post_id in post_urls:
            try:
                utils.logger.info(f"[TiebaSimulationCrawler] 获取指定帖子: {post_id}")
                
                # 获取帖子详情和评论
                await self._get_post_detail_and_comments(post_id)
                
                # 模拟用户行为延迟
                if self.simulation_config['enable_user_behavior']:
                    delay = random.uniform(*self.simulation_config['behavior_delay_range'])
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                utils.logger.error(f"[TiebaSimulationCrawler] 获取指定帖子失败 {post_id}: {e}")
                continue
    
    async def get_creator_posts(self) -> None:
        """获取创作者帖子"""
        utils.logger.info("[TiebaSimulationCrawler] 开始获取创作者帖子")
        
        creator_ids = getattr(config, 'TIEBA_CREATOR_URL_LIST', [])
        if not creator_ids:
            utils.logger.warning("[TiebaSimulationCrawler] 未配置创作者ID列表")
            return
        
        for creator_id in creator_ids:
            try:
                utils.logger.info(f"[TiebaSimulationCrawler] 获取创作者信息: {creator_id}")
                
                # 获取创作者信息
                creator_info = await self.tieba_client.get_user_info(creator_id)
                if creator_info:
                    await self._save_creator_data(creator_info)
                
                # 模拟用户行为延迟
                if self.simulation_config['enable_user_behavior']:
                    delay = random.uniform(*self.simulation_config['behavior_delay_range'])
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                utils.logger.error(f"[TiebaSimulationCrawler] 获取创作者信息失败 {creator_id}: {e}")
                continue
    
    async def get_page_content(self, keyword: str, page: int) -> List[Dict]:
        """
        获取指定页面内容（断点续爬使用）
        """
        try:
            posts_result = await self.tieba_client.get_posts_by_keyword(
                keyword=keyword,
                page=page,
                sort=SearchSortType.TIME_DESC,
                note_type=SearchNoteType.ALL
            )
            return posts_result.get('posts', [])
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationCrawler] 获取页面内容失败 keyword={keyword}, page={page}: {e}")
            return []
    
    async def store_content(self, content: Dict) -> None:
        """存储内容"""
        try:
            await self._save_post_data(content)
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationCrawler] 存储内容失败: {e}")
            raise e
    
    def extract_item_id(self, content: Dict) -> str:
        """提取内容唯一ID"""
        return content.get("post_id", "")
    
    def extract_item_timestamp(self, content: Dict) -> int:
        """提取内容时间戳"""
        return content.get("publish_time", 0)
    
    async def login(self) -> None:
        """登录处理"""
        utils.logger.info("[TiebaSimulationCrawler] 开始登录流程")
        
        login_obj = TiebaSimulationLogin(
            login_type=config.LOGIN_TYPE,
            browser_context=self.browser_context,
            context_page=self.context_page,
            login_phone=getattr(config, 'TIEBA_LOGIN_PHONE', ''),
            cookie_str=getattr(config, 'TIEBA_COOKIE_STR', '')
        )
        
        await login_obj.begin()
        
        # 更新Cookie
        cookie_dict = await self.browser_context.cookies()
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookie_dict}
        
        # 重新初始化客户端
        self.tieba_client = TiebaSimulationClient(
            timeout=30,
            proxies=None,  # 代理信息保持不变
            playwright_page=self.context_page,
            cookie_dict=cookie_dict
        )
    
    async def launch_browser(self,
                           chromium: BrowserType,
                           playwright_proxy: Optional[Dict],
                           user_agent: Optional[str],
                           headless: bool = True) -> BrowserContext:
        """启动浏览器"""
        utils.logger.info("[TiebaSimulationCrawler] 启动浏览器")
        
        browser_args = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox"
        ]
        
        # 随机化浏览器指纹
        if self.simulation_config['enable_anti_detection']:
            browser_args.extend([
                "--disable-extensions-except",
                "--disable-plugins-discovery"
            ])
        
        browser = await chromium.launch(
            headless=headless,
            args=browser_args,
            proxy=playwright_proxy
        )
        
        browser_context = await browser.new_context(
            viewport={"width": random.randint(1200, 1920), "height": random.randint(800, 1080)},
            user_agent=user_agent,
            ignore_https_errors=True,
        )
        
        return browser_context
    
    async def launch_browser_with_cdp(self, playwright: Playwright, playwright_proxy: Optional[Dict],
                                     user_agent: Optional[str], headless: bool = True) -> BrowserContext:
        """
        使用CDP模式启动浏览器
        """
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless
            )

            # 显示浏览器信息
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[TiebaSimulationCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[TiebaSimulationCrawler] CDP模式启动失败: {e}")
            # 回退到标准模式
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)
    
    async def close(self) -> None:
        """关闭爬虫"""
        utils.logger.info("[TiebaSimulationCrawler] 关闭模拟爬虫")
        
        # 如果使用CDP模式，需要特殊处理
        if hasattr(self, 'cdp_manager') and self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            if self.context_page:
                await self.context_page.close()
            
            if self.browser_context:
                await self.browser_context.close()
        
        utils.logger.info("[TiebaSimulationCrawler] 浏览器上下文已关闭")
    
    async def _simulate_search_behavior(self, keyword: str) -> None:
        """模拟搜索行为"""
        if not self.simulation_config['enable_user_behavior']:
            return
        
        try:
            behavior_sim = UserBehaviorSimulator(self.context_page)
            
            # 模拟在首页停留
            await behavior_sim.simulate_reading_behavior(1, 3)
            
            # 模拟鼠标移动到搜索框
            search_box_selector = "input[name='kw'], .search-input, #search-input"
            await behavior_sim.simulate_mouse_movement(search_box_selector)
            
            # 模拟输入关键词（字符间有延迟）
            try:
                await self.context_page.fill(search_box_selector, "")  # 先清空
                for char in keyword:
                    await self.context_page.type(search_box_selector, char, delay=random.randint(50, 200))
            except:
                pass
            
            # 短暂停顿后执行搜索
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            utils.logger.warning(f"[TiebaSimulationCrawler] 模拟搜索行为失败: {e}")
    
    async def _get_post_detail_and_comments(self, post_id: str) -> None:
        """获取帖子详情和评论"""
        try:
            # 获取帖子详情
            post_detail = await self.tieba_client.get_post_detail(post_id)
            if post_detail:
                await self._save_post_data(post_detail)
            
            # 获取评论
            if config.ENABLE_GET_COMMENTS:
                page = 1
                max_comments = getattr(config, 'CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES', 20)
                comment_count = 0
                
                while comment_count < max_comments:
                    comments_result = await self.tieba_client.get_post_comments(post_id, page)
                    
                    if not comments_result.get('comments'):
                        break
                    
                    comments = comments_result['comments']
                    for comment in comments:
                        await self._save_comment_data(comment)
                        comment_count += 1
                        
                        if comment_count >= max_comments:
                            break
                    
                    if not comments_result.get('has_more', False):
                        break
                    
                    page += 1
                    
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationCrawler] 获取帖子详情和评论失败 {post_id}: {e}")
    
    async def _save_post_data(self, post_data: Dict) -> None:
        """保存帖子数据"""
        try:
            # 这里需要根据实际的存储模型来调整
            # 假设tieba_store有对应的保存方法
            await tieba_store.update_tieba_note(post_data)
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationCrawler] 保存帖子数据失败: {e}")
    
    async def _save_comment_data(self, comment_data: Dict) -> None:
        """保存评论数据"""
        try:
            # 这里需要根据实际的存储模型来调整
            await tieba_store.update_tieba_note_comment(comment_data)
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationCrawler] 保存评论数据失败: {e}")
    
    async def _save_creator_data(self, creator_data: Dict) -> None:
        """保存创作者数据"""
        try:
            # 这里需要根据实际的存储模型来调整
            await tieba_store.save_creator(creator_data)
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationCrawler] 保存创作者数据失败: {e}")