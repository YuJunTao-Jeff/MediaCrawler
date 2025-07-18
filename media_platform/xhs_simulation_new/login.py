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
from typing import Optional

from playwright.async_api import BrowserContext, Page

import config
from base.base_crawler import AbstractLogin
from tools import utils

from .help import UserBehaviorSimulator, AntiDetectionHelper
from .exception import BrowserAutomationError


class XHSSimulationLogin(AbstractLogin):
    """小红书模拟登录"""
    
    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: str = ""):
        
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str
        
        # 初始化辅助工具
        self.behavior_simulator = UserBehaviorSimulator(context_page)
        self.anti_detection = AntiDetectionHelper(context_page)
    
    async def begin(self) -> None:
        """开始登录流程"""
        utils.logger.info("[XHSSimulationLogin] 开始模拟登录流程")
        
        try:
            # 设置反检测
            await self.anti_detection.setup_stealth_mode()
            
            # 导航到登录页面
            await self.context_page.goto("https://www.xiaohongshu.com")
            await asyncio.sleep(2)
            
            # 模拟用户行为
            await self.behavior_simulator.simulate_reading_behavior(2, 4)
            
            if self.login_type == "qrcode":
                await self._qrcode_login()
            elif self.login_type == "phone":
                await self._phone_login()
            elif self.login_type == "cookie":
                await self._cookie_login()
            else:
                raise BrowserAutomationError(f"不支持的登录类型: {self.login_type}")
                
        except Exception as e:
            utils.logger.error(f"[XHSSimulationLogin] 登录失败: {e}")
            raise e
    
    async def _qrcode_login(self) -> None:
        """二维码登录"""
        utils.logger.info("[XHSSimulationLogin] 使用二维码登录")
        
        try:
            # 先处理可能的遮罩和弹窗
            await self._handle_page_overlays()
            
            # 尝试多种方式触发登录
            login_success = False
            
            # 方法1: 直接查找并点击登录相关元素
            login_selectors = [
                "div.login-btn",
                ".side-bar-component.login-btn", 
                ".login-button",
                ".sign-in-button",
                "[data-testid='login-button']",
                "button:has-text('登录')",
                "div:has-text('登录')"
            ]
            
            for selector in login_selectors:
                try:
                    element = await self.context_page.query_selector(selector)
                    if element and await element.is_visible():
                        utils.logger.info(f"[XHSSimulationLogin] 尝试点击登录元素: {selector}")
                        await element.click(force=True)
                        login_success = True
                        break
                except Exception as e:
                    utils.logger.debug(f"[XHSSimulationLogin] 点击失败 {selector}: {e}")
                    continue
            
            # 方法2: 如果直接点击失败，尝试键盘导航
            if not login_success:
                utils.logger.info("[XHSSimulationLogin] 尝试键盘导航到登录按钮")
                await self.context_page.keyboard.press('Tab')
                await asyncio.sleep(0.5)
                await self.context_page.keyboard.press('Enter')
            
            # 等待二维码出现
            qr_selectors = [
                ".qrcode", 
                ".qr-code", 
                "[class*='qr']",
                "img[src*='qr']",
                "canvas",
                ".login-qrcode"
            ]
            
            qr_found = False
            for qr_selector in qr_selectors:
                try:
                    await self.context_page.wait_for_selector(qr_selector, timeout=5000)
                    qr_found = True
                    utils.logger.info(f"[XHSSimulationLogin] 找到二维码: {qr_selector}")
                    break
                except:
                    continue
            
            if not qr_found:
                utils.logger.warning("[XHSSimulationLogin] 未找到二维码，但继续等待登录")
            
            utils.logger.info("[XHSSimulationLogin] 请使用小红书APP扫描二维码登录，或手动完成登录流程")
            
            # 等待登录成功（检查页面变化）
            await self._wait_for_login_success()
            
        except Exception as e:
            raise BrowserAutomationError(f"二维码登录失败: {e}")
    
    async def _phone_login(self) -> None:
        """手机号登录"""
        utils.logger.info("[XHSSimulationLogin] 使用手机号登录")
        
        if not self.login_phone:
            raise BrowserAutomationError("手机号登录需要提供手机号")
        
        try:
            # 点击登录按钮
            login_button_selector = ".login-btn, .sign-in-button"
            await self.behavior_simulator.simulate_click_with_delay(login_button_selector)
            
            # 切换到手机号登录
            phone_tab_selector = ".phone-login-tab, [data-testid='phone-login']"
            await self.behavior_simulator.simulate_click_with_delay(phone_tab_selector)
            
            # 输入手机号
            phone_input_selector = "input[placeholder*='手机号'], input[type='tel']"
            await self.context_page.fill(phone_input_selector, self.login_phone)
            await self.behavior_simulator.simulate_reading_behavior(1, 2)
            
            # 发送验证码
            send_code_selector = ".send-code-btn, [data-testid='send-code']"
            await self.behavior_simulator.simulate_click_with_delay(send_code_selector)
            
            utils.logger.info("[XHSSimulationLogin] 请输入手机验证码")
            
            # 等待用户输入验证码并登录
            await self._wait_for_login_success()
            
        except Exception as e:
            raise BrowserAutomationError(f"手机号登录失败: {e}")
    
    async def _cookie_login(self) -> None:
        """Cookie登录"""
        utils.logger.info("[XHSSimulationLogin] 使用Cookie登录")
        
        if not self.cookie_str:
            raise BrowserAutomationError("Cookie登录需要提供Cookie字符串")
        
        try:
            # 解析并设置Cookie
            cookies = self._parse_cookie_string(self.cookie_str)
            await self.browser_context.add_cookies(cookies)
            
            # 刷新页面验证登录状态
            await self.context_page.reload()
            await asyncio.sleep(3)
            
            # 检查登录状态
            if await self._check_login_status():
                utils.logger.info("[XHSSimulationLogin] Cookie登录成功")
            else:
                raise BrowserAutomationError("Cookie已失效，请重新登录")
                
        except Exception as e:
            raise BrowserAutomationError(f"Cookie登录失败: {e}")
    
    async def _wait_for_login_success(self, timeout: int = 300000) -> None:
        """等待登录成功"""
        utils.logger.info("[XHSSimulationLogin] 等待登录成功...")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if (current_time - start_time) * 1000 > timeout:
                raise BrowserAutomationError("登录超时")
            
            if await self._check_login_status():
                utils.logger.info("[XHSSimulationLogin] 登录成功！")
                break
                
            await asyncio.sleep(2)
    
    async def _check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            # 检查是否存在用户头像或用户信息
            user_indicators = [
                ".user-avatar",
                ".user-info", 
                "[data-testid='user-avatar']",
                ".avatar"
            ]
            
            for selector in user_indicators:
                element = await self.context_page.query_selector(selector)
                if element:
                    return True
            
            # 检查当前URL是否不包含登录页面标识
            current_url = self.context_page.url
            if "login" not in current_url and "signin" not in current_url:
                return True
                
            return False
            
        except Exception:
            return False
    
    def _parse_cookie_string(self, cookie_str: str) -> list:
        """解析Cookie字符串"""
        cookies = []
        for cookie in cookie_str.split(';'):
            if '=' in cookie:
                name, value = cookie.strip().split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.xiaohongshu.com',
                    'path': '/'
                })
        return cookies
    
    async def check_login_state(self, account_file: str) -> str:
        """检查登录状态"""
        if await self._check_login_status():
            return "success"
        else:
            return "failed"
    
    async def login_by_qrcode(self) -> None:
        """二维码登录（抽象方法实现）"""
        await self._qrcode_login()
    
    async def login_by_mobile(self) -> None:
        """手机号登录（抽象方法实现）"""
        await self._phone_login()
    
    async def login_by_cookies(self) -> None:
        """Cookie登录（抽象方法实现）"""
        await self._cookie_login()
    
    async def _handle_page_overlays(self) -> None:
        """处理页面遮罩和弹窗"""
        try:
            # 处理可能的遮罩层
            overlay_selectors = [
                ".reds-mask",
                ".mask",
                ".overlay",
                ".modal-backdrop",
                "[class*='mask']",
                "[aria-label='弹窗遮罩']"
            ]
            
            for selector in overlay_selectors:
                try:
                    elements = await self.context_page.query_selector_all(selector)
                    for element in elements:
                        if await element.is_visible():
                            utils.logger.info(f"[XHSSimulationLogin] 发现遮罩层，尝试点击: {selector}")
                            await element.click(force=True)
                            await asyncio.sleep(0.5)
                except Exception as e:
                    utils.logger.debug(f"[XHSSimulationLogin] 处理遮罩失败 {selector}: {e}")
                    continue
            
            # 处理可能的弹窗关闭按钮
            close_selectors = [
                ".close",
                ".close-btn", 
                "[aria-label='关闭']",
                "[class*='close']",
                "button:has-text('×')",
                "button:has-text('关闭')"
            ]
            
            for selector in close_selectors:
                try:
                    element = await self.context_page.query_selector(selector)
                    if element and await element.is_visible():
                        utils.logger.info(f"[XHSSimulationLogin] 发现关闭按钮，尝试点击: {selector}")
                        await element.click()
                        await asyncio.sleep(0.5)
                except Exception as e:
                    utils.logger.debug(f"[XHSSimulationLogin] 处理关闭按钮失败 {selector}: {e}")
                    continue
            
            # 按ESC键关闭可能的弹窗
            await self.context_page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
        except Exception as e:
            utils.logger.warning(f"[XHSSimulationLogin] 处理页面遮罩失败: {e}")