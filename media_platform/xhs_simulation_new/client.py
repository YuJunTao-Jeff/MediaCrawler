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
import json
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from playwright.async_api import Page
from tenacity import retry, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractApiClient
from tools import utils

from .exception import DataFetchError, IPBlockError, NetworkInterceptError
from .field import SearchSortType, SearchNoteType, InterceptType
from .help import NetworkInterceptor, UserBehaviorSimulator, parse_note_info_from_response, format_search_params


class XHSSimulationClient(AbstractApiClient):
    """小红书模拟客户端"""
    
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
        self._host = "https://www.xiaohongshu.com"
        
        # 初始化核心组件
        self.network_interceptor = NetworkInterceptor(playwright_page)
        self.behavior_simulator = UserBehaviorSimulator(playwright_page)
        
        # 错误状态码定义
        self.IP_ERROR_CODE = 300012
        self.NOTE_ABNORMAL_CODE = -510001
        
    async def request(self, method: str, url: str, **kwargs) -> Any:
        """
        模拟客户端不直接发送HTTP请求，而是通过浏览器自动化获取数据
        """
        utils.logger.warning("[XHSSimulationClient] 模拟模式下不支持直接HTTP请求")
        return None
    
    async def get_note_by_keyword(self, 
                                keyword: str, 
                                page: int = 1, 
                                sort: SearchSortType = SearchSortType.GENERAL,
                                note_type: SearchNoteType = SearchNoteType.ALL) -> Dict:
        """
        通过关键词搜索笔记（使用浏览器自动化+网络拦截）
        """
        utils.logger.info(f"[XHSSimulationClient] 开始搜索关键词: {keyword}, 页码: {page}")
        
        try:
            # 设置网络拦截
            await self.network_interceptor.setup_interception()
            
            # 构建搜索URL
            search_url = f"{self._host}/search_result"
            params = {
                'keyword': keyword,
                'type': 'note' if note_type == SearchNoteType.NOTE_NORMAL else 'all'
            }
            full_url = f"{search_url}?{urlencode(params)}"
            
            # 导航到搜索页面
            await self.playwright_page.goto(full_url, wait_until="networkidle")
            
            # 模拟用户行为
            await self.behavior_simulator.simulate_reading_behavior(2, 4)
            await self.behavior_simulator.simulate_human_scroll(3)
            
            # 如果不是第一页，需要模拟翻页
            if page > 1:
                await self._navigate_to_page(page)
            
            # 等待网络请求完成并获取拦截数据
            await asyncio.sleep(3)
            intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.SEARCH_NOTES)
            
            if not intercepted_data:
                utils.logger.warning(f"[XHSSimulationClient] 未拦截到搜索数据: {keyword}")
                return {"has_more": False, "notes": []}
            
            # 解析最新的搜索结果
            latest_data = intercepted_data[-1]['data']
            return parse_note_info_from_response(latest_data)
            
        except Exception as e:
            utils.logger.error(f"[XHSSimulationClient] 搜索失败 {keyword}: {e}")
            raise DataFetchError(f"搜索笔记失败: {e}")
    
    async def get_note_detail(self, note_id: str) -> Dict:
        """
        获取笔记详情（使用浏览器自动化+网络拦截）
        """
        utils.logger.info(f"[XHSSimulationClient] 获取笔记详情: {note_id}")
        
        try:
            # 设置网络拦截
            await self.network_interceptor.setup_interception()
            
            # 构建笔记详情URL
            note_url = f"{self._host}/discovery/item/{note_id}"
            
            # 导航到笔记页面
            await self.playwright_page.goto(note_url, wait_until="networkidle")
            
            # 模拟用户阅读行为
            await self.behavior_simulator.simulate_reading_behavior(3, 6)
            await self.behavior_simulator.simulate_mouse_movement()
            
            # 等待网络请求完成并获取拦截数据
            await asyncio.sleep(2)
            intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.NOTE_DETAIL)
            
            if not intercepted_data:
                utils.logger.warning(f"[XHSSimulationClient] 未拦截到笔记详情数据: {note_id}")
                return {}
            
            # 返回最新的详情数据
            latest_data = intercepted_data[-1]['data']
            return self._parse_note_detail(latest_data)
            
        except Exception as e:
            utils.logger.error(f"[XHSSimulationClient] 获取笔记详情失败 {note_id}: {e}")
            raise DataFetchError(f"获取笔记详情失败: {e}")
    
    async def get_note_comments(self, note_id: str, cursor: str = "") -> Dict:
        """
        获取笔记评论（使用浏览器自动化+网络拦截）
        """
        utils.logger.info(f"[XHSSimulationClient] 获取笔记评论: {note_id}")
        
        try:
            # 如果页面不在笔记详情页，先导航过去
            current_url = self.playwright_page.url
            if note_id not in current_url:
                note_url = f"{self._host}/discovery/item/{note_id}"
                await self.playwright_page.goto(note_url, wait_until="networkidle")
            
            # 设置网络拦截
            await self.network_interceptor.setup_interception()
            
            # 滚动到评论区域
            comments_selector = ".comments-container, .comment-list, [class*='comment']"
            try:
                await self.playwright_page.scroll_into_view_if_needed(comments_selector)
            except:
                # 如果找不到评论区域，尝试滚动页面
                await self.behavior_simulator.simulate_human_scroll(2)
            
            # 模拟用户查看评论的行为
            await self.behavior_simulator.simulate_reading_behavior(2, 4)
            
            # 如果有cursor，说明需要加载更多评论
            if cursor:
                load_more_selector = ".load-more, .more-comments, [class*='load-more']"
                try:
                    await self.behavior_simulator.simulate_click_with_delay(load_more_selector)
                except:
                    utils.logger.debug("[XHSSimulationClient] 未找到加载更多按钮")
            
            # 等待网络请求完成并获取拦截数据
            await asyncio.sleep(2)
            intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.NOTE_COMMENTS)
            
            if not intercepted_data:
                utils.logger.warning(f"[XHSSimulationClient] 未拦截到评论数据: {note_id}")
                return {"has_more": False, "comments": []}
            
            # 返回最新的评论数据
            latest_data = intercepted_data[-1]['data']
            return self._parse_comments_data(latest_data)
            
        except Exception as e:
            utils.logger.error(f"[XHSSimulationClient] 获取评论失败 {note_id}: {e}")
            raise DataFetchError(f"获取评论失败: {e}")
    
    async def get_creator_info(self, user_id: str) -> Dict:
        """
        获取创作者信息（使用浏览器自动化+网络拦截）
        """
        utils.logger.info(f"[XHSSimulationClient] 获取创作者信息: {user_id}")
        
        try:
            # 设置网络拦截
            await self.network_interceptor.setup_interception()
            
            # 构建用户主页URL
            user_url = f"{self._host}/user/profile/{user_id}"
            
            # 导航到用户主页
            await self.playwright_page.goto(user_url, wait_until="networkidle")
            
            # 模拟用户浏览行为
            await self.behavior_simulator.simulate_reading_behavior(2, 4)
            await self.behavior_simulator.simulate_human_scroll(2)
            
            # 等待网络请求完成并获取拦截数据
            await asyncio.sleep(2)
            intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.USER_PROFILE)
            
            if not intercepted_data:
                utils.logger.warning(f"[XHSSimulationClient] 未拦截到用户信息数据: {user_id}")
                return {}
            
            # 返回最新的用户数据
            latest_data = intercepted_data[-1]['data']
            return self._parse_user_info(latest_data)
            
        except Exception as e:
            utils.logger.error(f"[XHSSimulationClient] 获取创作者信息失败 {user_id}: {e}")
            raise DataFetchError(f"获取创作者信息失败: {e}")
    
    async def _navigate_to_page(self, page: int) -> None:
        """导航到指定页面"""
        try:
            for i in range(page - 1):
                # 滚动到页面底部触发加载更多
                await self.behavior_simulator.simulate_human_scroll(5, 1000)
                await asyncio.sleep(2)
                
                # 查找并点击下一页或加载更多按钮
                next_selectors = [
                    ".next-page",
                    ".load-more",
                    ".more-content",
                    "[class*='next']",
                    "[class*='more']"
                ]
                
                clicked = False
                for selector in next_selectors:
                    try:
                        element = await self.playwright_page.query_selector(selector)
                        if element and await element.is_visible():
                            await self.behavior_simulator.simulate_click_with_delay(selector)
                            clicked = True
                            break
                    except:
                        continue
                
                if not clicked:
                    # 如果没有找到按钮，继续滚动可能会触发无限滚动
                    await self.behavior_simulator.simulate_human_scroll(3, 800)
                
                await asyncio.sleep(3)
                
        except Exception as e:
            utils.logger.warning(f"[XHSSimulationClient] 翻页失败: {e}")
    
    def _parse_note_detail(self, data: Dict) -> Dict:
        """解析笔记详情数据"""
        try:
            if 'data' not in data:
                return {}
            
            items = data['data'].get('items', [])
            if not items:
                return {}
            
            note_info = items[0].get('note_card', {})
            return {
                'note_id': note_info.get('note_id', ''),
                'title': note_info.get('display_title', ''),
                'desc': note_info.get('desc', ''),
                'type': note_info.get('type', ''),
                'liked_count': note_info.get('interact_info', {}).get('liked_count', 0),
                'collected_count': note_info.get('interact_info', {}).get('collected_count', 0),
                'comment_count': note_info.get('interact_info', {}).get('comment_count', 0),
                'share_count': note_info.get('interact_info', {}).get('share_count', 0),
                'time': note_info.get('time', 0),
                'last_update_time': note_info.get('last_update_time', 0),
                'user_info': {
                    'user_id': note_info.get('user', {}).get('user_id', ''),
                    'nickname': note_info.get('user', {}).get('nickname', ''),
                    'avatar': note_info.get('user', {}).get('avatar', ''),
                },
                'image_list': [img.get('url_default', '') for img in note_info.get('image_list', [])],
                'video_url': note_info.get('video', {}).get('media', {}).get('stream', {}).get('h264', [{}])[0].get('master_url', '') if note_info.get('video') else '',
                'tag_list': [tag.get('name', '') for tag in note_info.get('tag_list', [])],
            }
            
        except Exception as e:
            utils.logger.error(f"[XHSSimulationClient] 解析笔记详情失败: {e}")
            return {}
    
    def _parse_comments_data(self, data: Dict) -> Dict:
        """解析评论数据"""
        try:
            if 'data' not in data:
                return {"has_more": False, "comments": []}
            
            comments_data = data['data']
            comments = []
            
            for comment in comments_data.get('comments', []):
                comment_info = {
                    'id': comment.get('id', ''),
                    'content': comment.get('content', ''),
                    'create_time': comment.get('create_time', 0),
                    'like_count': comment.get('like_count', 0),
                    'user_info': {
                        'user_id': comment.get('user_info', {}).get('user_id', ''),
                        'nickname': comment.get('user_info', {}).get('nickname', ''),
                        'avatar': comment.get('user_info', {}).get('image', ''),
                    },
                    'sub_comments': []
                }
                
                # 解析子评论
                for sub_comment in comment.get('sub_comments', []):
                    sub_comment_info = {
                        'id': sub_comment.get('id', ''),
                        'content': sub_comment.get('content', ''),
                        'create_time': sub_comment.get('create_time', 0),
                        'like_count': sub_comment.get('like_count', 0),
                        'user_info': {
                            'user_id': sub_comment.get('user_info', {}).get('user_id', ''),
                            'nickname': sub_comment.get('user_info', {}).get('nickname', ''),
                            'avatar': sub_comment.get('user_info', {}).get('image', ''),
                        }
                    }
                    comment_info['sub_comments'].append(sub_comment_info)
                
                comments.append(comment_info)
            
            return {
                'comments': comments,
                'has_more': comments_data.get('has_more', False),
                'cursor': comments_data.get('cursor', '')
            }
            
        except Exception as e:
            utils.logger.error(f"[XHSSimulationClient] 解析评论数据失败: {e}")
            return {"has_more": False, "comments": []}
    
    def _parse_user_info(self, data: Dict) -> Dict:
        """解析用户信息数据"""
        try:
            if 'data' not in data:
                return {}
            
            user_info = data['data']
            return {
                'user_id': user_info.get('user_id', ''),
                'nickname': user_info.get('nickname', ''),
                'avatar': user_info.get('avatar', ''),
                'desc': user_info.get('desc', ''),
                'gender': user_info.get('gender', ''),
                'follows': user_info.get('follows', 0),
                'fans': user_info.get('fans', 0),
                'interaction': user_info.get('interaction', 0),
                'note_count': user_info.get('note_count', 0),
            }
            
        except Exception as e:
            utils.logger.error(f"[XHSSimulationClient] 解析用户信息失败: {e}")
            return {}
    
    async def update_cookies(self, cookie_dict: Dict[str, str]) -> None:
        """更新Cookie"""
        self.cookie_dict = cookie_dict
        utils.logger.info("[XHSSimulationClient] Cookie已更新")