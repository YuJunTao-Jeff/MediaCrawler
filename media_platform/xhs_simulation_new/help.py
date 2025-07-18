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

from .field import InterceptType, BehaviorType, AntiDetectionLevel
from .exception import NetworkInterceptError, UserBehaviorSimulationError, AntiDetectionError


class NetworkInterceptor:
    """网络请求拦截器"""
    
    def __init__(self, page: Page):
        self.page = page
        self.intercepted_data = []
        self.intercept_patterns = {
            InterceptType.SEARCH_NOTES: [
                "/api/sns/web/v1/search/notes",
                "/api/sns/web/v2/search/notes"
            ],
            InterceptType.NOTE_DETAIL: [
                "/api/sns/web/v1/feed",
                "/api/sns/web/v2/feed"
            ],
            InterceptType.NOTE_COMMENTS: [
                "/api/sns/web/v2/comment/page",
                "/api/sns/web/v1/comment/page"
            ],
            InterceptType.USER_PROFILE: [
                "/api/sns/web/v1/user/otherinfo"
            ]
        }
    
    async def setup_interception(self) -> None:
        """设置网络拦截"""
        try:
            await self.page.route("**/*", self._handle_request)
            self.page.on("response", self._handle_response)
        except Exception as e:
            raise NetworkInterceptError(f"设置网络拦截失败: {e}")
    
    async def _handle_request(self, route, request) -> None:
        """处理请求"""
        await route.continue_()
    
    async def _handle_response(self, response: Response) -> None:
        """处理响应"""
        try:
            url = response.url
            for intercept_type, patterns in self.intercept_patterns.items():
                if any(pattern in url for pattern in patterns):
                    if response.status == 200:
                        try:
                            data = await response.json()
                            self.intercepted_data.append({
                                'type': intercept_type.value,
                                'url': url,
                                'data': data,
                                'timestamp': int(time.time() * 1000)
                            })
                        except:
                            pass
        except Exception:
            pass
    
    def get_intercepted_data(self, intercept_type: InterceptType = None) -> List[Dict]:
        """获取拦截到的数据"""
        if intercept_type:
            return [item for item in self.intercepted_data if item['type'] == intercept_type.value]
        return self.intercepted_data
    
    def clear_data(self) -> None:
        """清空拦截数据"""
        self.intercepted_data.clear()


class UserBehaviorSimulator:
    """用户行为模拟器"""
    
    def __init__(self, page: Page):
        self.page = page
        
    async def simulate_human_scroll(self, 
                                  scroll_count: int = 3,
                                  scroll_distance: int = 800,
                                  delay_range: Tuple[float, float] = (1.0, 3.0)) -> None:
        """模拟人类滚动行为"""
        try:
            for i in range(scroll_count):
                # 随机滚动距离
                distance = scroll_distance + random.randint(-200, 200)
                
                # 模拟滚动动画
                await self.page.evaluate(f"""
                    window.scrollBy({{
                        top: {distance},
                        behavior: 'smooth'
                    }});
                """)
                
                # 随机停顿时间
                delay = random.uniform(*delay_range)
                await asyncio.sleep(delay)
                
        except Exception as e:
            raise UserBehaviorSimulationError(f"滚动模拟失败: {e}")
    
    async def simulate_mouse_movement(self, 
                                    target_selector: str = None,
                                    movement_count: int = 3) -> None:
        """模拟鼠标移动"""
        try:
            for _ in range(movement_count):
                if target_selector:
                    element = await self.page.query_selector(target_selector)
                    if element:
                        box = await element.bounding_box()
                        if box:
                            x = box['x'] + random.randint(0, int(box['width']))
                            y = box['y'] + random.randint(0, int(box['height']))
                        else:
                            x, y = random.randint(100, 800), random.randint(100, 600)
                    else:
                        x, y = random.randint(100, 800), random.randint(100, 600)
                else:
                    x, y = random.randint(100, 800), random.randint(100, 600)
                
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
        except Exception as e:
            raise UserBehaviorSimulationError(f"鼠标移动模拟失败: {e}")
    
    async def simulate_reading_behavior(self, min_time: float = 2.0, max_time: float = 8.0) -> None:
        """模拟阅读行为"""
        try:
            read_time = random.uniform(min_time, max_time)
            await asyncio.sleep(read_time)
        except Exception as e:
            raise UserBehaviorSimulationError(f"阅读行为模拟失败: {e}")
    
    async def simulate_click_with_delay(self, 
                                      selector: str,
                                      delay_before: Tuple[float, float] = (0.5, 2.0),
                                      delay_after: Tuple[float, float] = (1.0, 3.0)) -> None:
        """模拟带延迟的点击"""
        try:
            # 点击前延迟
            await asyncio.sleep(random.uniform(*delay_before))
            
            # 先移动到元素位置
            await self.page.hover(selector)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # 执行点击
            await self.page.click(selector)
            
            # 点击后延迟
            await asyncio.sleep(random.uniform(*delay_after))
            
        except Exception as e:
            raise UserBehaviorSimulationError(f"点击模拟失败: {e}")


