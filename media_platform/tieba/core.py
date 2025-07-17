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
                            utils.logger.info("[BaiduTieBaCrawler.search] 检测到安全验证，直接加载验证页面HTML")
                            # 尝试获取最后一次请求的HTML内容
                            await self.handle_security_verification_with_html(keyword, page)
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
                utils.logger.error(f"[BaiduTieBaCrawler.get_note_detail] Get note detail error: {ex}")
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
        """直接加载安全验证HTML内容到浏览器"""
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
            
            utils.logger.info("[BaiduTieBaCrawler.handle_security_verification_with_html] 安全验证页面已加载，请在浏览器中完成验证")
            utils.logger.info("[BaiduTieBaCrawler.handle_security_verification_with_html] 完成验证后，您可以重新运行程序")
            
            # 保持页面打开供用户操作
            await page_obj.wait_for_timeout(30000)  # 等待30秒供用户处理验证
            
        except Exception as e:
            utils.logger.error(f"[BaiduTieBaCrawler.handle_security_verification_with_html] Error: {e}")

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
