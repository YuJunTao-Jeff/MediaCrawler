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
import os
import random
import time
from asyncio import Task
from typing import Dict, List, Optional, Tuple, cast

from playwright.async_api import (BrowserContext, BrowserType, Page, Playwright,
                                  async_playwright)

import config
from constant import zhihu as constant
from base.base_crawler import AbstractCrawler
from model.m_zhihu import ZhihuContent, ZhihuCreator
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import zhihu as zhihu_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import ZhiHuClient
from .exception import DataFetchError
from .help import ZhihuExtractor, judge_zhihu_url
from .login import ZhiHuLogin


class ZhihuCrawler(AbstractCrawler):
    context_page: Page
    zhihu_client: ZhiHuClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        super().__init__()
        self.index_url = "https://www.zhihu.com"
        # self.user_agent = utils.get_user_agent()
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        self._extractor = ZhihuExtractor()
        self.cdp_manager = None

    async def start(self) -> None:
        """
        Start the crawler
        Returns:

        """
        # 初始化断点续爬功能
        await self.init_resume_crawl("zhihu", config.RESUME_TASK_ID)
        
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)

        try:
            async with async_playwright() as playwright:
                # 根据配置选择启动模式
                if config.ENABLE_CDP_MODE:
                    utils.logger.info("[ZhihuCrawler] 使用CDP模式启动浏览器")
                    self.browser_context = await self.launch_browser_with_cdp(
                        playwright, playwright_proxy_format, self.user_agent,
                        headless=config.CDP_HEADLESS
                    )
                else:
                    utils.logger.info("[ZhihuCrawler] 使用标准模式启动浏览器")
                    # Launch a browser context.
                    chromium = playwright.chromium
                    self.browser_context = await self.launch_browser(
                        chromium,
                        None,
                        self.user_agent,
                        headless=config.HEADLESS
                    )
                # stealth.min.js is a js script to prevent the website from detecting the crawler.
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

                self.context_page = await self.browser_context.new_page()
                await self.context_page.goto(self.index_url, wait_until="domcontentloaded")

                # Create a client to interact with the zhihu website.
                self.zhihu_client = await self.create_zhihu_client(httpx_proxy_format)
                if not await self.zhihu_client.pong():
                    login_obj = ZhiHuLogin(
                        login_type=config.LOGIN_TYPE,
                        login_phone="",  # input your phone number
                        browser_context=self.browser_context,
                        context_page=self.context_page,
                        cookie_str=config.COOKIES
                    )
                    await login_obj.begin()
                    await self.zhihu_client.update_cookies(browser_context=self.browser_context)

                # 知乎的搜索接口需要打开搜索页面之后cookies才能访问API，单独的首页不行
                utils.logger.info("[ZhihuCrawler.start] Zhihu跳转到搜索页面获取搜索页面的Cookies，该过程需要5秒左右")
                await self.context_page.goto(f"{self.index_url}/search?q=python&search_source=Guess&utm_content=search_hot&type=content")
                await asyncio.sleep(5)
                await self.zhihu_client.update_cookies(browser_context=self.browser_context)

                crawler_type_var.set(config.CRAWLER_TYPE)
                if config.CRAWLER_TYPE == "search":
                    # Search for notes and retrieve their comment information.
                    await self.search()
                elif config.CRAWLER_TYPE == "detail":
                    # Get the information and comments of the specified post
                    await self.get_specified_notes()
                elif config.CRAWLER_TYPE == "creator":
                    # Get creator's information and their notes and comments
                    await self.get_creators_and_notes()
                else:
                    pass

                utils.logger.info("[ZhihuCrawler.start] Zhihu Crawler finished ...")
                
        finally:
            # 清理断点续爬资源
            await self.cleanup_crawl_progress()

    async def search(self) -> None:
        """Search for notes and retrieve their comment information."""
        utils.logger.info("[ZhihuCrawler.search] Begin search zhihu keywords")
        zhihu_limit_count = 20  # zhihu limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < zhihu_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = zhihu_limit_count
        
        for keyword in config.KEYWORDS.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue
                
            source_keyword_var.set(keyword)
            utils.logger.info(f"[ZhihuCrawler.search] Current search keyword: {keyword}")
            
            # 获取断点续爬起始页
            start_page = await self.get_resume_start_page(keyword)
            
            # 如果起始页是999999，表示该关键词已完成
            if start_page >= 999999:
                utils.logger.info(f"[ZhihuCrawler.search] Keyword {keyword} already completed, skip")
                continue
            
            page = max(start_page, 1)
            total_items = 0
            new_items = 0
            duplicate_items = 0
            failed_items = 0
            empty_page_count = 0
            
            while (page - start_page + 1) * zhihu_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                # 检查是否应该停止
                if await self.should_stop_keyword_crawl(keyword, page):
                    utils.logger.info(f"[ZhihuCrawler.search] Stop crawling keyword {keyword} at page {page}")
                    break

                try:
                    utils.logger.info(f"[ZhihuCrawler.search] search zhihu keyword: {keyword}, page: {page}")
                    content_list: List[ZhihuContent]  = await self.zhihu_client.get_note_by_keyword(
                        keyword=keyword,
                        page=page,
                    )
                    utils.logger.info(f"[ZhihuCrawler.search] Search contents count: {len(content_list) if content_list else 0}")
                    
                    if not content_list:
                        empty_page_count += 1
                        if not await self.handle_empty_page(keyword, page):
                            utils.logger.info(f"[ZhihuCrawler.search] Too many empty pages for keyword {keyword}, stopping")
                            break
                        page += 1
                        continue
                    else:
                        empty_page_count = 0

                    # 批量处理数据
                    processed_items = await self.process_crawl_batch(keyword, page, 
                                                                   [content.model_dump() for content in content_list])
                    
                    # 去重和存储
                    page_new_items = 0
                    page_duplicate_items = 0
                    page_failed_items = 0
                    
                    for content in content_list:
                        total_items += 1
                        
                        # 检查是否应该跳过（去重）
                        if await self.should_skip_content(content.model_dump(), keyword):
                            duplicate_items += 1
                            page_duplicate_items += 1
                            continue
                        
                        # 存储数据
                        try:
                            await zhihu_store.update_zhihu_content(content)
                            new_items += 1
                            page_new_items += 1
                        except Exception as e:
                            failed_items += 1
                            page_failed_items += 1
                            utils.logger.error(f"[ZhihuCrawler.search] Store content failed: {e}")

                    # 更新进度
                    last_item = content_list[-1].model_dump() if content_list else None
                    await self.update_crawl_progress(keyword, page, len(content_list), last_item)
                    
                    # 保存检查点（只保存必要的元数据）
                    checkpoint_data = {
                        'page': page,
                        'items_count': len(content_list),
                        'last_item_id': content_list[-1].content_id if content_list else None,
                        'last_item_time': content_list[-1].created_time if content_list else None,
                        'page_stats': {
                            'new': page_new_items,
                            'duplicate': page_duplicate_items,
                            'failed': page_failed_items
                        }
                    }
                    await self.save_crawl_checkpoint(keyword, page, checkpoint_data)

                    # 获取评论
                    await self.batch_get_content_comments(content_list)
                    
                    page += 1
                    
                except DataFetchError:
                    utils.logger.error("[ZhihuCrawler.search] Search content error")
                    failed_items += 1
                    page += 1
                    continue
                except Exception as e:
                    import traceback
                    utils.logger.error(f"[ZhihuCrawler.search] Unexpected error: {e}")
                    utils.logger.error(f"[ZhihuCrawler.search] Traceback: {traceback.format_exc()}")
                    failed_items += 1
                    page += 1
                    continue
            
            # 标记关键词完成
            await self.mark_keyword_completed(keyword)
            
            # 更新统计信息
            await self.update_crawl_statistics(total_items, new_items, duplicate_items, failed_items)
            utils.logger.info(f"[ZhihuCrawler.search] Keyword {keyword} completed: total={total_items}, new={new_items}, duplicate={duplicate_items}, failed={failed_items}")

    async def batch_get_content_comments(self, content_list: List[ZhihuContent]):
        """
        Batch get content comments
        Args:
            content_list:

        Returns:

        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[ZhihuCrawler.batch_get_content_comments] Crawling comment mode is not enabled")
            return

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for content_item in content_list:
            task = asyncio.create_task(self.get_comments(content_item, semaphore), name=content_item.content_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments(self, content_item: ZhihuContent, semaphore: asyncio.Semaphore):
        """
        Get note comments with keyword filtering and quantity limitation
        Args:
            content_item:
            semaphore:

        Returns:

        """
        async with semaphore:
            utils.logger.info(f"[ZhihuCrawler.get_comments] Begin get note id comments {content_item.content_id}")
            await self.zhihu_client.get_note_all_comments(
                content=content_item,
                crawl_interval=random.random(),
                callback=zhihu_store.batch_update_zhihu_note_comments
            )

    async def get_creators_and_notes(self) -> None:
        """
        Get creator's information and their notes and comments
        Returns:

        """
        utils.logger.info("[ZhihuCrawler.get_creators_and_notes] Begin get xiaohongshu creators")
        for user_link in config.ZHIHU_CREATOR_URL_LIST:
            utils.logger.info(f"[ZhihuCrawler.get_creators_and_notes] Begin get creator {user_link}")
            user_url_token = user_link.split("/")[-1]
            # get creator detail info from web html content
            createor_info: ZhihuCreator = await self.zhihu_client.get_creator_info(url_token=user_url_token)
            if not createor_info:
                utils.logger.info(f"[ZhihuCrawler.get_creators_and_notes] Creator {user_url_token} not found")
                continue

            utils.logger.info(f"[ZhihuCrawler.get_creators_and_notes] Creator info: {createor_info}")
            await zhihu_store.save_creator(creator=createor_info)

            # 默认只提取回答信息，如果需要文章和视频，把下面的注释打开即可

            # Get all anwser information of the creator
            all_content_list = await self.zhihu_client.get_all_anwser_by_creator(
                creator=createor_info,
                crawl_interval=random.random(),
                callback=zhihu_store.batch_update_zhihu_contents
            )


            # Get all articles of the creator's contents
            # all_content_list = await self.zhihu_client.get_all_articles_by_creator(
            #     creator=createor_info,
            #     crawl_interval=random.random(),
            #     callback=zhihu_store.batch_update_zhihu_contents
            # )

            # Get all videos of the creator's contents
            # all_content_list = await self.zhihu_client.get_all_videos_by_creator(
            #     creator=createor_info,
            #     crawl_interval=random.random(),
            #     callback=zhihu_store.batch_update_zhihu_contents
            # )

            # Get all comments of the creator's contents
            await self.batch_get_content_comments(all_content_list)

    async def get_note_detail(
        self, full_note_url: str, semaphore: asyncio.Semaphore
    ) -> Optional[ZhihuContent]:
        """
        Get note detail
        Args:
            full_note_url: str
            semaphore:

        Returns:

        """
        async with semaphore:
            utils.logger.info(
                f"[ZhihuCrawler.get_specified_notes] Begin get specified note {full_note_url}"
            )
            # judge note type
            note_type: str = judge_zhihu_url(full_note_url)
            if note_type == constant.ANSWER_NAME:
                question_id = full_note_url.split("/")[-3]
                answer_id = full_note_url.split("/")[-1]
                utils.logger.info(
                    f"[ZhihuCrawler.get_specified_notes] Get answer info, question_id: {question_id}, answer_id: {answer_id}"
                )
                return await self.zhihu_client.get_answer_info(question_id, answer_id)

            elif note_type == constant.ARTICLE_NAME:
                article_id = full_note_url.split("/")[-1]
                utils.logger.info(
                    f"[ZhihuCrawler.get_specified_notes] Get article info, article_id: {article_id}"
                )
                return await self.zhihu_client.get_article_info(article_id)

            elif note_type == constant.VIDEO_NAME:
                video_id = full_note_url.split("/")[-1]
                utils.logger.info(
                    f"[ZhihuCrawler.get_specified_notes] Get video info, video_id: {video_id}"
                )
                return await self.zhihu_client.get_video_info(video_id)

    async def get_specified_notes(self):
        """
        Get the information and comments of the specified post
        Returns:

        """
        get_note_detail_task_list = []
        for full_note_url in config.ZHIHU_SPECIFIED_ID_LIST:
            # remove query params
            full_note_url = full_note_url.split("?")[0]
            crawler_task = self.get_note_detail(
                full_note_url=full_note_url,
                semaphore=asyncio.Semaphore(config.MAX_CONCURRENCY_NUM),
            )
            get_note_detail_task_list.append(crawler_task)

        need_get_comment_notes: List[ZhihuContent] = []
        note_details = await asyncio.gather(*get_note_detail_task_list)
        for index, note_detail in enumerate(note_details):
            if not note_detail:
                utils.logger.info(
                    f"[ZhihuCrawler.get_specified_notes] Note {config.ZHIHU_SPECIFIED_ID_LIST[index]} not found"
                )
                continue

            note_detail = cast(ZhihuContent, note_detail)  # only for type check
            need_get_comment_notes.append(note_detail)
            await zhihu_store.update_zhihu_content(note_detail)

        await self.batch_get_content_comments(need_get_comment_notes)

    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
        """format proxy info for playwright and httpx"""
        playwright_proxy = {
            "server": f"{ip_proxy_info.protocol}{ip_proxy_info.ip}:{ip_proxy_info.port}",
            "username": ip_proxy_info.user,
            "password": ip_proxy_info.password,
        }
        httpx_proxy = {
            f"{ip_proxy_info.protocol}": f"http://{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"
        }
        return playwright_proxy, httpx_proxy

    async def create_zhihu_client(self, httpx_proxy: Optional[str]) -> ZhiHuClient:
        """Create zhihu client"""
        utils.logger.info("[ZhihuCrawler.create_zhihu_client] Begin create zhihu API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        zhihu_client_obj = ZhiHuClient(
            proxies=httpx_proxy,
            headers={
                'accept': '*/*',
                'accept-language': 'zh-CN,zh;q=0.9',
                'cookie': cookie_str,
                'priority': 'u=1, i',
                'referer': 'https://www.zhihu.com/search?q=python&time_interval=a_year&type=content',
                'user-agent': self.user_agent,
                'x-api-version': '3.0.91',
                'x-app-za': 'OS=Web',
                'x-requested-with': 'fetch',
                'x-zse-93': '101_3_3.0',
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return zhihu_client_obj

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[ZhihuCrawler.launch_browser] Begin create browser context ...")
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
            utils.logger.info(f"[ZhihuCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[ZhihuCrawler] CDP模式启动失败，回退到标准模式: {e}")
            # 回退到标准模式
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self):
        """Close browser context"""
        # 如果使用CDP模式，需要特殊处理
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[ZhihuCrawler.close] Browser context closed ...")

    # ==================== 断点续爬必须实现的抽象方法 ====================
    
    def extract_item_id(self, content_item: Dict) -> Optional[str]:
        """从内容项中提取唯一ID"""
        # 知乎内容的唯一ID
        return content_item.get('content_id') or content_item.get('id')
    
    def extract_item_timestamp(self, content_item: Dict) -> Optional[int]:
        """从内容项中提取时间戳"""
        # 知乎内容的时间戳字段
        timestamp = content_item.get('created_time') or content_item.get('updated_time')
        if timestamp:
            # 确保返回毫秒级时间戳
            if isinstance(timestamp, int):
                # 如果是秒级时间戳，转换为毫秒
                if timestamp < 10000000000:  # 小于10位数，可能是秒级
                    return timestamp * 1000
                return timestamp
        return None
    
    # ==================== 可选实现的断点续爬优化方法 ====================
    
    async def smart_search_optimization(self, keyword: str, page: int) -> tuple:
        """智能搜索优化"""
        if not config.ENABLE_SMART_SEARCH:
            return False, {}
        
        # 知乎搜索优化示例：如果已经爬取了很多页，可以调整搜索策略
        if page > 30:  # 如果已经爬取了很多页
            # 可以考虑调整搜索排序等参数
            return True, {'sort_type': 'time'}
        
        return False, {}
    
    async def process_crawl_batch(self, keyword: str, page: int, items: List[Dict]) -> List[Dict]:
        """批量处理爬取数据"""
        # 为知乎数据添加爬取元数据
        processed_items = []
        
        for item in items:
            # 添加爬取元数据
            item['crawl_keyword'] = keyword
            item['crawl_page'] = page
            item['crawl_time'] = int(time.time() * 1000)
            
            # 确保source_keyword字段存在
            if 'source_keyword' not in item:
                item['source_keyword'] = keyword
            
            processed_items.append(item)
        
        return processed_items
