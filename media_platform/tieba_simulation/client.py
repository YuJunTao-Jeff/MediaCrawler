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
import random
from typing import Dict, List, Optional

from playwright.async_api import Page

from base.base_crawler import AbstractApiClient
from tools import utils

from .field import InterceptType, SearchSortType, SearchNoteType
from .help import NetworkInterceptor, UserBehaviorSimulator, parse_post_info_from_response, format_search_params
from .exception import DataFetchError


class TiebaSimulationClient(AbstractApiClient):
    """贴吧模拟客户端"""
    
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
        self._host = "https://tieba.baidu.com"
        
        # 初始化辅助工具
        self.network_interceptor = NetworkInterceptor(playwright_page)
        self.behavior_simulator = UserBehaviorSimulator(playwright_page)
    
    async def get_posts_by_keyword(self,
                                   keyword: str,
                                   page: int = 1,
                                   sort: SearchSortType = SearchSortType.TIME_DESC,
                                   note_type: SearchNoteType = SearchNoteType.ALL) -> Dict:
        """
        通过关键词搜索帖子（使用浏览器自动化+网络拦截）
        """
        utils.logger.info(f"[TiebaSimulationClient] 开始搜索关键词: {keyword}, 页码: {page}")
        
        try:
            # 设置网络拦截
            await self.network_interceptor.setup_interception()
            
            # 构建搜索URL
            search_url = f"{self._host}/f/search/res?isnew=1&kw=&qw={keyword}&rn=10&un=&only_thread=0&sm=1&sd=&ed=&pn={page}"
            
            # 导航到搜索页面
            await self.playwright_page.goto(search_url, wait_until="networkidle")
            
            # 模拟用户阅读行为
            await self.behavior_simulator.simulate_reading_behavior(2, 4)
            await self.behavior_simulator.simulate_mouse_movement()
            
            # 等待网络请求完成并获取拦截数据
            await asyncio.sleep(3)
            intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.SEARCH_POSTS)
            
            if not intercepted_data:
                utils.logger.warning(f"[TiebaSimulationClient] 未拦截到搜索数据: {keyword}")
                return {'posts': []}
            
            # 解析最新的搜索结果
            latest_data = intercepted_data[-1]['data']
            return parse_post_info_from_response(latest_data)
            
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationClient] 搜索失败 {keyword}: {e}")
            raise DataFetchError(f"搜索帖子失败: {e}")
    
    async def get_post_detail(self, post_id: str) -> Dict:
        """
        获取帖子详情（使用浏览器自动化+网络拦截）
        """
        utils.logger.info(f"[TiebaSimulationClient] 获取帖子详情: {post_id}")
        
        try:
            # 设置网络拦截
            await self.network_interceptor.setup_interception()
            
            # 构建帖子详情URL
            post_url = f"{self._host}/p/{post_id}"
            
            # 导航到帖子页面
            await self.playwright_page.goto(post_url, wait_until="networkidle")
            
            # 模拟用户阅读行为
            await self.behavior_simulator.simulate_reading_behavior(3, 6)
            await self.behavior_simulator.simulate_mouse_movement()
            
            # 等待网络请求完成并获取拦截数据
            await asyncio.sleep(2)
            intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.POST_DETAIL)
            
            if not intercepted_data:
                utils.logger.warning(f"[TiebaSimulationClient] 未拦截到帖子详情数据: {post_id}")
                return {}
            
            # 返回最新的详情数据
            latest_data = intercepted_data[-1]['data']
            return self._parse_post_detail(latest_data)
            
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationClient] 获取帖子详情失败 {post_id}: {e}")
            raise DataFetchError(f"获取帖子详情失败: {e}")
    
    async def get_post_comments(self, post_id: str, page: int = 1) -> Dict:
        """
        获取帖子评论（使用浏览器自动化+网络拦截）
        """
        utils.logger.info(f"[TiebaSimulationClient] 获取帖子评论: {post_id}, 页码: {page}")
        
        try:
            # 如果页面不在帖子详情页，先导航过去
            current_url = self.playwright_page.url
            if post_id not in current_url:
                post_url = f"{self._host}/p/{post_id}"
                await self.playwright_page.goto(post_url, wait_until="networkidle")
            
            # 设置网络拦截
            await self.network_interceptor.setup_interception()
            
            # 翻页到指定页码
            await self._navigate_to_comment_page(page)
            
            # 模拟用户阅读行为
            await self.behavior_simulator.simulate_reading_behavior(2, 4)
            
            # 等待网络请求完成并获取拦截数据
            await asyncio.sleep(2)
            intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.POST_COMMENTS)
            
            if not intercepted_data:
                utils.logger.warning(f"[TiebaSimulationClient] 未拦截到评论数据: {post_id}")
                return {"has_more": False, "comments": []}
            
            # 返回最新的评论数据
            latest_data = intercepted_data[-1]['data']
            return self._parse_comments_data(latest_data)
            
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationClient] 获取帖子评论失败 {post_id}: {e}")
            raise DataFetchError(f"获取帖子评论失败: {e}")
    
    async def get_user_info(self, user_id: str) -> Dict:
        """
        获取用户信息（使用浏览器自动化+网络拦截）
        """
        utils.logger.info(f"[TiebaSimulationClient] 获取用户信息: {user_id}")
        
        try:
            # 设置网络拦截
            await self.network_interceptor.setup_interception()
            
            # 构建用户主页URL
            user_url = f"{self._host}/home/main?un={user_id}"
            
            # 导航到用户主页
            await self.playwright_page.goto(user_url, wait_until="networkidle")
            
            # 模拟用户阅读行为
            await self.behavior_simulator.simulate_reading_behavior(2, 4)
            await self.behavior_simulator.simulate_mouse_movement()
            
            # 等待网络请求完成并获取拦截数据
            await asyncio.sleep(2)
            intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.USER_PROFILE)
            
            if not intercepted_data:
                utils.logger.warning(f"[TiebaSimulationClient] 未拦截到用户信息数据: {user_id}")
                return {}
            
            # 返回最新的用户数据
            latest_data = intercepted_data[-1]['data']
            return self._parse_user_info(latest_data)
            
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationClient] 获取用户信息失败 {user_id}: {e}")
            raise DataFetchError(f"获取用户信息失败: {e}")
    
    async def _navigate_to_comment_page(self, page: int) -> None:
        """导航到指定的评论页"""
        try:
            if page > 1:
                # 查找并点击翻页按钮
                page_selectors = [
                    f"a:has-text('{page}')",
                    f".p_pager a[href*='pn={page}']",
                    f".tbui_pagination a:has-text('{page}')",
                ]
                
                clicked = False
                for selector in page_selectors:
                    try:
                        element = await self.playwright_page.query_selector(selector)
                        if element and await element.is_visible():
                            await self.behavior_simulator.simulate_click_with_delay(selector)
                            clicked = True
                            break
                    except:
                        continue
                
                if not clicked:
                    # 如果没有找到翻页按钮，尝试滚动
                    await self.behavior_simulator.simulate_human_scroll(3, (1000, 2000))
                
                await asyncio.sleep(2)
                
        except Exception as e:
            utils.logger.warning(f"[TiebaSimulationClient] 翻页失败: {e}")
    
    def _parse_post_detail(self, data: Dict) -> Dict:
        """解析帖子详情数据"""
        try:
            if 'data' not in data:
                return {}
            
            post_data = data['data']
            return {
                'post_id': post_data.get('thread', {}).get('id', ''),
                'title': post_data.get('thread', {}).get('title', ''),
                'content': post_data.get('thread', {}).get('content', ''),
                'author': post_data.get('thread', {}).get('author', {}).get('name', ''),
                'reply_count': post_data.get('thread', {}).get('reply_num', 0),
                'view_count': post_data.get('thread', {}).get('view_num', 0),
                'publish_time': post_data.get('thread', {}).get('create_time', 0),
                'forum_name': post_data.get('forum', {}).get('name', ''),
            }
            
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationClient] 解析帖子详情失败: {e}")
            return {}
    
    def _parse_comments_data(self, data: Dict) -> Dict:
        """解析评论数据"""
        try:
            if 'data' not in data:
                return {"has_more": False, "comments": []}
            
            comments_data = data['data']
            comments = []
            
            for comment in comments_data.get('post_list', []):
                comment_info = {
                    'id': comment.get('id', ''),
                    'content': comment.get('content', ''),
                    'author': comment.get('author', {}).get('name', ''),
                    'publish_time': comment.get('time', 0),
                    'floor': comment.get('floor', 0),
                }
                comments.append(comment_info)
            
            return {
                "has_more": comments_data.get('has_more', False),
                "comments": comments
            }
            
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationClient] 解析评论数据失败: {e}")
            return {"has_more": False, "comments": []}
    
    def _parse_user_info(self, data: Dict) -> Dict:
        """解析用户信息数据"""
        try:
            if 'data' not in data:
                return {}
            
            user_info = data['data']
            return {
                'user_id': user_info.get('user', {}).get('id', ''),
                'username': user_info.get('user', {}).get('name', ''),
                'nickname': user_info.get('user', {}).get('show_nickname', ''),
                'avatar': user_info.get('user', {}).get('portrait', ''),
                'post_count': user_info.get('user', {}).get('post_num', 0),
                'concern_count': user_info.get('user', {}).get('concern_num', 0),
                'fans_count': user_info.get('user', {}).get('fans_num', 0),
            }
            
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationClient] 解析用户信息失败: {e}")
            return {}
    
    async def update_cookies(self, cookie_dict: Dict[str, str]) -> None:
        """更新Cookie"""
        self.cookie_dict = cookie_dict
        utils.logger.info("[TiebaSimulationClient] Cookie已更新")
    
    async def request(self, method: str, url: str, **kwargs) -> Dict:
        """
        发送HTTP请求（适配抽象方法）
        注意：贴吧模拟爬虫主要通过浏览器自动化获取数据，此方法仅为兼容性
        """
        utils.logger.warning("[TiebaSimulationClient] 贴吧模拟爬虫主要通过浏览器自动化获取数据")
        return {}