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
from store import xhs as xhs_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import XHSSimulationClient
from .exception import DataFetchError, BrowserAutomationError
from .field import SearchSortType, SearchNoteType, AntiDetectionLevel
from .help import NetworkInterceptor, UserBehaviorSimulator, AntiDetectionHelper
from .login import XHSSimulationLogin


class XHSSimulationCrawler(AbstractCrawler):
    """小红书模拟爬虫（浏览器自动化+网络拦截）"""
    
    context_page: Page
    xhs_client: XHSSimulationClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]
    
    def __init__(self) -> None:
        super().__init__()
        self.index_url = "https://www.xiaohongshu.com"
        self.user_agent = config.UA if config.UA else "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        self.cdp_manager = None
        
        # 模拟相关配置
        self.simulation_config = {
            'enable_user_behavior': getattr(config, 'XHS_SIMULATION_USER_BEHAVIOR', True),
            'enable_anti_detection': getattr(config, 'XHS_SIMULATION_ANTI_DETECTION', True),
            'anti_detection_level': getattr(config, 'XHS_SIMULATION_ANTI_DETECTION_LEVEL', 'medium'),
            'behavior_delay_range': getattr(config, 'XHS_SIMULATION_BEHAVIOR_DELAY', (1.0, 3.0)),
            'scroll_count_range': getattr(config, 'XHS_SIMULATION_SCROLL_COUNT', (2, 5)),
        }
    
    async def start(self) -> None:
        """启动爬虫"""
        playwright_proxy_format, httpx_proxy_format = None, None
        
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)
            
        async with async_playwright() as playwright:
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
            
            self.xhs_client = XHSSimulationClient(
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
                await self.init_resume_crawl(platform="xhs_simulation")
            
            # 根据爬虫类型执行相应逻辑
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                await self.get_specified_notes()
            elif config.CRAWLER_TYPE == "creator":
                await self.get_creator_notes()
            else:
                pass
            
            utils.logger.info("[XHSSimulationCrawler] 模拟爬虫执行完成")
    
    async def search(self) -> None:
        """搜索模式"""
        utils.logger.info("[XHSSimulationCrawler] 开始搜索模式")
        
        if config.ENABLE_RESUME_CRAWL:
            await self.search_with_resume()
        else:
            await self.traditional_search()
    
    async def traditional_search(self) -> None:
        """传统搜索模式"""
        utils.logger.info("[XHSSimulationCrawler] 使用传统搜索模式")
        
        keywords = config.KEYWORDS.split(',')
        for keyword in keywords:
            keyword = keyword.strip()
            if not keyword:
                continue
                
            utils.logger.info(f"[XHSSimulationCrawler] 开始搜索关键词: {keyword}")
            source_keyword_var.set(keyword)
            
            # 模拟用户搜索行为
            await self._simulate_search_behavior(keyword)
            
            # 获取搜索结果
            page = 1
            max_pages = getattr(config, 'PAGE_LIMIT', 20)
            
            while page <= max_pages:
                try:
                    utils.logger.info(f"[XHSSimulationCrawler] 搜索 {keyword} 第 {page} 页")
                    
                    notes_result = await self.xhs_client.get_note_by_keyword(
                        keyword=keyword,
                        page=page,
                        sort=SearchSortType.GENERAL,
                        note_type=SearchNoteType.ALL
                    )
                    
                    if not notes_result.get('notes'):
                        utils.logger.info(f"[XHSSimulationCrawler] 关键词 {keyword} 第 {page} 页无数据，停止搜索")
                        break
                    
                    # 处理搜索结果
                    for note_info in notes_result['notes']:
                        try:
                            # 存储笔记信息
                            await xhs_store.update_xhs_note(note_info)
                            
                            # 获取详情（可选）
                            if config.ENABLE_GET_COMMENTS:
                                await self._get_note_detail_and_comments(note_info['note_id'])
                                
                        except Exception as e:
                            utils.logger.error(f"[XHSSimulationCrawler] 处理笔记失败 {note_info.get('note_id', '')}: {e}")
                            continue
                    
                    # 模拟用户翻页行为
                    if self.simulation_config['enable_user_behavior']:
                        behavior_sim = UserBehaviorSimulator(self.context_page)
                        await behavior_sim.simulate_reading_behavior(2, 4)
                    
                    if not notes_result.get('has_more', False):
                        utils.logger.info(f"[XHSSimulationCrawler] 关键词 {keyword} 已搜索完毕")
                        break
                        
                    page += 1
                    
                except Exception as e:
                    utils.logger.error(f"[XHSSimulationCrawler] 搜索第 {page} 页失败: {e}")
                    break
    
    async def get_specified_notes(self) -> None:
        """获取指定笔记详情"""
        utils.logger.info("[XHSSimulationCrawler] 开始获取指定笔记详情")
        
        note_urls = getattr(config, 'XHS_SPECIFIED_NOTE_URL_LIST', [])
        if not note_urls:
            utils.logger.warning("[XHSSimulationCrawler] 未配置指定笔记URL列表")
            return
        
        for note_url in note_urls:
            try:
                # 从URL中解析note_id
                note_id = self._extract_note_id_from_url(note_url)
                if not note_id:
                    utils.logger.warning(f"[XHSSimulationCrawler] 无法从URL中提取note_id: {note_url}")
                    continue
                
                utils.logger.info(f"[XHSSimulationCrawler] 获取指定笔记: {note_id}")
                
                # 获取笔记详情和评论
                await self._get_note_detail_and_comments(note_id)
                
                # 模拟用户行为延迟
                if self.simulation_config['enable_user_behavior']:
                    delay = random.uniform(*self.simulation_config['behavior_delay_range'])
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                utils.logger.error(f"[XHSSimulationCrawler] 获取指定笔记失败 {note_url}: {e}")
                continue
    
    async def get_creator_notes(self) -> None:
        """获取创作者笔记"""
        utils.logger.info("[XHSSimulationCrawler] 开始获取创作者笔记")
        
        creator_ids = getattr(config, 'XHS_CREATOR_ID_LIST', [])
        if not creator_ids:
            utils.logger.warning("[XHSSimulationCrawler] 未配置创作者ID列表")
            return
        
        for creator_id in creator_ids:
            try:
                utils.logger.info(f"[XHSSimulationCrawler] 获取创作者信息: {creator_id}")
                
                # 获取创作者信息
                creator_info = await self.xhs_client.get_creator_info(creator_id)
                if creator_info:
                    await xhs_store.update_xhs_creator(creator_info)
                
                # 模拟用户行为延迟
                if self.simulation_config['enable_user_behavior']:
                    delay = random.uniform(*self.simulation_config['behavior_delay_range'])
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                utils.logger.error(f"[XHSSimulationCrawler] 获取创作者信息失败 {creator_id}: {e}")
                continue
    
    async def get_page_content(self, keyword: str, page: int) -> List[Dict]:
        """
        获取指定页面内容（断点续爬使用）
        """
        try:
            notes_result = await self.xhs_client.get_note_by_keyword(
                keyword=keyword,
                page=page,
                sort=SearchSortType.GENERAL,
                note_type=SearchNoteType.ALL
            )
            return notes_result.get('notes', [])
        except Exception as e:
            utils.logger.error(f"[XHSSimulationCrawler] 获取页面内容失败 keyword={keyword}, page={page}: {e}")
            return []
    
    async def store_content(self, content: Dict) -> None:
        """存储内容"""
        try:
            await xhs_store.update_xhs_note(content)
        except Exception as e:
            utils.logger.error(f"[XHSSimulationCrawler] 存储内容失败: {e}")
            raise e
    
    def extract_item_id(self, content: Dict) -> str:
        """提取内容唯一ID"""
        return content.get("note_id", "")
    
    def extract_item_timestamp(self, content: Dict) -> int:
        """提取内容时间戳"""
        return content.get("time", 0)
    
    async def login(self) -> None:
        """登录处理"""
        utils.logger.info("[XHSSimulationCrawler] 开始登录流程")
        
        login_obj = XHSSimulationLogin(
            login_type=config.LOGIN_TYPE,
            browser_context=self.browser_context,
            context_page=self.context_page,
            login_phone=getattr(config, 'XHS_LOGIN_PHONE', ''),
            cookie_str=getattr(config, 'XHS_COOKIE_STR', '')
        )
        
        await login_obj.begin()
        
        # 更新Cookie
        cookie_dict = await self.browser_context.cookies()
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookie_dict}
        
        # 重新初始化客户端
        self.xhs_client = XHSSimulationClient(
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
        utils.logger.info("[XHSSimulationCrawler] 启动浏览器")
        
        if config.ENABLE_CDP_MODE:
            # CDP模式
            return await self._launch_cdp_browser(chromium, playwright_proxy, user_agent, headless)
        else:
            # 普通模式
            return await self._launch_normal_browser(chromium, playwright_proxy, user_agent, headless)
    
    async def _launch_normal_browser(self,
                                   chromium: BrowserType,
                                   playwright_proxy: Optional[Dict],
                                   user_agent: Optional[str],
                                   headless: bool = True) -> BrowserContext:
        """启动普通浏览器"""
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
    
    async def _launch_cdp_browser(self,
                                chromium: BrowserType,
                                playwright_proxy: Optional[Dict],
                                user_agent: Optional[str],
                                headless: bool = True) -> BrowserContext:
        """启动CDP浏览器"""
        # CDP模式实现
        # 这里可以集成现有的CDPBrowserManager
        utils.logger.warning("[XHSSimulationCrawler] CDP模式暂未实现，使用普通模式")
        return await self._launch_normal_browser(chromium, playwright_proxy, user_agent, headless)
    
    async def close(self) -> None:
        """关闭爬虫"""
        utils.logger.info("[XHSSimulationCrawler] 关闭模拟爬虫")
        
        if self.context_page:
            await self.context_page.close()
        
        if self.browser_context:
            await self.browser_context.close()
        
        if self.cdp_manager:
            await self.cdp_manager.close()
    
    async def _simulate_search_behavior(self, keyword: str) -> None:
        """模拟搜索行为"""
        if not self.simulation_config['enable_user_behavior']:
            return
        
        try:
            behavior_sim = UserBehaviorSimulator(self.context_page)
            
            # 模拟在首页停留
            await behavior_sim.simulate_reading_behavior(1, 3)
            
            # 模拟鼠标移动到搜索框
            search_box_selector = "input[placeholder*='搜索'], .search-input, #search-input"
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
            utils.logger.warning(f"[XHSSimulationCrawler] 模拟搜索行为失败: {e}")
    
    async def _get_note_detail_and_comments(self, note_id: str) -> None:
        """获取笔记详情和评论"""
        try:
            # 获取笔记详情
            note_detail = await self.xhs_client.get_note_detail(note_id)
            if note_detail:
                await xhs_store.update_xhs_note(note_detail)
            
            # 获取评论
            if config.ENABLE_GET_COMMENTS:
                cursor = ""
                comment_count = 0
                max_comments = getattr(config, 'CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES', 20)
                
                while comment_count < max_comments:
                    comments_result = await self.xhs_client.get_note_comments(note_id, cursor)
                    
                    if not comments_result.get('comments'):
                        break
                    
                    # 存储评论
                    for comment in comments_result['comments']:
                        comment['note_id'] = note_id  # 添加note_id关联
                        await xhs_store.update_xhs_note_comment(comment)
                        comment_count += 1
                        
                        if comment_count >= max_comments:
                            break
                    
                    if not comments_result.get('has_more', False):
                        break
                        
                    cursor = comments_result.get('cursor', '')
                    
                    # 模拟用户查看评论的延迟
                    if self.simulation_config['enable_user_behavior']:
                        await asyncio.sleep(random.uniform(1, 2))
                        
        except Exception as e:
            utils.logger.error(f"[XHSSimulationCrawler] 获取笔记详情和评论失败 {note_id}: {e}")
    
    def _extract_note_id_from_url(self, url: str) -> Optional[str]:
        """从URL中提取note_id"""
        import re
        
        # 小红书笔记URL格式: https://www.xiaohongshu.com/discovery/item/note_id
        patterns = [
            r'/discovery/item/([a-fA-F0-9]+)',
            r'/explore/([a-fA-F0-9]+)',
            r'note_id=([a-fA-F0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None