class AntiDetectionHelper:
    """反检测助手"""
    
    def __init__(self, page: Page):
        self.page = page
        
    async def hide_webdriver_flags(self) -> None:
        """隐藏WebDriver特征"""
        try:
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // 删除 window.chrome.runtime
                delete window.chrome.runtime;
                
                // 重写 permissions.query
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // 重写 plugins 长度
                Object.defineProperty(navigator, 'plugins', {
                    get: () => ({
                        length: 1,
                        0: {
                            name: 'Chrome PDF Plugin'
                        }
                    }),
                });
                
                // 重写 languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                });
            """)
        except Exception as e:
            raise AntiDetectionError(f"隐藏WebDriver特征失败: {e}")
    
    async def randomize_viewport(self) -> None:
        """随机化视窗大小"""
        try:
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            await self.page.set_viewport_size({"width": width, "height": height})
        except Exception as e:
            raise AntiDetectionError(f"随机化视窗失败: {e}")
    
    async def add_random_delays(self, base_delay: float = 1.0, variance: float = 0.5) -> None:
        """添加随机延迟"""
        try:
            delay = base_delay + random.uniform(-variance, variance)
            if delay > 0:
                await asyncio.sleep(delay)
        except Exception as e:
            raise AntiDetectionError(f"添加随机延迟失败: {e}")
    
    async def setup_stealth_mode(self, level: AntiDetectionLevel = AntiDetectionLevel.MEDIUM) -> None:
        """设置隐蔽模式"""
        try:
            await self.hide_webdriver_flags()
            
            if level in [AntiDetectionLevel.MEDIUM, AntiDetectionLevel.HIGH, AntiDetectionLevel.EXTREME]:
                await self.randomize_viewport()
                
            if level in [AntiDetectionLevel.HIGH, AntiDetectionLevel.EXTREME]:
                # 高级反检测措施
                await self.page.add_init_script("""
                    // 伪造 canvas 指纹
                    const getContext = HTMLCanvasElement.prototype.getContext;
                    HTMLCanvasElement.prototype.getContext = function(type) {
                        const context = getContext.call(this, type);
                        if (type === '2d') {
                            const originalFillText = context.fillText;
                            context.fillText = function() {
                                // 添加微小的随机偏移
                                arguments[1] += Math.random() * 0.001;
                                arguments[2] += Math.random() * 0.001;
                                return originalFillText.apply(this, arguments);
                            };
                        }
                        return context;
                    };
                """)
                
        except Exception as e:
            raise AntiDetectionError(f"设置隐蔽模式失败: {e}")


def parse_note_info_from_response(response_data: Dict) -> Dict:
    """从响应数据中解析笔记信息"""
    try:
        if 'data' not in response_data:
            return {}
            
        items = response_data['data'].get('items', [])
        parsed_notes = []
        
        for item in items:
            note_info = item.get('note_card', {})
            if note_info:
                parsed_note = {
                    'note_id': note_info.get('note_id', ''),
                    'title': note_info.get('display_title', ''),
                    'desc': note_info.get('desc', ''),
                    'type': note_info.get('type', ''),
                    'liked_count': note_info.get('interact_info', {}).get('liked_count', 0),
                    'collected_count': note_info.get('interact_info', {}).get('collected_count', 0),
                    'comment_count': note_info.get('interact_info', {}).get('comment_count', 0),
                    'share_count': note_info.get('interact_info', {}).get('share_count', 0),
                    'time': note_info.get('time', 0),
                    'user_info': {
                        'user_id': note_info.get('user', {}).get('user_id', ''),
                        'nickname': note_info.get('user', {}).get('nickname', ''),
                        'avatar': note_info.get('user', {}).get('avatar', ''),
                    },
                    'image_list': [img.get('url_default', '') for img in note_info.get('image_list', [])],
                    'video_url': note_info.get('video', {}).get('media', {}).get('stream', {}).get('h264', [{}])[0].get('master_url', '') if note_info.get('video') else '',
                }
                parsed_notes.append(parsed_note)
        
        return {
            'notes': parsed_notes,
            'has_more': response_data['data'].get('has_more', False),
            'cursor': response_data['data'].get('cursor', '')
        }
        
    except Exception as e:
        return {'error': str(e)}


def format_search_params(keyword: str, page: int = 1, sort_type: SearchSortType = SearchSortType.GENERAL) -> Dict:
    """格式化搜索参数"""
    return {
        'keyword': keyword,
        'page': page,
        'sort': sort_type.value,
        'search_id': f"search_{int(time.time() * 1000)}"
    }