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
import random
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from playwright.async_api import Page, Response

from .field import InterceptType, BehaviorType, AntiDetectionLevel, SearchSortType
from .exception import NetworkInterceptError, UserBehaviorSimulationError, AntiDetectionError


class NetworkInterceptor:
    """网络请求拦截器"""
    
    def __init__(self, page: Page):
        self.page = page
        self.intercepted_data = []
        self.is_setup = False
    
    async def setup_interception(self) -> None:
        """设置网络拦截"""
        if self.is_setup:
            return
            
        self.page.on('response', self._handle_response)
        self.is_setup = True
    
    async def _handle_response(self, response: Response) -> None:
        """处理网络响应"""
        try:
            url = response.url
            
            # 拦截贴吧相关API
            if self._is_target_api(url):
                try:
                    data = await response.json()
                    intercept_type = self._classify_response(url)
                    
                    self.intercepted_data.append({
                        'type': intercept_type,
                        'url': url,
                        'data': data,
                        'timestamp': int(time.time() * 1000),
                        'status': response.status
                    })
                except Exception as e:
                    # 非JSON响应或解析失败，忽略
                    pass
                    
        except Exception as e:
            # 拦截失败不影响主流程
            pass
    
    def _is_target_api(self, url: str) -> bool:
        """判断是否为目标API"""
        target_patterns = [
            '/f/search/res',  # 搜索结果
            '/p/',            # 帖子详情
            '/f/',            # 贴吧首页
            '/mo/q/m',        # 移动端API
            '/home/get',      # 获取内容
            'searchjson',     # 搜索JSON
            'floorpb',        # 楼层回复
            '/f/commit/thread', # 发帖
            'api/search',     # API搜索
            'api/thread',     # API帖子
            'api/post',       # API发帖
            'pn=',            # 分页参数
            'kw=',            # 关键词参数
        ]
        
        return any(pattern in url for pattern in target_patterns)
    
    def _classify_response(self, url: str) -> InterceptType:
        """根据URL分类响应类型"""
        if '/f/search/res' in url or 'searchjson' in url:
            return InterceptType.SEARCH_POSTS
        elif '/p/' in url:
            return InterceptType.POST_DETAIL
        elif 'floorpb' in url:
            return InterceptType.POST_COMMENTS
        elif '/home/get' in url:
            return InterceptType.USER_PROFILE
        else:
            return InterceptType.SEARCH_POSTS
    
    def get_intercepted_data(self, intercept_type: InterceptType) -> List[Dict]:
        """获取指定类型的拦截数据"""
        return [item for item in self.intercepted_data if item['type'] == intercept_type]
    
    def clear_data(self) -> None:
        """清空拦截数据"""
        self.intercepted_data.clear()


class UserBehaviorSimulator:
    """用户行为模拟器"""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def simulate_human_scroll(self, count: int = 3, delay_range: Tuple[int, int] = (500, 1500)) -> None:
        """模拟人类滚动行为"""
        try:
            for i in range(count):
                # 随机滚动距离
                scroll_distance = random.randint(300, 800)
                
                # 执行滚动
                await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                
                # 等待页面稳定
                await asyncio.sleep(0.5)
                
                # 随机等待
                delay = random.randint(*delay_range)
                await asyncio.sleep(delay / 1000)
                
                # 偶尔向上滚动，模拟真实用户行为
                if random.random() < 0.2:  # 20%概率向上滚动
                    up_distance = random.randint(100, 300)
                    await self.page.evaluate(f"window.scrollBy(0, -{up_distance})")
                    await asyncio.sleep(0.3)
                
        except Exception as e:
            raise UserBehaviorSimulationError(f"滚动模拟失败: {e}")
    
    async def simulate_click_with_delay(self, selector: str, delay_range: Tuple[int, int] = (100, 500)) -> None:
        """模拟点击并添加延迟"""
        try:
            # 先悬停
            await self.page.hover(selector)
            
            # 随机延迟
            delay = random.randint(*delay_range)
            await asyncio.sleep(delay / 1000)
            
            # 点击
            await self.page.click(selector)
            
        except Exception as e:
            raise UserBehaviorSimulationError(f"点击模拟失败: {e}")
    
    async def simulate_reading_behavior(self, min_seconds: int = 2, max_seconds: int = 5) -> None:
        """模拟阅读行为"""
        try:
            # 模拟阅读时间
            read_time = random.uniform(min_seconds, max_seconds)
            await asyncio.sleep(read_time)
            
            # 模拟偶尔的页面滚动
            if random.random() < 0.3:  # 30%概率滚动
                await self.simulate_human_scroll(1, (200, 800))
                
        except Exception as e:
            raise UserBehaviorSimulationError(f"阅读行为模拟失败: {e}")
    
    async def simulate_mouse_movement(self, target_selector: Optional[str] = None) -> None:
        """模拟鼠标移动"""
        try:
            if target_selector:
                # 移动到指定元素
                await self.page.hover(target_selector)
            else:
                # 随机移动鼠标
                viewport = self.page.viewport_size
                if viewport:
                    x = random.randint(100, viewport['width'] - 100)
                    y = random.randint(100, viewport['height'] - 100)
                    await self.page.mouse.move(x, y)
                    
        except Exception as e:
            raise UserBehaviorSimulationError(f"鼠标移动模拟失败: {e}")


