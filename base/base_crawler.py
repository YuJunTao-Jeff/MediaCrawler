# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any, Tuple

from playwright.async_api import BrowserContext, BrowserType, Playwright


class AbstractCrawler(ABC):
    def __init__(self):
        self.progress_manager = None
        self.is_resume_mode = False
        
    @abstractmethod
    async def start(self):
        """
        start crawler
        """
        pass

    @abstractmethod
    async def search(self):
        """
        search
        """
        pass

    @abstractmethod
    async def launch_browser(self, chromium: BrowserType, playwright_proxy: Optional[Dict], user_agent: Optional[str],
                             headless: bool = True) -> BrowserContext:
        """
        launch browser
        :param chromium: chromium browser
        :param playwright_proxy: playwright proxy
        :param user_agent: user agent
        :param headless: headless mode
        :return: browser context
        """
        pass

    async def launch_browser_with_cdp(self, playwright: Playwright, playwright_proxy: Optional[Dict],
                                     user_agent: Optional[str], headless: bool = True) -> BrowserContext:
        """
        使用CDP模式启动浏览器（可选实现）
        :param playwright: playwright实例
        :param playwright_proxy: playwright代理配置
        :param user_agent: 用户代理
        :param headless: 无头模式
        :return: 浏览器上下文
        """
        # 默认实现：回退到标准模式
        return await self.launch_browser(playwright.chromium, playwright_proxy, user_agent, headless)

    # ==================== 断点续爬相关抽象方法 ====================
    
    async def init_resume_crawl(self, platform: str, task_id: Optional[str] = None):
        """
        初始化断点续爬功能
        :param platform: 平台名称
        :param task_id: 任务ID，如果不指定则自动生成
        """
        import config
        if not config.ENABLE_RESUME_CRAWL:
            return
            
        from tools.crawl_progress import CrawlProgressManager
        self.progress_manager = CrawlProgressManager(platform, task_id)
        await self.progress_manager.initialize()
        self.is_resume_mode = True

    async def get_resume_start_page(self, keyword: str) -> int:
        """
        获取断点续爬的起始页
        :param keyword: 关键词
        :return: 起始页码
        """
        if not self.progress_manager:
            import config
            return config.START_PAGE
        return await self.progress_manager.get_resume_page(keyword)

    async def should_skip_content(self, content_item: Dict, keyword: str) -> bool:
        """
        判断是否应该跳过该内容（去重）
        :param content_item: 内容项
        :param keyword: 关键词
        :return: 是否跳过
        """
        if not self.progress_manager:
            return False
        
        # 子类需要实现具体的ID和时间戳提取逻辑
        item_id = self.extract_item_id(content_item)
        item_timestamp = self.extract_item_timestamp(content_item)
        
        if item_id and item_timestamp:
            return await self.progress_manager.should_skip_item(item_id, item_timestamp, keyword)
        return False

    async def update_crawl_progress(self, keyword: str, page: int, items_count: int, 
                                  last_item: Optional[Dict] = None):
        """
        更新爬取进度
        :param keyword: 关键词
        :param page: 当前页码
        :param items_count: 当前页面条目数
        :param last_item: 最后一个条目
        """
        if not self.progress_manager:
            return
            
        last_item_id = None
        last_item_time = None
        
        if last_item:
            last_item_id = self.extract_item_id(last_item)
            last_item_time = self.extract_item_timestamp(last_item)
        
        await self.progress_manager.update_keyword_progress(
            keyword, page, items_count, last_item_id, last_item_time
        )

    async def mark_keyword_completed(self, keyword: str):
        """
        标记关键词完成
        :param keyword: 关键词
        """
        if self.progress_manager:
            await self.progress_manager.mark_keyword_completed(keyword)

    async def should_stop_keyword_crawl(self, keyword: str, page: int) -> bool:
        """
        判断是否应该停止当前关键词的爬取
        :param keyword: 关键词
        :param page: 当前页码
        :return: 是否停止
        """
        if not self.progress_manager:
            return False
        return await self.progress_manager.should_stop_crawling(keyword, page)

    async def save_crawl_checkpoint(self, keyword: str, page: int, checkpoint_data: Dict):
        """
        保存爬取检查点
        :param keyword: 关键词
        :param page: 页码
        :param checkpoint_data: 检查点数据
        """
        if self.progress_manager:
            await self.progress_manager.save_checkpoint(keyword, page, checkpoint_data)

    async def get_crawl_checkpoint(self, keyword: str, page: int) -> Optional[Dict]:
        """
        获取爬取检查点
        :param keyword: 关键词
        :param page: 页码
        :return: 检查点数据
        """
        if self.progress_manager:
            return await self.progress_manager.get_checkpoint(keyword, page)
        return None

    async def update_crawl_statistics(self, total_items: int, new_items: int, 
                                    duplicate_items: int, failed_items: int):
        """
        更新爬取统计信息
        :param total_items: 总条目数
        :param new_items: 新增条目数
        :param duplicate_items: 重复条目数
        :param failed_items: 失败条目数
        """
        if self.progress_manager:
            await self.progress_manager.update_statistics(
                total_items, new_items, duplicate_items, failed_items
            )

    async def cleanup_crawl_progress(self):
        """
        清理爬取进度资源
        """
        if self.progress_manager:
            await self.progress_manager.cleanup()

    # ==================== 需要子类实现的抽象方法 ====================

    @abstractmethod
    def extract_item_id(self, content_item: Dict) -> Optional[str]:
        """
        从内容项中提取唯一ID
        :param content_item: 内容项
        :return: 唯一ID
        """
        pass

    @abstractmethod  
    def extract_item_timestamp(self, content_item: Dict) -> Optional[int]:
        """
        从内容项中提取时间戳
        :param content_item: 内容项
        :return: 时间戳（毫秒）
        """
        pass

    async def smart_search_optimization(self, keyword: str, page: int) -> Tuple[bool, Dict[str, Any]]:
        """
        智能搜索优化（可选实现）
        :param keyword: 关键词
        :param page: 页码
        :return: (是否需要调整搜索策略, 调整参数)
        """
        # 默认实现：不调整
        return False, {}

    async def handle_empty_page(self, keyword: str, page: int) -> bool:
        """
        处理空页面情况（可选实现）
        :param keyword: 关键词
        :param page: 页码
        :return: 是否继续爬取
        """
        # 默认实现：检查连续空页面阈值
        import config
        if hasattr(self, '_empty_page_count'):
            self._empty_page_count = getattr(self, '_empty_page_count', 0) + 1
            if self._empty_page_count >= config.EMPTY_PAGE_THRESHOLD:
                return False
        else:
            self._empty_page_count = 1
        return True

    async def process_crawl_batch(self, keyword: str, page: int, items: List[Dict]) -> List[Dict]:
        """
        批量处理爬取数据（可选实现）
        :param keyword: 关键词
        :param page: 页码
        :param items: 原始数据项列表
        :return: 处理后的数据项列表
        """
        # 默认实现：直接返回原始数据
        return items


class AbstractLogin(ABC):
    @abstractmethod
    async def begin(self):
        pass

    @abstractmethod
    async def login_by_qrcode(self):
        pass

    @abstractmethod
    async def login_by_mobile(self):
        pass

    @abstractmethod
    async def login_by_cookies(self):
        pass


class AbstractStore(ABC):
    @abstractmethod
    async def store_content(self, content_item: Dict):
        pass

    @abstractmethod
    async def store_comment(self, comment_item: Dict):
        pass

    # TODO support all platform
    # only xhs is supported, so @abstractmethod is commented
    @abstractmethod
    async def store_creator(self, creator: Dict):
        pass


class AbstractStoreImage(ABC):
    # TODO: support all platform
    # only weibo is supported
    # @abstractmethod
    async def store_image(self, image_content_item: Dict):
        pass


class AbstractApiClient(ABC):
    @abstractmethod
    async def request(self, method, url, **kwargs):
        pass

    @abstractmethod
    async def update_cookies(self, browser_context: BrowserContext):
        pass
