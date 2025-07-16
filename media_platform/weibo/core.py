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
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/23 15:41
# @Desc    : 微博爬虫主流程代码


import asyncio
import os
import random
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page, Playwright,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import weibo as weibo_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import WeiboClient
from .exception import DataFetchError
from .field import SearchType
from .help import filter_search_result_card
from .login import WeiboLogin


class WeiboCrawler(AbstractCrawler):
    context_page: Page
    wb_client: WeiboClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self):
        super().__init__()
        self.index_url = "https://www.weibo.com"
        self.mobile_index_url = "https://m.weibo.cn"
        self.user_agent = utils.get_user_agent()
        self.mobile_user_agent = utils.get_mobile_user_agent()
        self.cdp_manager = None

    async def start(self):
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[WeiboCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright, playwright_proxy_format, self.mobile_user_agent,
                    headless=config.CDP_HEADLESS
                )
            else:
                utils.logger.info("[WeiboCrawler] 使用标准模式启动浏览器")
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    None,
                    self.mobile_user_agent,
                    headless=config.HEADLESS
                )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.mobile_index_url)

            # Create a client to interact with the xiaohongshu website.
            self.wb_client = await self.create_weibo_client(httpx_proxy_format)
            if not await self.wb_client.pong():
                login_obj = WeiboLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # your phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()

                # 登录成功后重定向到手机端的网站，再更新手机端登录成功的cookie
                utils.logger.info("[WeiboCrawler.start] redirect weibo mobile homepage and update cookies on mobile platform")
                await self.context_page.goto(self.mobile_index_url)
                await asyncio.sleep(2)
                await self.wb_client.update_cookies(browser_context=self.browser_context)

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for video and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_notes()
            elif config.CRAWLER_TYPE == "creator":
                # Get creator's information and their notes and comments
                await self.get_creators_and_notes()
            else:
                pass
            utils.logger.info("[WeiboCrawler.start] Weibo Crawler finished ...")

    async def search(self):
        """
        search weibo note with keywords
        :return:
        """
        utils.logger.info("[WeiboCrawler.search] Begin search weibo keywords")
        weibo_limit_count = 10  # weibo limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < weibo_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = weibo_limit_count
        start_page = config.START_PAGE

        # Set the search type based on the configuration for weibo
        if config.WEIBO_SEARCH_TYPE == "default":
            search_type = SearchType.DEFAULT
        elif config.WEIBO_SEARCH_TYPE == "real_time":
            search_type = SearchType.REAL_TIME
        elif config.WEIBO_SEARCH_TYPE == "popular":
            search_type = SearchType.POPULAR
        elif config.WEIBO_SEARCH_TYPE == "video":
            search_type = SearchType.VIDEO
        else:
            utils.logger.error(f"[WeiboCrawler.search] Invalid WEIBO_SEARCH_TYPE: {config.WEIBO_SEARCH_TYPE}")
            return

        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[WeiboCrawler.search] Current search keyword: {keyword}")
            page = 1
            while (page - start_page + 1) * weibo_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[WeiboCrawler.search] Skip page: {page}")
                    page += 1
                    continue
                utils.logger.info(f"[WeiboCrawler.search] search weibo keyword: {keyword}, page: {page}")
                
                try:
                    search_res = await self.wb_client.get_note_by_keyword(
                        keyword=keyword,
                        page=page,
                        search_type=search_type
                    )
                    note_id_list: List[str] = []
                    note_list = filter_search_result_card(search_res.get("cards"))
                    for note_item in note_list:
                        if note_item:
                            mblog: Dict = note_item.get("mblog")
                            if mblog:
                                note_id_list.append(mblog.get("id"))
                                await weibo_store.update_weibo_note(note_item)
                                await self.get_note_images(mblog)

                    page += 1
                    await self.batch_get_notes_comments(note_id_list)
                    
                except DataFetchError as ex:
                    error_msg = str(ex)
                    utils.logger.warning(f"[WeiboCrawler.search] search keyword: {keyword}, page: {page} error: {error_msg}")
                    
                    # 根据错误类型进行分类处理
                    if "这里还没有内容" in error_msg:
                        utils.logger.info(f"[WeiboCrawler.search] keyword: {keyword} 搜索结果为空，跳过剩余页面")
                        break  # 跳出当前关键词的分页循环
                    elif "博主已开启防火墙" in error_msg:
                        utils.logger.info(f"[WeiboCrawler.search] keyword: {keyword}, page: {page} 遇到防火墙限制，跳过当前页面")
                        page += 1
                        continue  # 继续下一页
                    else:
                        utils.logger.error(f"[WeiboCrawler.search] keyword: {keyword}, page: {page} 未知错误: {error_msg}")
                        page += 1
                        continue  # 继续下一页
                        
                except Exception as ex:
                    utils.logger.error(f"[WeiboCrawler.search] keyword: {keyword}, page: {page} 发生未预期错误: {ex}")
                    page += 1
                    continue  # 继续下一页

    async def get_specified_notes(self):
        """
        get specified notes info
        :return:
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_info_task(note_id=note_id, semaphore=semaphore) for note_id in
            config.WEIBO_SPECIFIED_ID_LIST
        ]
        video_details = await asyncio.gather(*task_list)
        for note_item in video_details:
            if note_item:
                await weibo_store.update_weibo_note(note_item)
        await self.batch_get_notes_comments(config.WEIBO_SPECIFIED_ID_LIST)

    async def get_note_info_task(self, note_id: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """
        Get note detail task
        :param note_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.wb_client.get_note_info_by_id(note_id)
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[WeiboCrawler.get_note_info_task] Get note detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[WeiboCrawler.get_note_info_task] have not fund note detail note_id:{note_id}, err: {ex}")
                return None

    async def batch_get_notes_comments(self, note_id_list: List[str]):
        """
        batch get notes comments
        :param note_id_list:
        :return:
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[WeiboCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(f"[WeiboCrawler.batch_get_notes_comments] note ids:{note_id_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for note_id in note_id_list:
            task = asyncio.create_task(self.get_note_comments(note_id, semaphore), name=note_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_note_comments(self, note_id: str, semaphore: asyncio.Semaphore):
        """
        get comment for note id
        :param note_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                utils.logger.info(f"[WeiboCrawler.get_note_comments] begin get note_id: {note_id} comments ...")
                await self.wb_client.get_note_all_comments(
                    note_id=note_id,
                    crawl_interval=random.randint(1,3), # 微博对API的限流比较严重，所以延时提高一些
                    callback=weibo_store.batch_update_weibo_note_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES
                )
            except DataFetchError as ex:
                utils.logger.error(f"[WeiboCrawler.get_note_comments] get note_id: {note_id} comment error: {ex}")
            except Exception as e:
                utils.logger.error(f"[WeiboCrawler.get_note_comments] may be been blocked, err:{e}")

    async def get_note_images(self, mblog: Dict):
        """
        get note images
        :param mblog:
        :return:
        """
        if not config.ENABLE_GET_IMAGES:
            utils.logger.info(f"[WeiboCrawler.get_note_images] Crawling image mode is not enabled")
            return
        
        pics: Dict = mblog.get("pics")
        if not pics:
            return
        for pic in pics:
            url = pic.get("url")
            if not url:
                continue
            content = await self.wb_client.get_note_image(url)
            if content != None:
                extension_file_name = url.split(".")[-1]
                await weibo_store.update_weibo_note_image(pic["pid"], content, extension_file_name)


    async def get_creators_and_notes(self) -> None:
        """
        Get creator's information and their notes and comments
        Returns:

        """
        utils.logger.info("[WeiboCrawler.get_creators_and_notes] Begin get weibo creators")
        for user_id in config.WEIBO_CREATOR_ID_LIST:
            createor_info_res: Dict = await self.wb_client.get_creator_info_by_id(creator_id=user_id)
            if createor_info_res:
                createor_info: Dict = createor_info_res.get("userInfo", {})
                utils.logger.info(f"[WeiboCrawler.get_creators_and_notes] creator info: {createor_info}")
                if not createor_info:
                    raise DataFetchError("Get creator info error")
                await weibo_store.save_creator(user_id, user_info=createor_info)

                # Get all note information of the creator
                all_notes_list = await self.wb_client.get_all_notes_by_creator_id(
                    creator_id=user_id,
                    container_id=createor_info_res.get("lfid_container_id"),
                    crawl_interval=0,
                    callback=weibo_store.batch_update_weibo_notes
                )

                note_ids = [note_item.get("mblog", {}).get("id") for note_item in all_notes_list if
                            note_item.get("mblog", {}).get("id")]
                await self.batch_get_notes_comments(note_ids)

            else:
                utils.logger.error(
                    f"[WeiboCrawler.get_creators_and_notes] get creator info error, creator_id:{user_id}")



    async def create_weibo_client(self, httpx_proxy: Optional[str]) -> WeiboClient:
        """Create xhs client"""
        utils.logger.info("[WeiboCrawler.create_weibo_client] Begin create weibo API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        weibo_client_obj = WeiboClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": utils.get_mobile_user_agent(),
                "Cookie": cookie_str,
                "Origin": "https://m.weibo.cn",
                "Referer": "https://m.weibo.cn",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return weibo_client_obj

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

    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[WeiboCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
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
            utils.logger.info(f"[WeiboCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[WeiboCrawler] CDP模式启动失败，回退到标准模式: {e}")
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
        utils.logger.info("[WeiboCrawler.close] Browser context closed ...")

    # ==================== 实现新的简化接口 ====================
    
    async def get_page_content(self, keyword: str, page: int) -> List[Dict]:
        """获取指定关键词和页码的内容列表"""
        try:
            # 微博搜索API调用
            wb_result = await self.wb_client.get_note_by_keyword(keyword=keyword, page=page)
            if not wb_result or not wb_result.get("cards"):
                return []
            
            # 转换为标准格式
            content_list = []
            for card in wb_result["cards"]:
                if card.get("card_type") == 9:  # 微博内容类型
                    mblog = card.get("mblog", {})
                    content_dict = {
                        "note_id": mblog.get("id", ""),
                        "title": mblog.get("text", "")[:50],  # 取前50字符作为标题
                        "desc": mblog.get("text", ""),
                        "user_id": mblog.get("user", {}).get("id", ""),
                        "user_name": mblog.get("user", {}).get("screen_name", ""),
                        "liked_count": mblog.get("attitudes_count", 0),
                        "comment_count": mblog.get("comments_count", 0),
                        "repost_count": mblog.get("reposts_count", 0),
                        "created_time": mblog.get("created_at", ""),
                        "keyword": keyword,
                        "page": page,
                        "source": mblog.get("source", ""),
                        "region_name": mblog.get("region_name", ""),
                        "pic_ids": mblog.get("pic_ids", []),
                        "pic_infos": mblog.get("pic_infos", {}),
                        "isLongText": mblog.get("isLongText", False),
                        "raw_data": mblog  # 保留原始数据
                    }
                    content_list.append(content_dict)
            
            return content_list
            
        except Exception as e:
            utils.logger.error(f"[WeiboCrawler.get_page_content] Error: {e}")
            raise

    async def store_content(self, content_item: Dict) -> None:
        """存储单个内容项"""
        try:
            # 转换为微博Note对象
            from model.m_weibo import WeiboContent
            
            # 构造WeiboContent对象
            weibo_data = {
                "note_id": content_item.get("note_id", ""),
                "content": content_item.get("desc", ""),
                "create_time": content_item.get("created_time", ""),
                "create_date_time": 0,  # 需要转换时间
                "liked_count": content_item.get("liked_count", 0),
                "comments_count": content_item.get("comment_count", 0),
                "shared_count": content_item.get("repost_count", 0),
                "source": content_item.get("source", ""),
                "user_id": content_item.get("user_id", ""),
                "nickname": content_item.get("user_name", ""),
                "gender": "",
                "profile_url": "",
                "avatar": "",
                "location": content_item.get("region_name", ""),
                "profile": "",
                "verified": "",
                "verified_type": 0,
                "followers_count": 0,
                "follows_count": 0,
                "notes_count": 0,
                "ip_location": content_item.get("region_name", ""),
                "keyword": content_item.get("keyword", ""),
                "image_list": content_item.get("pic_ids", []),
                "video_url": "",
                "is_long_text": content_item.get("isLongText", False)
            }
            
            # 时间转换
            if weibo_data["create_time"]:
                import time
                from datetime import datetime
                try:
                    # 微博时间格式转换
                    create_time_str = weibo_data["create_time"]
                    if "刚刚" in create_time_str:
                        weibo_data["create_date_time"] = int(time.time() * 1000)
                    elif "分钟前" in create_time_str:
                        minutes = int(create_time_str.replace("分钟前", ""))
                        weibo_data["create_date_time"] = int((time.time() - minutes * 60) * 1000)
                    elif "小时前" in create_time_str:
                        hours = int(create_time_str.replace("小时前", ""))
                        weibo_data["create_date_time"] = int((time.time() - hours * 3600) * 1000)
                    else:
                        # 其他格式尝试解析
                        weibo_data["create_date_time"] = int(time.time() * 1000)
                except:
                    weibo_data["create_date_time"] = int(time.time() * 1000)
            
            weibo_note = WeiboContent(**weibo_data)
            await weibo_store.update_weibo_note(weibo_note)
            
        except Exception as e:
            utils.logger.error(f"[WeiboCrawler.store_content] Error: {e}")
            raise

    def extract_item_id(self, content_item: Dict) -> str:
        """从内容项中提取唯一ID"""
        return content_item.get("note_id", "")

    def extract_item_timestamp(self, content_item: Dict) -> int:
        """从内容项中提取时间戳"""
        # 微博时间处理比较复杂，需要解析相对时间
        create_time = content_item.get("created_time", "")
        if create_time:
            import time
            try:
                if "刚刚" in create_time:
                    return int(time.time() * 1000)
                elif "分钟前" in create_time:
                    minutes = int(create_time.replace("分钟前", ""))
                    return int((time.time() - minutes * 60) * 1000)
                elif "小时前" in create_time:
                    hours = int(create_time.replace("小时前", ""))
                    return int((time.time() - hours * 3600) * 1000)
                else:
                    return int(time.time() * 1000)
            except:
                return int(time.time() * 1000)
        return int(time.time() * 1000)

    def get_platform_config(self) -> Dict:
        """获取微博平台特定配置"""
        return {
            'page_limit': 20,  # 微博每页约20条
            'enable_comments': config.ENABLE_GET_COMMENTS,
            'max_empty_pages': 3
        }
