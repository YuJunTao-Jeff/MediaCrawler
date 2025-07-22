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
import hashlib
import random
import re
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page, Response

import config
from tools import utils
from model.m_weixin import WeixinArticle
from .field import SOGOU_WEIXIN_SELECTORS, AntiDetectionLevel
from .exception import DataFetchError, ContentExtractionError, CaptchaDetectionError


class NetworkInterceptor:
    """网络拦截器"""
    
    def __init__(self, page: Page):
        self.page = page
        self.intercepted_data = []
    
    async def start_intercept(self) -> None:
        """开始网络拦截"""
        await self.page.route("**/*", self._handle_request)
        utils.logger.info("[NetworkInterceptor] 开始网络拦截")
    
    async def _handle_request(self, route, request) -> None:
        """处理请求"""
        # 对于搜狗微信，我们主要通过DOM解析获取数据，暂不拦截API
        await route.continue_()


class UserBehaviorSimulator:
    """用户行为模拟器"""
    
    def __init__(self, page: Page):
        self.page = page
        self.behavior_config = {
            'scroll_delay_range': (1.0, 3.0),
            'click_delay_range': (0.5, 1.5), 
            'typing_delay_range': (0.1, 0.3),
        }
    
    async def random_scroll(self, scroll_count: int = 3) -> None:
        """随机滚动页面"""
        for i in range(scroll_count):
            # 随机滚动距离
            scroll_distance = random.randint(300, 800)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            
            # 随机等待
            delay = random.uniform(*self.behavior_config['scroll_delay_range'])
            await asyncio.sleep(delay)
            
            utils.logger.debug(f"[UserBehaviorSimulator] 执行滚动 {i+1}/{scroll_count}")
    
    async def random_mouse_move(self) -> None:
        """随机鼠标移动"""
        try:
            # 获取页面尺寸
            viewport = self.page.viewport_size
            if viewport:
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.5))
        except Exception as e:
            utils.logger.warning(f"[UserBehaviorSimulator] 鼠标移动失败: {e}")
    
    async def simulate_reading_behavior(self, duration: float = 3.0) -> None:
        """模拟阅读行为"""
        utils.logger.debug(f"[UserBehaviorSimulator] 模拟阅读行为 {duration}秒")
        
        # 随机滚动和鼠标移动
        scroll_times = random.randint(1, 3)
        for _ in range(scroll_times):
            await self.random_mouse_move()
            await self.random_scroll(1)
            await asyncio.sleep(duration / scroll_times)


