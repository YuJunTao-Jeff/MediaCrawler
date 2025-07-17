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
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page, Playwright,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from model.m_baidu_tieba import TiebaCreator, TiebaNote
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import tieba as tieba_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from tools.crawler_util import format_proxy_info
from var import crawler_type_var, source_keyword_var

from .client import BaiduTieBaClient
from .field import SearchNoteType, SearchSortType
from .help import TieBaExtractor
from .login import BaiduTieBaLogin


class TieBaCrawler(AbstractCrawler):
    context_page: Page
    tieba_client: BaiduTieBaClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        super().__init__()
        self.index_url = "https://tieba.baidu.com"
        self.user_agent = utils.get_user_agent()
        self._page_extractor = TieBaExtractor()
        self.cdp_manager = None

    async def start(self) -> None:
        """
        Start the crawler
        Returns:

        """
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            utils.logger.info("[BaiduTieBaCrawler.start] Begin create ip proxy pool ...")
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = format_proxy_info(ip_proxy_info)
            utils.logger.info(f"[BaiduTieBaCrawler.start] Init default ip proxy, value: {httpx_proxy_format}")

        try:
            async with async_playwright() as playwright:
                # 根据配置选择启动模式
                if config.ENABLE_CDP_MODE:
                    utils.logger.info("🚀 使用CDP模式，需要启动CDP浏览器")
                    self.browser_context = await self.launch_browser_with_cdp(
                        playwright, playwright_proxy_format, self.user_agent,
                        headless=config.CDP_HEADLESS
                    )
                else:
                    utils.logger.info("🌐 使用标准模式，无需启动CDP浏览器")
                    # Launch a browser context.
                    chromium = playwright.chromium
                    self.browser_context = await self.launch_browser(
                        chromium, playwright_proxy_format, self.user_agent, 
                        headless=config.HEADLESS
                    )

                # Create a client to interact with the baidutieba website.
                self.tieba_client = BaiduTieBaClient(
                    ip_pool=ip_proxy_pool if config.ENABLE_IP_PROXY else None,
                    default_ip_proxy=httpx_proxy_format,
                )
                
                crawler_type_var.set(config.CRAWLER_TYPE)
                if config.CRAWLER_TYPE == "search":
                    # Search for notes and retrieve their comment information.
                    await self.search()
                    await self.get_specified_tieba_notes()
                elif config.CRAWLER_TYPE == "detail":
                    # Get the information and comments of the specified post
                    await self.get_specified_notes()
                elif config.CRAWLER_TYPE == "creator":
                    # Get creator's information and their notes and comments
                    await self.get_creators_and_notes()
                else:
                    pass
        except Exception as e:
            utils.logger.error(f"[BaiduTieBaCrawler.start] Error: {e}")
            raise e
        finally:
            await self.close()

        utils.logger.info("[BaiduTieBaCrawler.start] Tieba Crawler finished ...")

    async def search(self) -> None:
        """
        Search for notes and retrieve their comment information.
        Returns:

        """
        utils.logger.info("[BaiduTieBaCrawler.search] Begin search baidu tieba keywords")
        tieba_limit_count = 10  # tieba limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < tieba_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = tieba_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[BaiduTieBaCrawler.search] Current search keyword: {keyword}")
            page = 1
            while (page - start_page + 1) * tieba_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[BaiduTieBaCrawler.search] Skip page {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(f"[BaiduTieBaCrawler.search] search tieba keyword: {keyword}, page: {page}")
                    
                    # 尝试通过API获取数据
                    try:
                        notes_list: List[TiebaNote] = await self.tieba_client.get_notes_by_keyword(
                            keyword=keyword,
                            page=page,
                            page_size=tieba_limit_count,
                            sort=SearchSortType.TIME_DESC,
                            note_type=SearchNoteType.FIXED_THREAD
                        )
                        if not notes_list:
                            utils.logger.info(f"[BaiduTieBaCrawler.search] Search note list is empty")
                            break
                        utils.logger.info(f"[BaiduTieBaCrawler.search] Note list len: {len(notes_list)}")
                        await self.get_specified_notes(note_id_list=[note_detail.note_id for note_detail in notes_list])
                        page += 1
                    except Exception as api_ex:
                        # 如果API请求失败，可能是遇到安全验证，使用浏览器导航
                        error_msg = str(api_ex)
                        if ("Security verification" in error_msg or 
                            "browser verification" in error_msg or
                            "403" in error_msg or 
                            "IP已经被Block" in error_msg):
                            utils.logger.info("[BaiduTieBaCrawler.search] 检测到安全验证，尝试自动化处理")
                            
                            # 尝试自动化处理验证
                            auto_result = await self.handle_security_verification_with_html(keyword, page)
                            
                            if auto_result and len(auto_result) > 0:
                                # 自动验证成功，处理搜索结果
                                utils.logger.info(f"[BaiduTieBaCrawler.search] 自动验证成功，获得 {len(auto_result)} 个结果")
                                await self.get_specified_notes(note_id_list=[note_detail.note_id for note_detail in auto_result])
                                page += 1
                                continue  # 继续下一页搜索
                            else:
                                # 自动验证失败，中断搜索
                                utils.logger.info("[BaiduTieBaCrawler.search] 自动验证失败，停止搜索")
                                break
                        else:
                            raise api_ex
                            
                except Exception as ex:
                    utils.logger.error(
                        f"[BaiduTieBaCrawler.search] Search keywords error, current page: {page}, current keyword: {keyword}, err: {ex}")
                    break

    async def get_specified_tieba_notes(self):
        """
        Get the information and comments of the specified post by tieba name
        Returns:

        """
        tieba_limit_count = 50
        if config.CRAWLER_MAX_NOTES_COUNT < tieba_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = tieba_limit_count
        for tieba_name in config.TIEBA_NAME_LIST:
            utils.logger.info(
                f"[BaiduTieBaCrawler.get_specified_tieba_notes] Begin get tieba name: {tieba_name}")
            page_number = 0
            while page_number <= config.CRAWLER_MAX_NOTES_COUNT:
                note_list: List[TiebaNote] = await self.tieba_client.get_notes_by_tieba_name(
                    tieba_name=tieba_name,
                    page_num=page_number
                )
                if not note_list:
                    utils.logger.info(
                        f"[BaiduTieBaCrawler.get_specified_tieba_notes] Get note list is empty")
                    break

                utils.logger.info(
                    f"[BaiduTieBaCrawler.get_specified_tieba_notes] tieba name: {tieba_name} note list len: {len(note_list)}")
                await self.get_specified_notes([note.note_id for note in note_list])
                page_number += tieba_limit_count

    async def get_specified_notes(self, note_id_list: List[str] = config.TIEBA_SPECIFIED_ID_LIST):
        """
        Get the information and comments of the specified post
        Args:
            note_id_list:

        Returns:

        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_detail_async_task(note_id=note_id, semaphore=semaphore) for note_id in note_id_list
        ]
        note_details = await asyncio.gather(*task_list)
        note_details_model: List[TiebaNote] = []
        for note_detail in note_details:
            if note_detail is not None:
                note_details_model.append(note_detail)
                await tieba_store.update_tieba_note(note_detail)
        await self.batch_get_note_comments(note_details_model)

    async def get_note_detail_async_task(self, note_id: str, semaphore: asyncio.Semaphore) -> Optional[TiebaNote]:
        """
        Get note detail
        Args:
            note_id: baidu tieba note id
            semaphore: asyncio semaphore

        Returns:

        """
        async with semaphore:
            try:
                utils.logger.info(f"[BaiduTieBaCrawler.get_note_detail] Begin get note detail, note_id: {note_id}")
                note_detail: TiebaNote = await self.tieba_client.get_note_by_id(note_id)
                if not note_detail:
                    utils.logger.error(
                        f"[BaiduTieBaCrawler.get_note_detail] Get note detail error, note_id: {note_id}")
                    return None
                return note_detail
            except Exception as ex:
                utils.logger.error(f"[BaiduTieBaCrawler.get_note_detail] Get note detail error: {ex}", exc_info=True)
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[BaiduTieBaCrawler.get_note_detail] have not fund note detail note_id:{note_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, note_detail_list: List[TiebaNote]):
        """
        Batch get note comments
        Args:
            note_detail_list:

        Returns:

        """
        if not config.ENABLE_GET_COMMENTS:
            return

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for note_detail in note_detail_list:
            task = asyncio.create_task(self.get_comments_async_task(note_detail, semaphore), name=note_detail.note_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments_async_task(self, note_detail: TiebaNote, semaphore: asyncio.Semaphore):
        """
        Get comments async task
        Args:
            note_detail:
            semaphore:

        Returns:

        """
        async with semaphore:
            utils.logger.info(f"[BaiduTieBaCrawler.get_comments] Begin get note id comments {note_detail.note_id}")
            await self.tieba_client.get_note_all_comments(
                note_detail=note_detail,
                crawl_interval=random.random(),
                callback=tieba_store.batch_update_tieba_note_comments,
                max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES
            )

    async def get_creators_and_notes(self) -> None:
        """
        Get creator's information and their notes and comments
        Returns:

        """
        utils.logger.info("[WeiboCrawler.get_creators_and_notes] Begin get weibo creators")
        for creator_url in config.TIEBA_CREATOR_URL_LIST:
            creator_page_html_content = await self.tieba_client.get_creator_info_by_url(creator_url=creator_url)
            creator_info: TiebaCreator = self._page_extractor.extract_creator_info(creator_page_html_content)
            if creator_info:
                utils.logger.info(f"[WeiboCrawler.get_creators_and_notes] creator info: {creator_info}")
                if not creator_info:
                    raise Exception("Get creator info error")

                await tieba_store.save_creator(user_info=creator_info)

                # Get all note information of the creator
                all_notes_list = await self.tieba_client.get_all_notes_by_creator_user_name(
                    user_name=creator_info.user_name,
                    crawl_interval=0,
                    callback=tieba_store.batch_update_tieba_notes,
                    max_note_count=config.CRAWLER_MAX_NOTES_COUNT,
                    creator_page_html_content=creator_page_html_content,
                )

                await self.batch_get_note_comments(all_notes_list)

            else:
                utils.logger.error(
                    f"[WeiboCrawler.get_creators_and_notes] get creator info error, creator_url:{creator_url}")

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """
        Launch browser and create browser
        Args:
            chromium:
            playwright_proxy:
            user_agent:
            headless:

        Returns:

        """
        utils.logger.info("[BaiduTieBaCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
            # feat issue #14
            # we will save login state to avoid login every time
            user_data_dir = os.path.join(os.getcwd(), "browser_data",
                                         config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions",
                    "--disable-plugins-discovery",
                    "--no-first-run",
                    "--disable-default-apps"
                ]
            )
            return browser_context
        else:
            browser = await chromium.launch(
                headless=headless, 
                proxy=playwright_proxy,
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions",
                    "--disable-plugins-discovery",
                    "--no-first-run",
                    "--disable-default-apps"
                ]
            )  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
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
            utils.logger.info(f"[TieBaCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[TieBaCrawler] CDP模式启动失败，回退到标准模式: {e}")
            # 回退到标准模式
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self):
        """
        Close browser context
        Returns:

        """
        try:
            # 如果使用CDP模式，需要特殊处理
            if self.cdp_manager:
                await self.cdp_manager.cleanup()
                self.cdp_manager = None
            elif hasattr(self, 'browser_context') and self.browser_context:
                await self.browser_context.close()
            utils.logger.info("[BaiduTieBaCrawler.close] Browser context closed ...")
        except Exception as e:
            utils.logger.warning(f"[BaiduTieBaCrawler.close] Error closing browser context: {e}")

    async def handle_security_verification(self, keyword: str):
        """处理安全验证，使用浏览器导航到登录页面"""
        try:
            if not hasattr(self, 'browser_context') or not self.browser_context:
                utils.logger.error("[BaiduTieBaCrawler.handle_security_verification] Browser context not available")
                return
                
            # 创建新页面并导航到贴吧首页
            page = await self.browser_context.new_page()
            utils.logger.info("[BaiduTieBaCrawler.handle_security_verification] 正在导航到贴吧首页...")
            await page.goto("https://tieba.baidu.com")
            
            # 等待页面加载
            await page.wait_for_timeout(3000)
            
            # 检查是否需要登录
            try:
                # 尝试查找登录按钮或登录相关元素
                login_element = await page.wait_for_selector(".u_login", timeout=5000)
                if login_element:
                    utils.logger.info("[BaiduTieBaCrawler.handle_security_verification] 检测到需要登录，请在浏览器中完成登录...")
                    # 点击登录按钮
                    await login_element.click()
                    
                    # 等待用户完成登录（等待较长时间）
                    utils.logger.info("[BaiduTieBaCrawler.handle_security_verification] 等待用户登录完成...")
                    await page.wait_for_timeout(30000)  # 等待30秒供用户登录
                    
            except Exception:
                # 可能已经登录或页面结构不同
                utils.logger.info("[BaiduTieBaCrawler.handle_security_verification] 页面可能已经登录或需要手动处理")
                
            # 保持页面打开供用户操作
            utils.logger.info("[BaiduTieBaCrawler.handle_security_verification] 浏览器页面已打开，请手动完成验证和登录")
            
        except Exception as e:
            utils.logger.error(f"[BaiduTieBaCrawler.handle_security_verification] Error: {e}")

    async def handle_security_verification_with_url(self, url: str):
        """处理安全验证，直接打开验证页面URL"""
        try:
            if not hasattr(self, 'browser_context') or not self.browser_context:
                utils.logger.error("[BaiduTieBaCrawler.handle_security_verification_with_url] Browser context not available")
                return
                
            # 创建新页面并直接导航到验证页面
            page = await self.browser_context.new_page()
            utils.logger.info(f"[BaiduTieBaCrawler.handle_security_verification_with_url] 正在打开验证页面: {url}")
            await page.goto(url)
            
            # 等待页面加载
            await page.wait_for_timeout(5000)
            
            utils.logger.info("[BaiduTieBaCrawler.handle_security_verification_with_url] 安全验证页面已打开，请在浏览器中完成验证")
            utils.logger.info("[BaiduTieBaCrawler.handle_security_verification_with_url] 完成验证后，可以手动刷新页面或重新运行程序")
            
            # 保持页面打开供用户操作
            await page.wait_for_timeout(30000)  # 等待30秒供用户处理验证
            
        except Exception as e:
            utils.logger.error(f"[BaiduTieBaCrawler.handle_security_verification_with_url] Error: {e}")

    async def handle_security_verification_with_html(self, keyword: str, page: int):
        """直接加载安全验证HTML内容到浏览器，并尝试自动化处理"""
        try:
            if not hasattr(self, 'browser_context') or not self.browser_context:
                utils.logger.error("[BaiduTieBaCrawler.handle_security_verification_with_html] Browser context not available")
                return
                
            if not hasattr(self, 'tieba_client') or not self.tieba_client.last_verification_html:
                utils.logger.warning("[BaiduTieBaCrawler.handle_security_verification_with_html] No verification HTML available, fallback to URL")
                search_url = f"https://tieba.baidu.com/f/search/res?isnew=1&qw={keyword}&rn=10&pn={page}&sm=1&only_thread=0"
                await self.handle_security_verification_with_url(search_url)
                return
                
            # 创建新页面并直接设置HTML内容
            page_obj = await self.browser_context.new_page()
            utils.logger.info("[BaiduTieBaCrawler.handle_security_verification_with_html] 正在加载安全验证页面HTML...")
            
            # 直接设置HTML内容
            await page_obj.set_content(self.tieba_client.last_verification_html)
            
            # 尝试自动化处理验证
            verification_result = await self.auto_handle_verification(page_obj, keyword, page)
            
            if verification_result:
                utils.logger.info("[BaiduTieBaCrawler.handle_security_verification_with_html] 自动验证成功，继续搜索流程")
                return verification_result
            else:
                utils.logger.info("[BaiduTieBaCrawler.handle_security_verification_with_html] 自动验证失败，需要手动处理")
                utils.logger.info("[BaiduTieBaCrawler.handle_security_verification_with_html] 请在浏览器中完成验证")
                # 保持页面打开供用户操作
                await page_obj.wait_for_timeout(30000)
            
        except Exception as e:
            utils.logger.error(f"[BaiduTieBaCrawler.handle_security_verification_with_html] Error: {e}")

    async def auto_handle_verification(self, page_obj, keyword: str, page_num: int):
        """自动化处理安全验证"""
        try:
            utils.logger.info("[BaiduTieBaCrawler.auto_handle_verification] 开始自动化验证处理...")
            
            # 检查页面是否还可用
            try:
                await page_obj.evaluate("document.readyState")
            except Exception as e:
                utils.logger.error(f"[BaiduTieBaCrawler.auto_handle_verification] 页面已关闭: {e}")
                return None
            
            # 等待验证页面完全加载，包括动态脚本
            utils.logger.info("[BaiduTieBaCrawler.auto_handle_verification] 等待验证页面动态内容加载...")
            try:
                await page_obj.wait_for_timeout(8000)  # 增加等待时间
            except Exception as e:
                utils.logger.error(f"[BaiduTieBaCrawler.auto_handle_verification] 等待超时: {e}")
                return None
            
            # 等待页面内容完全渲染
            try:
                await page_obj.wait_for_function("document.readyState === 'complete'", timeout=5000)
            except Exception as e:
                utils.logger.warning(f"[BaiduTieBaCrawler.auto_handle_verification] 等待页面完成失败: {e}")
            
            # 调试：输出当前页面内容
            current_content = await page_obj.content()
            utils.logger.info(f"[BaiduTieBaCrawler.auto_handle_verification] 当前页面长度: {len(current_content)}")
            
            # 尝试查找所有可点击元素，包括div按钮
            try:
                clickable_selectors = [
                    "button", "input[type='button']", "input[type='submit']",
                    "[role='button']", ".btn", "[onclick]",
                    # 百度BIOC特定元素
                    ".bioc_disaster_proven_tip_text", "span.bioc_disaster_proven_tip_text",
                    "[class*='bioc']", ".bioc-btn", ".bioc_btn",
                    # 专门针对div按钮的选择器
                    "div[onclick]", "div[role='button']", "div.btn", "div.button",
                    "div[data-action]", "div[data-click]", "div[data-testid]",
                    # 专门针对span按钮的选择器
                    "span[onclick]", "span[role='button']", "span.btn", "span.button",
                    "span[data-action]", "span[data-click]", "span[data-testid]",
                    # 百度特定的元素
                    "div[data-module]", "div.verify", "div.confirm", "div.check",
                    "span.verify", "span.confirm", "span.check",
                    # CSS样式指示的可点击元素
                    "div[style*='cursor: pointer']", "div[style*='cursor:pointer']",
                    "span[style*='cursor: pointer']", "span[style*='cursor:pointer']"
                ]
                
                all_buttons = []
                for selector in clickable_selectors:
                    elements = await page_obj.query_selector_all(selector)
                    all_buttons.extend(elements)
                
                # 去重
                unique_buttons = []
                seen_elements = set()
                for btn in all_buttons:
                    btn_handle = await btn.evaluate("el => el")
                    if btn_handle not in seen_elements:
                        unique_buttons.append(btn)
                        seen_elements.add(btn_handle)
                
                all_buttons = unique_buttons
                utils.logger.info(f"[BaiduTieBaCrawler.auto_handle_verification] 找到 {len(all_buttons)} 个可能的可点击元素")
                
                # 检查是否有iframe
                iframes = await page_obj.query_selector_all("iframe")
                utils.logger.info(f"[BaiduTieBaCrawler.auto_handle_verification] 找到 {len(iframes)} 个iframe")
                
                # 详细分析每个元素，特别关注div按钮
                for i, btn in enumerate(all_buttons[:10]):  # 检查更多元素
                    try:
                        text = await btn.text_content()
                        tag = await btn.evaluate("el => el.tagName")
                        class_name = await btn.get_attribute("class") or ""
                        onclick = await btn.get_attribute("onclick") or ""
                        role = await btn.get_attribute("role") or ""
                        data_action = await btn.get_attribute("data-action") or ""
                        cursor_style = await btn.evaluate("el => getComputedStyle(el).cursor")
                        
                        # 检查是否是可点击的div
                        is_clickable = (
                            onclick or 
                            role == "button" or 
                            "btn" in class_name.lower() or
                            "button" in class_name.lower() or
                            "click" in class_name.lower() or
                            "verify" in class_name.lower() or
                            "confirm" in class_name.lower() or
                            cursor_style == "pointer" or
                            data_action
                        )
                        
                        utils.logger.info(f"[BaiduTieBaCrawler.auto_handle_verification] 元素{i+1}: {tag}, class='{class_name}', text='{text[:20]}', 可点击={is_clickable}")
                        if onclick:
                            utils.logger.info(f"  └─ onclick: {onclick[:50]}")
                        if cursor_style == "pointer":
                            utils.logger.info(f"  └─ cursor: {cursor_style}")
                            
                    except Exception as e:
                        utils.logger.warning(f"[BaiduTieBaCrawler.auto_handle_verification] 分析元素{i+1}失败: {e}")
                        
                # 如果没找到按钮但有iframe，尝试在iframe中查找
                if len(all_buttons) == 0 and len(iframes) > 0:
                    utils.logger.info("[BaiduTieBaCrawler.auto_handle_verification] 尝试在iframe中查找验证元素")
                    for i, iframe in enumerate(iframes):
                        try:
                            iframe_content = await iframe.content_frame()
                            if iframe_content:
                                iframe_buttons = await iframe_content.query_selector_all("button, input[type='button'], [role='button'], .btn")
                                utils.logger.info(f"[BaiduTieBaCrawler.auto_handle_verification] iframe{i+1}中找到 {len(iframe_buttons)} 个按钮")
                        except Exception as iframe_e:
                            utils.logger.warning(f"[BaiduTieBaCrawler.auto_handle_verification] 检查iframe{i+1}失败: {iframe_e}")
                            
            except Exception as e:
                utils.logger.warning(f"[BaiduTieBaCrawler.auto_handle_verification] 查找按钮失败: {e}")
                
            # 由于这是一个特殊的百度验证页面，尝试等待自动重定向
            utils.logger.info("[BaiduTieBaCrawler.auto_handle_verification] 这是百度BIOC验证页面，等待自动处理或重定向")
            
            # 等待可能的重定向或验证完成
            try:
                # 监听页面URL变化，等待跳转到搜索结果页面
                for wait_round in range(6):  # 最多等待30秒
                    await page_obj.wait_for_timeout(5000)  # 每轮等待5秒
                    current_url = page_obj.url
                    utils.logger.info(f"[BaiduTieBaCrawler.auto_handle_verification] 等待第{wait_round+1}轮，当前URL: {current_url}")
                    
                    # 检查是否已经跳转
                    if "search/res" in current_url and "qw=" in current_url:
                        utils.logger.info("[BaiduTieBaCrawler.auto_handle_verification] 检测到自动跳转到搜索页面")
                        content = await page_obj.content()
                        return self._page_extractor.extract_search_note_list(content)
                    
                    # 检查页面内容是否发生变化
                    new_content = await page_obj.content()
                    if len(new_content) != len(current_content):
                        utils.logger.info(f"[BaiduTieBaCrawler.auto_handle_verification] 页面内容发生变化: {len(current_content)} -> {len(new_content)}")
                        current_content = new_content
                        
                        # 重新检查是否有可点击元素出现
                        new_buttons = await page_obj.query_selector_all("button, input[type='button'], [role='button'], .btn, [onclick], div[onclick]")
                        if len(new_buttons) > 0:
                            utils.logger.info(f"[BaiduTieBaCrawler.auto_handle_verification] 发现新的可点击元素: {len(new_buttons)} 个")
                            all_buttons = new_buttons
                            break
                            
            except Exception as wait_e:
                utils.logger.warning(f"[BaiduTieBaCrawler.auto_handle_verification] 等待验证处理失败: {wait_e}")
            
            # 专门针对百度BIOC验证的选择器
            verification_selectors = [
                # 优先级1: 百度BIOC特定元素（最高优先级）
                '.bioc_disaster_proven_tip_text',
                'span.bioc_disaster_proven_tip_text',
                '.bioc_disaster_proven_tip_text:contains("点击按钮开始验证")',
                'span:contains("点击按钮开始验证")',
                '.bioc-disaster-proven-tip-text',
                
                # 优先级2: 百度验证相关
                '.bioc-btn',
                '.bioc_btn', 
                '[class*="bioc"]',
                'div[data-module="security"]',
                'div[data-action="verify"]', 
                'div[data-action="confirm"]',
                'div.security-check-btn',
                'div.verify-button',
                'div.verify-btn',
                'div.confirm-btn',
                'div.captcha-button',
                'div.verification-button',
                
                # 优先级3: 包含验证文本的元素
                '*:contains("点击按钮开始验证")',
                '*:contains("点击验证")',
                '*:contains("开始验证")',
                'div:contains("确认")',
                'div:contains("验证")',
                'span:contains("验证")',
                'div:contains("继续访问")',
                'div:contains("点击完成验证")',
                'div:contains("立即验证")',
                
                # 优先级4: 传统按钮元素
                'button[data-name="confirm"]',
                'button:contains("确认")',
                'button:contains("验证")',
                'input[type="submit"]',
                'button[type="submit"]',
                
                # 优先级5: 通用可点击元素
                '[role="button"]',
                '.btn',
                'button',
                
                # 优先级6: 任何带onclick的元素（最后尝试）
                'div[onclick]',
                'span[onclick]',
            ]
            
            for selector in verification_selectors:
                try:
                    # 等待元素出现
                    element = await page_obj.wait_for_selector(selector, timeout=2000)
                    if element:
                        utils.logger.info(f"[BaiduTieBaCrawler.auto_handle_verification] 找到验证元素: {selector}")
                        
                        # 点击验证元素
                        await element.click()
                        utils.logger.info("[BaiduTieBaCrawler.auto_handle_verification] 已点击验证元素")
                        
                        # 等待验证处理
                        await page_obj.wait_for_timeout(2000)
                        
                        # 检查是否跳转到搜索结果页面
                        current_url = page_obj.url
                        if "search/res" in current_url and "qw=" in current_url:
                            utils.logger.info("[BaiduTieBaCrawler.auto_handle_verification] 验证成功，已跳转到搜索结果页面")
                            
                            # 直接从当前页面提取搜索结果
                            content = await page_obj.content()
                            return self._page_extractor.extract_search_note_list(content)
                        
                        break
                        
                except Exception as e:
                    # 这个选择器没找到，尝试下一个
                    continue
            
            # 如果没有自动跳转，尝试等待跳转
            try:
                utils.logger.info("[BaiduTieBaCrawler.auto_handle_verification] 等待页面跳转...")
                await page_obj.wait_for_url("**/search/res**", timeout=5000)
                content = await page_obj.content()
                return self._page_extractor.extract_search_note_list(content)
            except:
                pass
                
            # 自动验证失败，尝试重新发起API请求
            utils.logger.info("[BaiduTieBaCrawler.auto_handle_verification] 自动验证可能成功，尝试重新发起API请求")
            await page_obj.wait_for_timeout(3000)  # 等待验证完成
            
            try:
                return await self.tieba_client.get_notes_by_keyword(
                    keyword=keyword,
                    page=page_num,
                    page_size=10,
                    sort=SearchSortType.TIME_DESC,
                    note_type=SearchNoteType.FIXED_THREAD
                )
            except Exception as retry_ex:
                utils.logger.warning(f"[BaiduTieBaCrawler.auto_handle_verification] API重试也失败: {retry_ex}")
                return None
                
        except Exception as e:
            utils.logger.error(f"[BaiduTieBaCrawler.auto_handle_verification] 自动验证处理失败: {e}")
            return None

    # 实现抽象方法
    def extract_item_id(self, content: dict) -> str:
        """从内容中提取唯一ID"""
        return content.get("note_id", "")

    def extract_item_timestamp(self, content: dict) -> int:
        """从内容中提取时间戳"""
        return content.get("publish_time", 0)

    async def get_page_content(self, page_num: int) -> List[dict]:
        """获取指定页面的内容"""
        # 这里需要根据实际需求实现
        return []

    async def store_content(self, content: dict) -> None:
        """存储内容到数据库"""
        await tieba_store.update_tieba_note(content)
