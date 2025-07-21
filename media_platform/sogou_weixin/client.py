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
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

from playwright.async_api import Page

from base.base_crawler import AbstractApiClient
from tools import utils
import config
from model.m_weixin import WeixinArticle
from var import source_keyword_var

from .field import SearchType, SOGOU_WEIXIN_URLS, SOGOU_WEIXIN_SELECTORS
from .help import NetworkInterceptor, UserBehaviorSimulator, AntiDetectionHelper, SogouWeixinParser
from .exception import DataFetchError, CaptchaDetectionError


class SogouWeixinClient(AbstractApiClient):
    """搜狗微信客户端"""
    
    def __init__(self,
                 timeout: int = 30,
                 proxies: Optional[Dict] = None,
                 *,
                 playwright_page: Page,
                 cookie_dict: Dict[str, str]):
        
        self.timeout = timeout
        self.proxies = proxies
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self._host = "https://weixin.sogou.com"
        
        # 初始化辅助工具
        self.network_interceptor = NetworkInterceptor(playwright_page)
        self.behavior_simulator = UserBehaviorSimulator(playwright_page)
        self.anti_detection_helper = AntiDetectionHelper(playwright_page)
        
        # 搜索配置
        self.search_config = {
            'max_pages_per_session': getattr(config, 'SOGOU_WEIXIN_MAX_PAGES_PER_SESSION', 20),
            'request_delay_range': getattr(config, 'SOGOU_WEIXIN_REQUEST_DELAY', (8, 12)),
            'extract_original_content': getattr(config, 'SOGOU_WEIXIN_EXTRACT_ORIGINAL_CONTENT', True),
        }
    
    async def search_articles(self,
                            keyword: str,
                            max_pages: int = 10) -> List[WeixinArticle]:
        """
        搜索微信公众号文章
        
        Args:
            keyword: 搜索关键词
            max_pages: 最大页数
            
        Returns:
            文章列表
        """
        utils.logger.info(f"[SogouWeixinClient] 开始搜索文章，关键词: {keyword}")
        
        try:
            # 设置反检测
            await self.anti_detection_helper.setup_anti_detection()
            
            all_articles = []
            current_page = 1
            
            while current_page <= max_pages and current_page <= self.search_config['max_pages_per_session']:
                utils.logger.info(f"[SogouWeixinClient] 搜索第 {current_page}/{max_pages} 页")
                
                # 智能延迟
                if current_page > 1:
                    await self.anti_detection_helper.smart_delay()
                
                # 构建搜索URL
                search_url = SOGOU_WEIXIN_URLS['article_search'].format(
                    keyword=quote(keyword),
                    page=current_page
                )
                
                # 访问搜索页面
                await self.playwright_page.goto(search_url, wait_until="networkidle", timeout=self.timeout * 1000)
                
                # 检查验证码
                await self.anti_detection_helper.check_for_captcha()
                
                # 模拟用户行为
                await self.behavior_simulator.simulate_reading_behavior(2.0)
                
                # 解析搜索结果
                articles_data = await SogouWeixinParser.parse_search_results(self.playwright_page)
                
                if not articles_data:
                    utils.logger.warning(f"[SogouWeixinClient] 第 {current_page} 页没有找到文章")
                    break
                
                # 转换为WeixinArticle对象
                for article_data in articles_data:
                    try:
                        # 添加搜索关键词
                        article_data['source_keyword'] = keyword
                        
                        weixin_article = WeixinArticle(**article_data)
                        all_articles.append(weixin_article)
                        
                    except Exception as e:
                        utils.logger.warning(f"[SogouWeixinClient] 创建WeixinArticle对象失败: {e}")
                        continue
                
                utils.logger.info(f"[SogouWeixinClient] 第 {current_page} 页获取到 {len(articles_data)} 篇文章")
                
                # 检查是否有下一页
                has_next, next_url = await SogouWeixinParser.check_has_next_page(self.playwright_page)
                if not has_next:
                    utils.logger.info(f"[SogouWeixinClient] 已达到最后一页")
                    break
                
                current_page += 1
            
            utils.logger.info(f"[SogouWeixinClient] 搜索完成，共获取 {len(all_articles)} 篇文章")
            return all_articles
            
        except CaptchaDetectionError:
            utils.logger.error(f"[SogouWeixinClient] 遇到验证码，停止搜索")
            return all_articles  # 返回已获取的文章
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinClient] 搜索文章失败: {e}")
            raise DataFetchError(f"搜索文章失败: {e}")
    
    async def search_accounts(self,
                            keyword: str,
                            max_pages: int = 5) -> List[Dict]:
        """
        搜索微信公众号
        
        Args:
            keyword: 搜索关键词
            max_pages: 最大页数
            
        Returns:
            公众号信息列表
        """
        utils.logger.info(f"[SogouWeixinClient] 开始搜索公众号，关键词: {keyword}")
        
        try:
            # 设置反检测
            await self.anti_detection_helper.setup_anti_detection()
            
            all_accounts = []
            current_page = 1
            
            while current_page <= max_pages:
                # 智能延迟
                if current_page > 1:
                    await self.anti_detection_helper.smart_delay()
                
                # 构建搜索URL
                search_url = SOGOU_WEIXIN_URLS['account_search'].format(
                    keyword=quote(keyword),
                    page=current_page
                )
                
                # 访问搜索页面
                await self.playwright_page.goto(search_url, wait_until="networkidle", timeout=self.timeout * 1000)
                
                # 检查验证码
                await self.anti_detection_helper.check_for_captcha()
                
                # 模拟用户行为
                await self.behavior_simulator.simulate_reading_behavior(2.0)
                
                # 解析公众号信息 (这里可以根据实际需要实现)
                # 暂时返回空列表，后续可以扩展
                
                current_page += 1
            
            return all_accounts
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinClient] 搜索公众号失败: {e}")
            raise DataFetchError(f"搜索公众号失败: {e}")
    
    async def extract_article_content(self, article_url: str) -> Optional[str]:
        """
        提取文章正文内容
        
        Args:
            article_url: 文章链接
            
        Returns:
            文章正文内容
        """
        if not self.search_config['extract_original_content']:
            return None
            
        try:
            utils.logger.debug(f"[SogouWeixinClient] 提取文章内容: {article_url}")
            
            # 智能延迟
            await self.anti_detection_helper.smart_delay()
            
            # 访问文章页面
            await self.playwright_page.goto(article_url, wait_until="networkidle", timeout=self.timeout * 1000)
            
            # 等待内容加载
            await asyncio.sleep(2)
            
            # 提取文章正文 (微信文章通常在 #js_content 或 .rich_media_content 中)
            content_selectors = [
                '#js_content',
                '.rich_media_content', 
                '.share_article_content',
                '[data-role="content"]'
            ]
            
            content = ""
            for selector in content_selectors:
                try:
                    element = await self.playwright_page.query_selector(selector)
                    if element:
                        content = await element.inner_text()
                        if content.strip():
                            break
                except:
                    continue
            
            if content:
                utils.logger.debug(f"[SogouWeixinClient] 成功提取文章内容，长度: {len(content)}")
                return content.strip()
            else:
                utils.logger.warning(f"[SogouWeixinClient] 未能提取文章内容: {article_url}")
                return None
                
        except Exception as e:
            utils.logger.warning(f"[SogouWeixinClient] 提取文章内容失败: {e}")
            return None
    
    async def get_total_result_count(self, keyword: str) -> int:
        """
        获取搜索结果总数
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            结果总数
        """
        try:
            search_url = SOGOU_WEIXIN_URLS['article_search'].format(
                keyword=quote(keyword),
                page=1
            )
            
            await self.playwright_page.goto(search_url, wait_until="networkidle")
            return await SogouWeixinParser.get_result_count(self.playwright_page)
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinClient] 获取结果总数失败: {e}")
            return 0
    
    # ==================== 抽象方法实现 ====================
    
    async def request(self, method: str, url: str, **kwargs):
        """HTTP请求方法"""
        # 搜狗微信主要使用浏览器自动化，不需要直接HTTP请求
        # 这里提供基础实现以满足抽象类要求
        import httpx
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                proxies=self.proxies,
                cookies=self.cookie_dict
            ) as client:
                response = await client.request(method, url, **kwargs)
                return response
        except Exception as e:
            utils.logger.error(f"[SogouWeixinClient] HTTP请求失败: {e}")
            raise
    
    async def update_cookies(self, browser_context):
        """更新Cookie"""
        try:
            cookie_list = await browser_context.cookies()
            self.cookie_dict = {cookie['name']: cookie['value'] for cookie in cookie_list}
            utils.logger.debug("[SogouWeixinClient] Cookie已更新")
        except Exception as e:
            utils.logger.warning(f"[SogouWeixinClient] 更新Cookie失败: {e}")