class AntiDetectionHelper:
    """反检测助手"""
    
    def __init__(self, page: Page, level: AntiDetectionLevel = AntiDetectionLevel.MEDIUM):
        self.page = page
        self.level = level
        self.last_request_time = 0
        
    async def setup_anti_detection(self) -> None:
        """设置反检测措施"""
        try:
            # 1. 设置随机User-Agent
            await self._randomize_user_agent()
            
            # 2. 移除自动化检测特征
            await self._remove_automation_flags()
            
            # 3. 设置随机视窗大小
            await self._randomize_viewport()
            
            utils.logger.info(f"[AntiDetectionHelper] 反检测设置完成，级别: {self.level.value}")
            
        except Exception as e:
            utils.logger.error(f"[AntiDetectionHelper] 反检测设置失败: {e}")
    
    async def _randomize_user_agent(self) -> None:
        """随机化User-Agent"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ]
        
        selected_ua = random.choice(user_agents)
        await self.page.set_extra_http_headers({"User-Agent": selected_ua})
        utils.logger.debug(f"[AntiDetectionHelper] 设置User-Agent: {selected_ua}")
    
    async def _remove_automation_flags(self) -> None:
        """移除自动化检测标志"""
        await self.page.evaluate("""() => {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 移除Chrome自动化扩展
            delete navigator.__proto__.webdriver;
            
            // 修改plugins长度
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        }""")
        
    async def _randomize_viewport(self) -> None:
        """随机化视窗大小"""
        if self.level in [AntiDetectionLevel.HIGH, AntiDetectionLevel.EXTREME]:
            widths = [1366, 1440, 1536, 1920]
            heights = [768, 900, 1024, 1080]
            
            width = random.choice(widths)
            height = random.choice(heights)
            
            await self.page.set_viewport_size({"width": width, "height": height})
            utils.logger.debug(f"[AntiDetectionHelper] 设置视窗大小: {width}x{height}")
    
    async def smart_delay(self, base_delay: float = 2.0) -> None:
        """智能延迟"""
        current_time = time.time()
        
        # 计算从上次请求以来的时间
        time_since_last = current_time - self.last_request_time
        
        # 根据反检测级别调整延迟
        if self.level == AntiDetectionLevel.LOW:
            min_interval = 3.0
            max_interval = 6.0
        elif self.level == AntiDetectionLevel.MEDIUM:
            min_interval = 6.0
            max_interval = 12.0
        elif self.level == AntiDetectionLevel.HIGH:
            min_interval = 10.0
            max_interval = 20.0
        else:  # EXTREME
            min_interval = 15.0
            max_interval = 30.0
        
        # 如果距离上次请求时间太短，则额外等待
        if time_since_last < min_interval:
            additional_delay = min_interval - time_since_last + random.uniform(0, max_interval - min_interval)
            utils.logger.debug(f"[AntiDetectionHelper] 智能延迟: {additional_delay:.2f}秒")
            await asyncio.sleep(additional_delay)
        
        self.last_request_time = time.time()
    
    async def check_for_captcha(self) -> bool:
        """检查是否出现验证码"""
        try:
            captcha_element = await self.page.query_selector(SOGOU_WEIXIN_SELECTORS['captcha_container'])
            if captcha_element:
                utils.logger.warning("[AntiDetectionHelper] 检测到验证码！")
                raise CaptchaDetectionError("检测到验证码，需要人工处理")
            return False
        except CaptchaDetectionError:
            raise
        except Exception as e:
            utils.logger.error(f"[AntiDetectionHelper] 验证码检查失败: {e}")
            return False


class SogouWeixinParser:
    """搜狗微信内容解析器"""
    
    @staticmethod
    async def parse_search_results(page: Page) -> List[Dict]:
        """解析搜索结果页面"""
        try:
            # 等待搜索结果加载
            await page.wait_for_selector(SOGOU_WEIXIN_SELECTORS['search_results_container'], timeout=10000)
            
            # 获取所有搜索结果项
            article_elements = await page.query_selector_all(SOGOU_WEIXIN_SELECTORS['search_result_item'])
            
            if not article_elements:
                utils.logger.warning("[SogouWeixinParser] 未找到搜索结果")
                return []
            
            articles = []
            for element in article_elements:
                try:
                    article_data = await SogouWeixinParser._parse_single_article(element)
                    if article_data:
                        articles.append(article_data)
                except Exception as e:
                    utils.logger.warning(f"[SogouWeixinParser] 解析单个文章失败: {e}")
                    continue
            
            utils.logger.info(f"[SogouWeixinParser] 解析到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinParser] 解析搜索结果失败: {e}")
            raise DataFetchError(f"解析搜索结果失败: {e}")
    
    @staticmethod
    async def _parse_single_article(element) -> Optional[Dict]:
        """解析单个文章元素"""
        try:
            # 文章标题和链接
            title_element = await element.query_selector(SOGOU_WEIXIN_SELECTORS['article_title'])
            title = await title_element.inner_text() if title_element else ""
            title = re.sub(r'<em>|</em>', '', title).strip()  # 移除搜索高亮标签
            
            article_url = await title_element.get_attribute('href') if title_element else ""
            if article_url:
                # 补全URL
                article_url = urljoin("https://weixin.sogou.com", article_url)
            
            # 文章摘要
            summary_element = await element.query_selector(SOGOU_WEIXIN_SELECTORS['article_summary'])
            summary = await summary_element.inner_text() if summary_element else ""
            summary = re.sub(r'<em>|</em>', '', summary).strip()  # 移除搜索高亮标签
            
            # 公众号名称
            account_element = await element.query_selector(SOGOU_WEIXIN_SELECTORS['account_name'])
            account_name = await account_element.inner_text() if account_element else ""
            
            # 发布时间
            time_element = await element.query_selector(SOGOU_WEIXIN_SELECTORS['publish_time'])
            publish_time = await time_element.inner_text() if time_element else ""
            
            # 解析发布时间戳
            publish_timestamp = SogouWeixinParser._parse_publish_time(publish_time)
            
            # 封面图片
            cover_element = await element.query_selector(SOGOU_WEIXIN_SELECTORS['cover_image'])
            cover_image = await cover_element.get_attribute('src') if cover_element else ""
            if cover_image and cover_image.startswith('//'):
                cover_image = 'https:' + cover_image
            
            # 生成文章ID
            article_id = hashlib.md5(article_url.encode()).hexdigest() if article_url else ""
            
            if not title or not article_url:
                return None
                
            return {
                'article_id': article_id,
                'title': title,
                'summary': summary,
                'account_name': account_name,
                'original_url': article_url,
                'publish_time': publish_time,
                'publish_timestamp': publish_timestamp,
                'cover_image': cover_image,
            }
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinParser] 解析单个文章元素失败: {e}")
            return None
    
    @staticmethod
    def _parse_publish_time(time_str: str) -> int:
        """
        解析发布时间字符串为时间戳
        
        Args:
            time_str: 时间字符串，如 "2天前", "昨天", "今天", "2024-01-01"
            
        Returns:
            Unix时间戳（毫秒）
        """
        if not time_str or time_str.strip() == "":
            return 0
            
        try:
            import datetime
            import re
            
            time_str = time_str.strip()
            now = datetime.datetime.now()
            
            # 处理相对时间格式
            if "分钟前" in time_str:
                minutes = int(re.findall(r'(\d+)分钟前', time_str)[0])
                target_time = now - datetime.timedelta(minutes=minutes)
                
            elif "小时前" in time_str:
                hours = int(re.findall(r'(\d+)小时前', time_str)[0])
                target_time = now - datetime.timedelta(hours=hours)
                
            elif "天前" in time_str:
                days = int(re.findall(r'(\d+)天前', time_str)[0])
                target_time = now - datetime.timedelta(days=days)
                
            elif "昨天" in time_str:
                target_time = now - datetime.timedelta(days=1)
                
            elif "今天" in time_str:
                target_time = now
                
            elif "前天" in time_str:
                target_time = now - datetime.timedelta(days=2)
                
            # 处理绝对时间格式 "2024-01-01" 或 "2024/01/01"
            elif re.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', time_str):
                # 替换分隔符为统一格式
                time_str = re.sub(r'[-/]', '-', time_str)
                target_time = datetime.datetime.strptime(time_str, '%Y-%m-%d')
                
            # 处理带时间的格式 "2024-01-01 12:34"
            elif re.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{1,2}', time_str):
                time_str = re.sub(r'[-/]', '-', time_str)
                target_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                
            else:
                # 无法解析的格式，返回0
                utils.logger.warning(f"[SogouWeixinParser] 无法解析时间格式: {time_str}")
                return 0
            
            # 转换为毫秒时间戳
            timestamp = int(target_time.timestamp() * 1000)
            return timestamp
            
        except Exception as e:
            utils.logger.warning(f"[SogouWeixinParser] 时间解析失败: {time_str}, 错误: {e}")
            return 0
    
    @staticmethod
    async def check_has_next_page(page: Page) -> Tuple[bool, Optional[str]]:
        """检查是否有下一页"""
        try:
            next_element = await page.query_selector(SOGOU_WEIXIN_SELECTORS['next_page_link'])
            if next_element:
                next_url = await next_element.get_attribute('href')
                if next_url:
                    next_url = urljoin("https://weixin.sogou.com", next_url)
                    return True, next_url
            return False, None
        except Exception as e:
            utils.logger.error(f"[SogouWeixinParser] 检查下一页失败: {e}")
            return False, None
    
    @staticmethod  
    async def get_result_count(page: Page) -> int:
        """获取搜索结果总数"""
        try:
            count_element = await page.query_selector(SOGOU_WEIXIN_SELECTORS['result_count'])
            if count_element:
                count_text = await count_element.inner_text()
                # 提取数字，格式如"找到约788条结果"
                match = re.search(r'约(\d+)条', count_text)
                if match:
                    return int(match.group(1))
            return 0
        except Exception as e:
            utils.logger.error(f"[SogouWeixinParser] 获取结果总数失败: {e}")
            return 0