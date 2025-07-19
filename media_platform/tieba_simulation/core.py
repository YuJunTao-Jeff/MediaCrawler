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
from model.m_baidu_tieba import TiebaNote, TiebaComment

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
            
            # 登录处理（但不强制要求登录成功）
            try:
                await self.login()
            except Exception as e:
                utils.logger.warning(f"[TiebaSimulationCrawler] 登录失败，但继续进行: {e}")
            
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
                
                # 加入最大空页计数
                empty_page_count = 0
                max_empty_pages = 3
                
                while page <= max_pages and empty_page_count < max_empty_pages:
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
                            empty_page_count += 1
                            utils.logger.info(f"[TiebaSimulationCrawler] 关键词 {keyword} 第 {page} 页无数据 (连续空页: {empty_page_count}/{max_empty_pages})")
                            if empty_page_count >= max_empty_pages:
                                utils.logger.warning(f"[TiebaSimulationCrawler] 连续 {max_empty_pages} 页无数据，停止该关键词的爬取")
                                break
                        else:
                            empty_page_count = 0  # 重置空页计数
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
                        # 如果是网络超时等可恢复错误，可以尝试继续下一页
                        if "timeout" in str(e).lower() or "network" in str(e).lower():
                            utils.logger.info(f"[TiebaSimulationCrawler] 网络错误，尝试继续下一页")
                            page += 1
                            if self.simulation_config['enable_user_behavior']:
                                await asyncio.sleep(random.uniform(2, 5))  # 较长的延迟
                        else:
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
        return content.get("note_id", "")
    
    async def handle_empty_page(self, keyword: str, page: int) -> bool:
        """
        处理空页面情况，对贴吧搜索更宽容
        :param keyword: 关键词
        :param page: 页码
        :return: 是否继续爬取
        """
        # 贴吧搜索结果可能不连续，允许更多的空页面
        if not hasattr(self, '_empty_page_count'):
            self._empty_page_count = 0
        
        self._empty_page_count += 1
        
        # 贴吧允许连续5个空页面，因为搜索结果可能不连续
        if self._empty_page_count >= 5:
            utils.logger.info(f"[TiebaSimulationCrawler] 连续{self._empty_page_count}个空页面，停止爬取关键词: {keyword}")
            return False
        
        utils.logger.info(f"[TiebaSimulationCrawler] 空页面计数: {self._empty_page_count}/5, 继续爬取")
        return True
    
    async def process_crawl_batch(self, keyword: str, page: int, content_list: List[Dict]) -> List[Dict]:
        """处理爬取批次，支持获取帖子详情和评论"""
        utils.logger.info(f"[TiebaSimulationCrawler] 开始批次处理: {len(content_list) if content_list else 0} 个帖子，评论获取开关: {config.ENABLE_GET_COMMENTS}")
        
        if not content_list:
            return []
        
        processed_items = []
        
        for content in content_list:
            try:
                processed_content = content.copy()
                
                # 如果启用了评论获取，则获取帖子详情和评论
                if config.ENABLE_GET_COMMENTS and processed_content.get('note_id'):
                    post_id = processed_content['note_id']
                    utils.logger.info(f"[TiebaSimulationCrawler] 获取帖子详情: {post_id}")
                    
                    try:
                        # 获取帖子详情
                        utils.logger.debug(f"[TiebaSimulationCrawler] 开始获取帖子详情: {post_id}")
                        post_detail = await self.tieba_client.get_post_detail(post_id)
                        if post_detail and post_detail.get('content'):
                            # 更新详细内容，覆盖搜索结果的摘要
                            processed_content['desc'] = post_detail.get('content', processed_content.get('desc', ''))
                            processed_content['user_nickname'] = post_detail.get('author', processed_content.get('user_nickname', ''))
                            utils.logger.info(f"[TiebaSimulationCrawler] 成功更新帖子详情: {post_id}")
                        else:
                            utils.logger.info(f"[TiebaSimulationCrawler] 帖子详情为空，保持原始数据: {post_id}")
                        
                        # 获取帖子评论
                        utils.logger.debug(f"[TiebaSimulationCrawler] 开始获取帖子评论: {post_id}")
                        comments_result = await self.tieba_client.get_post_comments(post_id, 1)
                        if comments_result and comments_result.get('comments'):
                            comment_count = len(comments_result['comments'])
                            processed_content['total_replay_num'] = comment_count
                            utils.logger.info(f"[TiebaSimulationCrawler] 成功获取评论数量: {comment_count}")
                            
                            # 保存评论数据
                            saved_comments = 0
                            for comment in comments_result['comments']:
                                try:
                                    await self._save_comment_data(
                                        comment, 
                                        post_id, 
                                        processed_content.get('note_url', ''),
                                        processed_content.get('tieba_name', ''),
                                        processed_content.get('tieba_link', '')
                                    )
                                    saved_comments += 1
                                except Exception as e:
                                    utils.logger.warning(f"[TiebaSimulationCrawler] 保存评论失败: {e}")
                            
                            if saved_comments > 0:
                                utils.logger.info(f"[TiebaSimulationCrawler] 成功保存 {saved_comments}/{comment_count} 条评论")
                        else:
                            utils.logger.info(f"[TiebaSimulationCrawler] 未获取到评论或评论为空: {post_id}")
                        
                        # 模拟用户行为延迟（缩短延迟时间）
                        await asyncio.sleep(random.uniform(0.3, 1.0))
                        
                    except Exception as e:
                        # 分类错误类型并采用不同的处理策略
                        error_msg = str(e).lower()
                        
                        if "timeout" in error_msg or "exceeded" in error_msg:
                            utils.logger.warning(f"[TiebaSimulationCrawler] 获取帖子详情超时 {post_id}: {e}")
                            utils.logger.info(f"[TiebaSimulationCrawler] 超时不影响主帖保存，继续处理下一个")
                        elif "datafetcherror" in error_msg:
                            utils.logger.warning(f"[TiebaSimulationCrawler] 数据获取错误 {post_id}: {e}")
                        else:
                            utils.logger.error(f"[TiebaSimulationCrawler] 未知错误类型 {post_id}: {e}")
                        
                        # 详情获取失败不影响主帖保存，但记录统计信息
                        processed_content['detail_fetch_failed'] = True
                        processed_content['detail_fetch_error'] = str(e)
                
                processed_items.append(processed_content)
                
            except Exception as e:
                utils.logger.error(f"[TiebaSimulationCrawler] 处理帖子数据失败: {e}")
                continue
        
        # 统计处理结果
        total_items = len(content_list) if content_list else 0
        processed_count = len(processed_items)
        failed_details = sum(1 for item in processed_items if item.get('detail_fetch_failed', False))
        successful_details = processed_count - failed_details
        
        utils.logger.info(f"[TiebaSimulationCrawler] 批次处理完成: {processed_count}/{total_items}")
        if config.ENABLE_GET_COMMENTS and processed_count > 0:
            utils.logger.info(f"[TiebaSimulationCrawler] 详情获取统计: 成功 {successful_details}, 失败 {failed_details}")
            
            # 计算成功率
            if processed_count > 0:
                success_rate = (successful_details / processed_count) * 100
                utils.logger.info(f"[TiebaSimulationCrawler] 详情获取成功率: {success_rate:.1f}%")
        
        # 有内容时重置空页面计数
        if processed_items:
            self._empty_page_count = 0
            
        return processed_items
    
    def extract_item_timestamp(self, content: Dict) -> int:
        """提取内容时间戳"""
        import time
        import re
        from datetime import datetime
        
        publish_time = content.get("publish_time", "")
        if not publish_time:
            return int(time.time() * 1000)  # 返回当前时间戳
        
        try:
            # 尝试解析贴吧时间格式：2024-05-28 15:33
            if re.match(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}', str(publish_time)):
                dt = datetime.strptime(str(publish_time), '%Y-%m-%d %H:%M')
                return int(dt.timestamp() * 1000)
            
            # 如果已经是时间戳，直接返回
            if isinstance(publish_time, (int, float)):
                return int(publish_time)
            
            # 如果是字符串数字，转换为整数
            if str(publish_time).isdigit():
                return int(publish_time)
                
        except Exception as e:
            utils.logger.debug(f"[TiebaSimulationCrawler] 时间戳解析失败: {e}")
        
        # 如果无法解析，返回当前时间戳
        return int(time.time() * 1000)
    
    async def login(self) -> None:
        """登录处理"""
        utils.logger.info("[TiebaSimulationCrawler] 开始登录流程")
        
        # 检查是否已经登录
        try:
            # 检查登录状态
            current_url = self.context_page.url
            if "login" not in current_url:
                # 检查是否有用户信息元素
                user_elements = await self.context_page.query_selector_all(".u_menu_username, .user_name, .userinfo_username")
                if user_elements:
                    utils.logger.info("[TiebaSimulationCrawler] 检测到已登录状态，跳过登录流程")
                    return
        except Exception:
            pass
        
        login_obj = TiebaSimulationLogin(
            login_type=config.LOGIN_TYPE,
            browser_context=self.browser_context,
            context_page=self.context_page,
            login_phone=getattr(config, 'TIEBA_LOGIN_PHONE', ''),
            cookie_str=getattr(config, 'TIEBA_COOKIE_STR', '')
        )
        
        try:
            await login_obj.begin()
            utils.logger.info("[TiebaSimulationCrawler] 登录流程完成")
        except Exception as e:
            utils.logger.warning(f"[TiebaSimulationCrawler] 登录失败，但继续执行: {e}")
        
        # 更新Cookie
        try:
            cookie_dict = await self.browser_context.cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookie_dict}
            
            # 重新初始化客户端
            self.tieba_client = TiebaSimulationClient(
                timeout=30,
                proxies=None,  # 代理信息保持不变
                playwright_page=self.context_page,
                cookie_dict=cookie_dict
            )
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationCrawler] 更新Cookie失败: {e}")
    
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
            "--disable-setuid-sandbox",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-field-trial-config",
            "--disable-ipc-flooding-protection"
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
            
            # 检查是否在贴吧首页，如果不是则导航过去
            current_url = self.context_page.url
            if "tieba.baidu.com" not in current_url or "/f/search" in current_url:
                utils.logger.info("[TiebaSimulationCrawler] 导航到贴吧首页")
                await self.context_page.goto("https://tieba.baidu.com", wait_until="domcontentloaded")
                await asyncio.sleep(2)
            
            # 模拟鼠标移动到搜索框（基于Chrome MCP分析的真实页面结构）
            search_box_selectors = [
                "input.s_ipt#kw",          # 主要选择器：真实页面的搜索输入框
                "input#kw",                # 备选：仅ID选择器
                "input.s_ipt",             # 备选：仅class选择器
                "input[name='kw']",        # 备选：name属性
                ".search-input",           # 通用选择器（保留兼容性）
                "#search-input",
                "input[placeholder*='搜索']"
            ]
            
            search_box_found = False
            for selector in search_box_selectors:
                try:
                    element = await self.context_page.query_selector(selector)
                    if element and await element.is_visible():
                        await behavior_sim.simulate_mouse_movement(selector)
                        
                        # 模拟输入关键词（字符间有延迟）
                        await self.context_page.fill(selector, "")  # 先清空
                        for char in keyword:
                            await self.context_page.type(selector, char, delay=random.randint(50, 200))
                        
                        search_box_found = True
                        utils.logger.info(f"[TiebaSimulationCrawler] 成功找到并填写搜索框: {selector}")
                        break
                except Exception as e:
                    utils.logger.debug(f"[TiebaSimulationCrawler] 搜索框 {selector} 不可用: {e}")
                    continue
            
            if not search_box_found:
                utils.logger.warning("[TiebaSimulationCrawler] 未找到可用的搜索框")
                return
            
            # 短暂停顿后点击搜索按钮
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # 查找并点击搜索按钮（基于Chrome MCP分析的真实页面结构）
            search_btn_selectors = [
                "input.s_btn#su",          # 主要选择器：真实页面的搜索按钮
                "input#su",                # 备选：仅ID选择器  
                "input.s_btn",             # 备选：仅class选择器
                "input[type='submit']",    # 备选：type属性
                ".search-btn",             # 通用选择器（保留兼容性）
                "button[type='submit']",
                "input[value='百度一下']"
            ]
            
            search_btn_found = False
            for btn_selector in search_btn_selectors:
                try:
                    btn_element = await self.context_page.query_selector(btn_selector)
                    if btn_element and await btn_element.is_visible():
                        # 模拟鼠标移动到搜索按钮
                        await behavior_sim.simulate_mouse_movement(btn_selector)
                        await asyncio.sleep(random.uniform(0.2, 0.5))
                        
                        # 点击搜索按钮
                        await btn_element.click()
                        utils.logger.info(f"[TiebaSimulationCrawler] 成功点击搜索按钮: {btn_selector}")
                        search_btn_found = True
                        
                        # 等待搜索结果页面加载
                        await asyncio.sleep(random.uniform(2, 4))
                        break
                except Exception as e:
                    utils.logger.debug(f"[TiebaSimulationCrawler] 搜索按钮 {btn_selector} 不可用: {e}")
                    continue
            
            if not search_btn_found:
                utils.logger.warning("[TiebaSimulationCrawler] 未找到可用的搜索按钮，尝试按Enter键搜索")
                # 备选方案：按Enter键触发搜索
                try:
                    await self.context_page.keyboard.press('Enter')
                    await asyncio.sleep(random.uniform(2, 4))
                    utils.logger.info("[TiebaSimulationCrawler] 使用Enter键触发搜索")
                except Exception as e:
                    utils.logger.error(f"[TiebaSimulationCrawler] Enter键搜索也失败: {e}")
            
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
                        await self._save_comment_data(
                            comment, 
                            post_id, 
                            f"https://tieba.baidu.com/p/{post_id}",
                            "",  # tieba_name - 将在评论保存时设置默认值
                            ""   # tieba_link - 将在评论保存时设置默认值
                        )
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
            # 添加source_keyword字段
            post_data['source_keyword'] = source_keyword_var.get()
            
            # 数据清洗和验证
            cleaned_data = self._clean_post_data(post_data)
            
            # 转换为TiebaNote对象
            tieba_note = TiebaNote(**cleaned_data)
            
            # 保存到数据库
            await tieba_store.update_tieba_note(tieba_note)
            
        except ValueError as e:
            utils.logger.error(f"[TiebaSimulationCrawler] 数据验证失败: {e}")
            utils.logger.debug(f"[TiebaSimulationCrawler] 问题数据: {post_data}")
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationCrawler] 保存帖子数据失败: {e}")
            utils.logger.debug(f"[TiebaSimulationCrawler] 问题数据: {post_data}")
    
    def _clean_post_data(self, post_data: Dict) -> Dict:
        """清洗帖子数据，确保符合TiebaNote模型要求"""
        cleaned = post_data.copy()
        
        # 确保必需字段存在且不为空
        required_fields = ['note_id', 'title', 'note_url', 'tieba_name', 'tieba_link']
        for field in required_fields:
            if not cleaned.get(field):
                if field == 'note_id':
                    raise ValueError(f"必需字段 {field} 不能为空")
                cleaned[field] = ""
        
        # 限制字符串字段长度
        string_limits = {
            'title': 500,
            'desc': 1000,
            'note_url': 1000,
            'publish_time': 50,
            'user_link': 1000,
            'user_nickname': 100,
            'user_avatar': 1000,
            'tieba_name': 100,
            'tieba_link': 1000,
            'ip_location': 100,
            'source_keyword': 100
        }
        
        for field, limit in string_limits.items():
            if field in cleaned and isinstance(cleaned[field], str):
                if len(cleaned[field]) > limit:
                    cleaned[field] = cleaned[field][:limit]
        
        # 确保数值字段为整数
        numeric_fields = ['total_replay_num', 'total_replay_page']
        for field in numeric_fields:
            if field in cleaned:
                try:
                    cleaned[field] = int(cleaned[field]) if cleaned[field] else 0
                except (ValueError, TypeError):
                    cleaned[field] = 0
        
        # 移除不属于TiebaNote模型的字段（如错误记录字段）
        model_fields = {
            'note_id', 'title', 'desc', 'note_url', 'publish_time', 
            'user_link', 'user_nickname', 'user_avatar', 'tieba_name', 
            'tieba_link', 'total_replay_num', 'total_replay_page', 
            'ip_location', 'source_keyword'
        }
        
        # 保留模型字段，移除其他字段
        cleaned = {k: v for k, v in cleaned.items() if k in model_fields}
        
        return cleaned
    
    async def _save_comment_data(self, comment_data: Dict, note_id: str, note_url: str, tieba_name: str, tieba_link: str) -> None:
        """保存评论数据"""
        try:
            # 确保必需字段存在并重命名字段以匹配TiebaComment模型
            processed_comment = {
                'comment_id': comment_data.get('comment_id', f"comment_{int(time.time())}"),
                'content': comment_data.get('content', ''),  # 必需字段
                'user_nickname': comment_data.get('author', ''),  # 将author映射为user_nickname
                'note_id': note_id,
                'note_url': note_url,
                'tieba_name': tieba_name,
                'tieba_link': tieba_link,
                'tieba_id': "",
                'parent_comment_id': "",
                'user_link': "",
                'user_avatar': "",
                'publish_time': "",
                'ip_location': "",
                'sub_comment_count': 0,
            }
            
            # 转换为TiebaComment对象
            tieba_comment = TiebaComment(**processed_comment)
            
            # 保存到数据库
            await tieba_store.update_tieba_note_comment(note_id, tieba_comment)
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationCrawler] 保存评论数据失败: {e}")
            utils.logger.debug(f"[TiebaSimulationCrawler] 问题评论数据: {comment_data}")
    
    async def _save_creator_data(self, creator_data: Dict) -> None:
        """保存创作者数据"""
        try:
            # 这里需要根据实际的存储模型来调整
            await tieba_store.save_creator(creator_data)
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationCrawler] 保存创作者数据失败: {e}")