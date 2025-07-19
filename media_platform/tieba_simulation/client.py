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
from typing import Dict, List, Optional, Tuple

from playwright.async_api import Page

from base.base_crawler import AbstractApiClient
from tools import utils
import config

from .field import InterceptType, SearchSortType, SearchNoteType
from .help import NetworkInterceptor, UserBehaviorSimulator, parse_post_info_from_response
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
        # 标记暂未使用的参数
        _ = sort, note_type
        utils.logger.info(f"[TiebaSimulationClient] 开始搜索关键词: {keyword}, 页码: {page}")
        
        try:
            # 设置网络拦截
            await self.network_interceptor.setup_interception()
            
            # 构建搜索URL - 使用URL编码确保中文关键词正确传递
            import urllib.parse
            encoded_keyword = urllib.parse.quote(keyword.encode('gbk'))
            search_url = f"{self._host}/f/search/res?isnew=1&kw=&qw={encoded_keyword}&rn=10&un=&only_thread=1&sm=1&sd=&ed=&pn={page}"
            utils.logger.info(f"[TiebaSimulationClient] 搜索URL: {search_url}")
            
            # 导航到搜索页面，使用渐进式加载策略
            search_timeout = getattr(config, 'TIEBA_SEARCH_PAGE_TIMEOUT', 20000)
            try:
                await self.playwright_page.goto(search_url, wait_until="domcontentloaded", timeout=search_timeout)
                # 等待页面内容加载
                await asyncio.sleep(1)
            except Exception as e:
                if "timeout" in str(e).lower():
                    utils.logger.debug(f"[TiebaSimulationClient] DOM加载超时，尝试基础加载策略")
                    try:
                        page_timeout = getattr(config, 'TIEBA_PAGE_LOAD_TIMEOUT', 30000)
                        await self.playwright_page.goto(search_url, wait_until="load", timeout=page_timeout)
                    except Exception as e2:
                        if "timeout" in str(e2).lower():
                            utils.logger.debug(f"[TiebaSimulationClient] 基础加载也超时，使用兜底策略")
                            await self.playwright_page.goto(search_url, timeout=page_timeout)
                        else:
                            raise e2
                else:
                    raise e
            
            # 模拟用户阅读行为
            await self.behavior_simulator.simulate_reading_behavior(2, 4)
            await self.behavior_simulator.simulate_mouse_movement()
            
            # 使用自适应网络等待
            await self._adaptive_network_wait_for_search()
            
            # 获取拦截数据
            intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.SEARCH_POSTS)
            
            if not intercepted_data:
                # 如果没有拦截到数据，尝试从页面直接提取
                utils.logger.info("[TiebaSimulationClient] 未拦截到网络数据，开始页面直接提取")
                intercepted_data = await self._extract_data_from_page()
            
            # 检查是否拦截到有效的搜索数据
            valid_search_data = []
            if isinstance(intercepted_data, list) and intercepted_data:
                utils.logger.info(f"[TiebaSimulationClient] 获取到网络拦截数据，数量: {len(intercepted_data)}")
                
                # 过滤出真正的搜索结果数据
                for item in intercepted_data:
                    url = item.get('url', '')
                    if '/f/search/res' in url and item.get('data'):
                        valid_search_data.append(item)
                        utils.logger.info(f"[TiebaSimulationClient] 找到有效搜索数据: {url[:100]}")
            
            if valid_search_data:
                # 使用最新的搜索数据
                latest_data = valid_search_data[-1].get('data', {})
                parsed_result = parse_post_info_from_response(latest_data)
                utils.logger.info(f"[TiebaSimulationClient] 网络解析结果: {parsed_result}")
                return parsed_result
            else:
                utils.logger.warning(f"[TiebaSimulationClient] 未拦截到有效搜索数据，尝试直接解析页面: {keyword}")
                # 如果网络拦截失败，尝试直接从页面解析
                return await self._parse_page_content()
            
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationClient] 搜索失败 {keyword}: {e}")
            # 尝试直接解析页面作为备选方案
            try:
                return await self._parse_page_content()
            except:
                raise DataFetchError(f"搜索帖子失败: {e}")
    
    async def _extract_post_detail_from_page(self) -> Dict:
        """从帖子详情页面提取内容"""
        try:
            # 等待页面加载完成
            await self.playwright_page.wait_for_selector(".d_post_content, .l_post", timeout=5000)
            
            post_detail = {}
            
            # 提取帖子正文内容
            content_selectors = [
                ".d_post_content",           # 主要内容区域
                ".l_post .d_post_content",   # 楼层内容区域 
                ".post_content",             # 帖子内容
                ".content",                  # 通用内容选择器
            ]
            
            for selector in content_selectors:
                try:
                    content_element = await self.playwright_page.query_selector(selector)
                    if content_element:
                        content_text = await content_element.text_content()
                        if content_text and content_text.strip():
                            post_detail['content'] = content_text.strip()
                            utils.logger.debug(f"[TiebaSimulationClient] 使用选择器 {selector} 提取帖子正文")
                            break
                except Exception:
                    continue
            
            # 提取作者信息
            author_selectors = [
                ".d_name a",                 # 作者名称链接
                ".username",                 # 用户名
                ".author",                   # 作者
                ".p_author",                 # 帖子作者
            ]
            
            for selector in author_selectors:
                try:
                    author_element = await self.playwright_page.query_selector(selector)
                    if author_element:
                        author_text = await author_element.text_content()
                        if author_text and author_text.strip():
                            post_detail['author'] = author_text.strip()
                            break
                except Exception:
                    continue
            
            utils.logger.info(f"[TiebaSimulationClient] 页面解析提取帖子详情完成")
            return post_detail
            
        except Exception as e:
            utils.logger.warning(f"[TiebaSimulationClient] 页面解析帖子详情失败: {e}")
            return {}
    
    async def _extract_post_comments_from_page(self) -> Dict:
        """从帖子页面提取楼层评论"""
        try:
            # 等待帖子列表加载
            await self.playwright_page.wait_for_selector(".l_post", timeout=5000)
            
            comments = []
            # 获取所有楼层（除了1楼主楼）
            post_elements = await self.playwright_page.query_selector_all(".l_post")
            
            utils.logger.info(f"[TiebaSimulationClient] 找到 {len(post_elements)} 个楼层")
            
            for i, element in enumerate(post_elements):
                try:
                    # 跳过1楼（主楼）
                    if i == 0:
                        continue
                        
                    # 提取楼层作者
                    author_element = await element.query_selector(".p_author_name")
                    author = ""
                    if author_element:
                        author = await author_element.text_content()
                        author = author.strip() if author else ""
                    
                    # 提取楼层内容
                    content_element = await element.query_selector(".d_post_content")
                    if content_element:
                        content = await content_element.text_content()
                        if content and content.strip():
                            # 提取楼层号
                            floor_element = await element.query_selector(".tail-info")
                            floor_num = i + 1  # 默认按顺序
                            if floor_element:
                                floor_text = await floor_element.text_content()
                                if floor_text and "楼" in floor_text:
                                    try:
                                        floor_num = int(floor_text.replace("楼", "").strip())
                                    except:
                                        pass
                            
                            comments.append({
                                'content': content.strip(),
                                'comment_id': f"floor_{floor_num}",
                                'author': author,
                                'floor_num': floor_num,
                            })
                            
                            # 限制评论数量
                            if len(comments) >= 20:
                                break
                                
                except Exception as e:
                    utils.logger.debug(f"[TiebaSimulationClient] 解析第{i}楼失败: {e}")
                    continue
            
            utils.logger.info(f"[TiebaSimulationClient] 页面解析获得 {len(comments)} 个楼层评论")
            return {'comments': comments, 'has_more': len(comments) >= 20}
            
        except Exception as e:
            utils.logger.warning(f"[TiebaSimulationClient] 页面解析楼层评论失败: {e}")
            return {'comments': [], 'has_more': False}
    
    async def get_post_detail(self, post_id: str) -> Dict:
        """
        获取帖子详情（使用浏览器自动化+网络拦截），支持渐进式加载和智能重试
        """
        utils.logger.info(f"[TiebaSimulationClient] 获取帖子详情: {post_id}")
        
        # 使用智能重试机制
        max_retries = getattr(config, 'TIEBA_MAX_RETRY_COUNT', 3)
        
        for attempt in range(max_retries):
            try:
                result = await self._get_post_detail_with_progressive_loading(post_id)
                if result:  # 成功获取到数据
                    return result
                
            except Exception as e:
                is_timeout_error = "timeout" in str(e).lower() or "exceeded" in str(e).lower()
                
                if attempt < max_retries - 1:  # 不是最后一次尝试
                    if is_timeout_error:
                        # 对超时错误使用递增延迟重试
                        delay_base = getattr(config, 'TIEBA_RETRY_DELAY_BASE', 2)
                        delay_increment = getattr(config, 'TIEBA_RETRY_DELAY_INCREMENT', 2)
                        delay = delay_base + (attempt * delay_increment)
                        
                        utils.logger.warning(f"[TiebaSimulationClient] 获取帖子详情超时 {post_id} (尝试 {attempt + 1}/{max_retries})，{delay}秒后重试")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # 非超时错误，立即重试
                        utils.logger.warning(f"[TiebaSimulationClient] 获取帖子详情失败 {post_id} (尝试 {attempt + 1}/{max_retries}): {e}")
                        await asyncio.sleep(1)
                        continue
                else:
                    # 最后一次尝试也失败了
                    utils.logger.error(f"[TiebaSimulationClient] 获取帖子详情最终失败 {post_id}: {e}")
                    raise DataFetchError(f"获取帖子详情失败: {e}")
        
        # 如果所有重试都没有返回结果，尝试页面解析作为最后手段
        utils.logger.warning(f"[TiebaSimulationClient] 所有重试失败，尝试页面解析: {post_id}")
        try:
            return await self._extract_post_detail_from_page()
        except Exception as e:
            raise DataFetchError(f"获取帖子详情完全失败: {e}")
    
    async def _get_post_detail_with_progressive_loading(self, post_id: str) -> Dict:
        """
        使用渐进式加载策略获取帖子详情
        """
        # 设置网络拦截
        await self.network_interceptor.setup_interception()
        
        # 构建帖子详情URL
        post_url = f"{self._host}/p/{post_id}"
        
        # 渐进式加载策略：从宽松到严格
        loading_strategies = [
            ("domcontentloaded", getattr(config, 'TIEBA_DOM_LOAD_TIMEOUT', 15000)),
            ("load", getattr(config, 'TIEBA_PAGE_LOAD_TIMEOUT', 30000)),
            ("networkidle", getattr(config, 'TIEBA_NETWORK_IDLE_TIMEOUT', 30000)),
            (None, getattr(config, 'TIEBA_DETAIL_PAGE_TIMEOUT', 40000))  # 最后兜底：无等待条件
        ]
        
        for strategy_name, timeout_ms in loading_strategies:
            try:
                utils.logger.debug(f"[TiebaSimulationClient] 尝试加载策略: {strategy_name or 'none'}, 超时: {timeout_ms}ms")
                
                if strategy_name:
                    await self.playwright_page.goto(post_url, wait_until=strategy_name, timeout=timeout_ms)
                else:
                    # 最后的兜底策略：没有等待条件，仅超时控制
                    await self.playwright_page.goto(post_url, timeout=timeout_ms)
                
                # 页面加载成功，等待页面就绪
                if await self._wait_for_page_ready():
                    break
                    
            except Exception as e:
                if "timeout" in str(e).lower() or "exceeded" in str(e).lower():
                    utils.logger.debug(f"[TiebaSimulationClient] 加载策略 {strategy_name or 'none'} 超时，尝试下一个策略")
                    continue
                else:
                    # 非超时错误，立即抛出
                    raise e
        else:
            # 所有策略都失败了
            raise DataFetchError(f"所有加载策略都失败了: {post_id}")
        
        # 模拟用户阅读行为
        await self.behavior_simulator.simulate_reading_behavior(2, 4)  # 减少等待时间
        await self.behavior_simulator.simulate_mouse_movement()
        
        # 自适应等待网络请求完成
        await self._adaptive_network_wait()
        
        # 获取拦截数据
        intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.POST_DETAIL)
        
        if intercepted_data:
            # 返回最新的详情数据
            latest_data = intercepted_data[-1]['data']
            return self._parse_post_detail(latest_data)
        else:
            # 如果没有拦截到数据，尝试页面解析
            utils.logger.info(f"[TiebaSimulationClient] 未拦截到网络数据，尝试页面解析: {post_id}")
            return await self._extract_post_detail_from_page()
    
    async def _wait_for_page_ready(self, timeout_ms: int = 5000) -> bool:
        """
        等待页面就绪，检查关键元素是否加载
        """
        ready_selectors = [
            ".d_post_content",        # 帖子内容
            ".core_reply_wrapper",    # 回复区域
            ".j_thread_list",         # 线程列表
            ".post_content",          # 帖子内容（备选）
        ]
        
        try:
            # 等待任意一个关键元素加载完成
            for selector in ready_selectors:
                try:
                    await self.playwright_page.wait_for_selector(selector, timeout=timeout_ms)
                    utils.logger.debug(f"[TiebaSimulationClient] 页面就绪，检测到元素: {selector}")
                    return True
                except:
                    continue
            
            # 如果没有找到关键元素，检查页面是否至少有基本内容
            page_title = await self.playwright_page.title()
            if page_title and "贴吧" in page_title:
                utils.logger.debug(f"[TiebaSimulationClient] 页面标题正常: {page_title}")
                return True
            
            return False
            
        except Exception as e:
            utils.logger.debug(f"[TiebaSimulationClient] 页面就绪检查失败: {e}")
            return False
    
    async def _adaptive_network_wait(self) -> None:
        """
        自适应网络等待，根据是否拦截到数据动态调整等待时间
        """
        if not getattr(config, 'TIEBA_ADAPTIVE_WAIT_ENABLED', True):
            # 如果没有启用自适应等待，使用固定等待时间
            await asyncio.sleep(2)
            return
        
        base_wait = getattr(config, 'TIEBA_NETWORK_WAIT_BASE', 2)
        max_wait = getattr(config, 'TIEBA_NETWORK_WAIT_MAX', 8)
        
        # 渐进式等待，检查是否有数据拦截
        for wait_time in [base_wait, base_wait * 2, max_wait]:
            await asyncio.sleep(wait_time)
            
            # 检查是否拦截到了数据
            intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.POST_DETAIL)
            if intercepted_data:
                utils.logger.debug(f"[TiebaSimulationClient] 在等待{wait_time}秒后检测到网络数据")
                break
                
            utils.logger.debug(f"[TiebaSimulationClient] 等待{wait_time}秒后仍无网络数据，继续等待")
        else:
            utils.logger.debug(f"[TiebaSimulationClient] 网络等待结束，总计等待{sum([base_wait, base_wait * 2, max_wait])}秒")
    
    async def _adaptive_network_wait_for_search(self) -> None:
        """
        搜索专用的自适应网络等待，搜索页面通常响应更快
        """
        if not getattr(config, 'TIEBA_ADAPTIVE_WAIT_ENABLED', True):
            # 如果没有启用自适应等待，使用固定等待时间
            await asyncio.sleep(1)
            return
        
        base_wait = 1  # 搜索页面等待时间更短
        max_wait = 5
        
        # 渐进式等待，检查是否有数据拦截
        for wait_time in [base_wait, 2, max_wait]:
            await asyncio.sleep(wait_time)
            
            # 检查是否拦截到了数据
            intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.SEARCH_POSTS)
            if intercepted_data:
                utils.logger.debug(f"[TiebaSimulationClient] 搜索在等待{wait_time}秒后检测到网络数据")
                break
                
            utils.logger.debug(f"[TiebaSimulationClient] 搜索等待{wait_time}秒后仍无网络数据，继续等待")
        else:
            utils.logger.debug(f"[TiebaSimulationClient] 搜索网络等待结束，总计等待{sum([base_wait, 2, max_wait])}秒")
    
    async def get_post_comments(self, post_id: str, page: int = 1) -> Dict:
        """
        获取帖子评论（使用浏览器自动化+网络拦截），支持渐进式加载和智能重试
        """
        utils.logger.info(f"[TiebaSimulationClient] 获取帖子评论: {post_id}, 页码: {page}")
        
        # 使用智能重试机制
        max_retries = getattr(config, 'TIEBA_MAX_RETRY_COUNT', 3)
        
        for attempt in range(max_retries):
            try:
                result = await self._get_post_comments_with_progressive_loading(post_id, page)
                if result:  # 成功获取到数据
                    return result
                    
            except Exception as e:
                is_timeout_error = "timeout" in str(e).lower() or "exceeded" in str(e).lower()
                
                if attempt < max_retries - 1:  # 不是最后一次尝试
                    if is_timeout_error:
                        # 对超时错误使用递增延迟重试
                        delay_base = getattr(config, 'TIEBA_RETRY_DELAY_BASE', 2)
                        delay_increment = getattr(config, 'TIEBA_RETRY_DELAY_INCREMENT', 2)
                        delay = delay_base + (attempt * delay_increment)
                        
                        utils.logger.warning(f"[TiebaSimulationClient] 获取帖子评论超时 {post_id} (尝试 {attempt + 1}/{max_retries})，{delay}秒后重试")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # 非超时错误，立即重试
                        utils.logger.warning(f"[TiebaSimulationClient] 获取帖子评论失败 {post_id} (尝试 {attempt + 1}/{max_retries}): {e}")
                        await asyncio.sleep(1)
                        continue
                else:
                    # 最后一次尝试也失败了
                    utils.logger.error(f"[TiebaSimulationClient] 获取帖子评论最终失败 {post_id}: {e}")
                    raise DataFetchError(f"获取帖子评论失败: {e}")
        
        # 如果所有重试都没有返回结果，尝试页面解析作为最后手段
        utils.logger.warning(f"[TiebaSimulationClient] 所有重试失败，尝试页面解析评论: {post_id}")
        try:
            return await self._extract_post_comments_from_page()
        except Exception as e:
            # 评论获取失败不应该阻止主流程，返回空评论列表
            utils.logger.warning(f"[TiebaSimulationClient] 获取评论完全失败，返回空评论列表: {e}")
            return {'comments': [], 'has_more': False}
    
    async def _get_post_comments_with_progressive_loading(self, post_id: str, page: int = 1) -> Dict:
        """
        使用渐进式加载策略获取帖子评论
        """
        # 如果页面不在帖子详情页，先导航过去
        current_url = self.playwright_page.url
        if post_id not in current_url:
            post_url = f"{self._host}/p/{post_id}"
            
            # 使用较快的加载策略导航到帖子页面
            try:
                await self.playwright_page.goto(post_url, wait_until="domcontentloaded", 
                                              timeout=getattr(config, 'TIEBA_DOM_LOAD_TIMEOUT', 15000))
            except Exception as e:
                if "timeout" in str(e).lower():
                    # 如果DOM加载超时，尝试无等待条件的加载
                    utils.logger.debug(f"[TiebaSimulationClient] DOM加载超时，尝试基础加载")
                    await self.playwright_page.goto(post_url, timeout=getattr(config, 'TIEBA_PAGE_LOAD_TIMEOUT', 30000))
                else:
                    raise e
        
        # 设置网络拦截
        await self.network_interceptor.setup_interception()
        
        # 翻页到指定页码
        await self._navigate_to_comment_page(page)
        
        # 模拟用户阅读行为（缩短时间）
        await self.behavior_simulator.simulate_reading_behavior(1, 2)
        
        # 自适应等待网络请求完成
        await self._adaptive_network_wait()
        
        # 获取拦截数据
        intercepted_data = self.network_interceptor.get_intercepted_data(InterceptType.POST_COMMENTS)
        
        if intercepted_data:
            # 返回最新的评论数据
            latest_data = intercepted_data[-1]['data']
            return self._parse_comments_data(latest_data)
        else:
            # 如果没有拦截到数据，尝试页面解析
            utils.logger.info(f"[TiebaSimulationClient] 未拦截到评论网络数据，尝试页面解析: {post_id}")
            return await self._extract_post_comments_from_page()
    
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
    
    async def _extract_data_from_page(self) -> List[Dict]:
        """从页面直接提取数据（当网络拦截失败时使用）"""
        try:
            # 尝试等待更长时间，让页面充分加载
            await asyncio.sleep(3)
            
            # 基于Chrome MCP分析的真实页面结构进行数据提取
            posts_data = []
            
            # 检查当前页面是否为搜索结果页面
            current_url = self.playwright_page.url
            if "search/res" not in current_url:
                utils.logger.warning(f"[TiebaSimulationClient] 当前页面不是搜索结果页面: {current_url}")
                return []
                
            # 等待搜索结果容器加载
            try:
                await self.playwright_page.wait_for_selector(".s_post_list, .s_post", timeout=5000)
                utils.logger.info("[TiebaSimulationClient] 找到搜索结果容器")
            except:
                utils.logger.warning("[TiebaSimulationClient] 搜索结果容器未找到，打印页面内容进行调试")
                # 打印当前页面标题和URL
                current_url = self.playwright_page.url
                page_title = await self.playwright_page.title()
                utils.logger.info(f"[TiebaSimulationClient] 当前页面: {page_title} - {current_url}")
                
                # 检查页面是否有内容
                page_content = await self.playwright_page.content()
                utils.logger.info(f"[TiebaSimulationClient] 页面内容长度: {len(page_content)}")
                
                # 检查是否有常见的错误页面标识
                if "页面不存在" in page_content or "404" in page_content:
                    utils.logger.error("[TiebaSimulationClient] 页面不存在或404错误")
                elif "验证" in page_content or "security" in page_content.lower():
                    utils.logger.error("[TiebaSimulationClient] 可能遇到安全验证页面")
                
            # 基于真实页面结构提取帖子数据
            post_selectors = [
                ".s_post",           # 主要选择器：搜索结果中的帖子
                ".result-op",        # 备选选择器
                ".c-container",      # 通用容器选择器
                "[class*='post']"    # 包含post的class
            ]
            
            for selector in post_selectors:
                try:
                    post_elements = await self.playwright_page.query_selector_all(selector)
                    if post_elements:
                        utils.logger.info(f"[TiebaSimulationClient] 使用选择器 {selector} 找到 {len(post_elements)} 个帖子元素")
                        
                        for element in post_elements[:10]:  # 限制处理前10个元素
                            try:
                                post_data = await self._extract_post_from_element(element)
                                if post_data:
                                    posts_data.append(post_data)
                            except Exception as e:
                                utils.logger.debug(f"[TiebaSimulationClient] 提取单个帖子失败: {e}")
                                continue
                        break
                except Exception as e:
                    utils.logger.debug(f"[TiebaSimulationClient] 选择器 {selector} 失败: {e}")
                    continue
                    
            utils.logger.info(f"[TiebaSimulationClient] 页面直接提取获得 {len(posts_data)} 个帖子")
            return posts_data
            
        except Exception as e:
            utils.logger.warning(f"[TiebaSimulationClient] 直接提取数据失败: {e}")
            return []
    
    async def _extract_post_from_element(self, element) -> Optional[Dict]:
        """从单个帖子元素中提取数据（基于Chrome MCP分析的真实贴吧搜索结果页面结构）"""
        try:
            post_data = {}
            
            # 基于真实页面结构：<span class="p_title"><a>标题</a></span>
            title_element = await element.query_selector('.p_title a')
            if not title_element:
                # 备选选择器
                title_element = await element.query_selector('a[href*="/p/"]')
            
            if not title_element:
                utils.logger.debug("[TiebaSimulationClient] 未找到标题元素")
                return None
            
            # 提取标题和链接
            title = await title_element.text_content()
            href = await title_element.get_attribute('href')
            
            if not title or not title.strip() or not href:
                utils.logger.debug("[TiebaSimulationClient] 标题或链接为空")
                return None
            
            post_data['title'] = title.strip()
            
            # 标准化URL
            if href.startswith('/'):
                post_data['note_url'] = f"https://tieba.baidu.com{href}"
            elif href.startswith('http'):
                post_data['note_url'] = href
            else:
                utils.logger.debug(f"[TiebaSimulationClient] 无效的链接格式: {href}")
                return None
            
            # 提取帖子ID - 优先从data-tid属性获取
            post_id = await title_element.get_attribute('data-tid')
            if not post_id and '/p/' in href:
                # 从URL中提取帖子ID
                post_id = href.split('/p/')[-1].split('?')[0].split('#')[0]
            
            if not post_id or not post_id.isdigit():
                utils.logger.debug(f"[TiebaSimulationClient] 无效的帖子ID: {post_id}")
                return None
            
            post_data['note_id'] = post_id
            
            # 提取内容摘要 - 基于真实结构：<div class="p_content">内容</div>
            desc_element = await element.query_selector('.p_content')
            if desc_element:
                desc_text = await desc_element.text_content()
                if desc_text and desc_text.strip():
                    post_data['desc'] = desc_text.strip()
            
            # 提取贴吧信息 - 基于真实结构：<a class="p_forum" href="/f?kw=xxx">
            tieba_element = await element.query_selector('.p_forum')
            if not tieba_element:
                # 备选选择器
                tieba_element = await element.query_selector('a[href*="/f?kw="]')
            
            if tieba_element:
                tieba_text = await tieba_element.text_content()
                tieba_href = await tieba_element.get_attribute('href')
                if tieba_text and tieba_text.strip():
                    post_data['tieba_name'] = tieba_text.strip()
                    if tieba_href:
                        if tieba_href.startswith('/'):
                            post_data['tieba_link'] = f"https://tieba.baidu.com{tieba_href}"
                        else:
                            post_data['tieba_link'] = tieba_href
                
                # 尝试从data-fid属性获取贴吧ID
                fid = await tieba_element.get_attribute('data-fid')
                if fid:
                    post_data['tieba_id'] = fid
            
            # 提取用户信息 - 查找包含/home/main的链接
            user_element = await element.query_selector('a[href*="/home/main"]')
            if user_element:
                user_text = await user_element.text_content()
                user_href = await user_element.get_attribute('href')
                if user_text and user_text.strip():
                    post_data['user_nickname'] = user_text.strip()
                if user_href:
                    if user_href.startswith('/'):
                        post_data['user_link'] = f"https://tieba.baidu.com{user_href}"
                    else:
                        post_data['user_link'] = user_href
            
            # 提取时间信息 - 基于真实结构：<font class="p_green p_date">时间</font>
            time_element = await element.query_selector('.p_date')
            if not time_element:
                # 备选选择器
                time_element = await element.query_selector('.p_green')
            
            if time_element:
                time_text = await time_element.text_content()
                if time_text and time_text.strip():
                    # 处理时间格式，确保数据库兼容
                    time_clean = time_text.strip()
                    # 限制时间字段长度，避免数据库截断
                    if len(time_clean) > 50:  # 假设数据库字段长度限制
                        time_clean = time_clean[:50]
                    post_data['publish_time'] = time_clean
            
            # 设置必需的默认值
            post_data.setdefault('desc', "")
            post_data.setdefault('publish_time', "")
            post_data.setdefault('tieba_name', "")
            post_data.setdefault('tieba_link', "")
            post_data.setdefault('user_link', "")
            post_data.setdefault('user_nickname', "")
            post_data.setdefault('user_avatar', "")
            post_data.setdefault('total_replay_num', 0)
            post_data.setdefault('total_replay_page', 0)
            post_data.setdefault('ip_location', "")
            post_data.setdefault('source_keyword', "")
            
            # 验证提取的数据完整性
            if not post_data.get('note_id') or not post_data.get('title'):
                utils.logger.warning(f"[TiebaSimulationClient] 提取的帖子数据不完整，跳过")
                return None
                
            utils.logger.debug(f"[TiebaSimulationClient] 成功提取帖子: {post_data.get('title', '')[:30]}...")
            return post_data
                
        except Exception as e:
            utils.logger.warning(f"[TiebaSimulationClient] 提取帖子元素数据失败: {e}")
            utils.logger.debug(f"[TiebaSimulationClient] 错误详情: {e.__class__.__name__}: {str(e)}")
            return None
    
    async def _parse_page_content(self) -> Dict:
        """直接解析页面内容"""
        try:
            utils.logger.info("[TiebaSimulationClient] 使用页面直接解析模式")
            
            # 使用已有的数据提取方法
            posts_data = await self._extract_data_from_page()
            
            return {'posts': posts_data}
            
        except Exception as e:
            utils.logger.error(f"[TiebaSimulationClient] 页面内容解析失败: {e}")
            return {'posts': []}
    
    async def request(self, method: str, url: str, **kwargs) -> Dict:
        """
        发送HTTP请求（适配抽象方法）
        注意：贴吧模拟爬虫主要通过浏览器自动化获取数据，此方法仅为兼容性
        """
        # 标记参数为已使用以避免警告
        _ = method, url, kwargs
        utils.logger.warning("[TiebaSimulationClient] 贴吧模拟爬虫主要通过浏览器自动化获取数据")
        return {}