class AntiDetectionHelper:
    """反检测助手"""
    
    def __init__(self, page: Page):
        self.page = page
    
    async def setup_stealth_mode(self, level: AntiDetectionLevel = AntiDetectionLevel.MEDIUM) -> None:
        """设置隐身模式"""
        try:
            # 基础反检测
            await self._hide_webdriver()
            await self._randomize_viewport()
            
            if level in [AntiDetectionLevel.HIGH, AntiDetectionLevel.EXTREME]:
                await self._inject_random_properties()
                await self._setup_request_interception()
                
            if level == AntiDetectionLevel.EXTREME:
                await self._randomize_timing()
                
        except Exception as e:
            raise AntiDetectionError(f"反检测设置失败: {e}")
    
    async def _hide_webdriver(self) -> None:
        """隐藏webdriver特征"""
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en'],
            });
            
            window.chrome = {
                runtime: {},
            };
        """)
    
    async def _randomize_viewport(self) -> None:
        """随机化视口大小"""
        width = random.randint(1200, 1920)
        height = random.randint(800, 1080)
        await self.page.set_viewport_size({'width': width, 'height': height})
    
    async def _inject_random_properties(self) -> None:
        """注入随机属性"""
        await self.page.add_init_script(f"""
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {random.randint(4, 16)},
            }});
            
            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {random.choice([4, 8, 16])},
            }});
            
            Object.defineProperty(screen, 'colorDepth', {{
                get: () => {random.choice([24, 32])},
            }});
        """)
    
    async def _setup_request_interception(self) -> None:
        """设置请求拦截"""
        await self.page.route('**/*', lambda route: route.continue_())
    
    async def _randomize_timing(self) -> None:
        """随机化时序"""
        await self.page.add_init_script("""
            const originalSetTimeout = window.setTimeout;
            window.setTimeout = function(fn, delay) {
                const randomDelay = delay + Math.random() * 100;
                return originalSetTimeout(fn, randomDelay);
            };
        """)


def parse_post_info_from_response(data: Dict) -> Dict:
    """从响应数据中解析帖子信息"""
    try:
        if not data or 'data' not in data:
            return {}
        
        # 根据贴吧API结构解析
        posts = []
        post_data = data['data']
        
        if isinstance(post_data, dict):
            # 单个帖子详情
            post_info = {
                'post_id': post_data.get('tid', ''),
                'title': post_data.get('title', ''),
                'content': post_data.get('content', ''),
                'author': post_data.get('author', ''),
                'reply_count': post_data.get('reply_num', 0),
                'publish_time': post_data.get('create_time', 0),
                'forum_name': post_data.get('fname', ''),
            }
            posts.append(post_info)
            
        elif isinstance(post_data, list):
            # 搜索结果列表
            for item in post_data:
                post_info = {
                    'post_id': item.get('tid', ''),
                    'title': item.get('title', ''),
                    'content': item.get('abstract', ''),
                    'author': item.get('author_name', ''),
                    'reply_count': item.get('reply_num', 0),
                    'publish_time': item.get('create_time', 0),
                    'forum_name': item.get('fname', ''),
                }
                posts.append(post_info)
        
        return {'posts': posts}
        
    except Exception as e:
        return {'error': str(e)}


def format_search_params(keyword: str, page: int = 1, sort_type: SearchSortType = SearchSortType.TIME_DESC) -> Dict:
    """格式化搜索参数"""
    return {
        'keyword': keyword,
        'page': page,
        'sort': sort_type.value,
        'search_id': f"search_{int(time.time() * 1000)}"
    }