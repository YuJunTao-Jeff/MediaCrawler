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
import json
from typing import Dict, Any, Optional

from playwright.async_api import BrowserContext, Page

import config
from tools import utils
from .exception import BrowserAutomationError


class SogouWeixinLogin:
    """搜狗微信登录管理"""
    
    def __init__(self, login_type: str):
        """
        初始化登录管理器
        
        Args:
            login_type: 登录类型，暂时不支持登录，主要用于Cookie管理
        """
        self.login_type = login_type
        self.cookie_str = getattr(config, 'SOGOU_WEIXIN_COOKIE_STR', '')
        
    async def begin(self, playwright_page: Page) -> Page:
        """
        开始登录流程（搜狗微信主要靠Cookie，暂不支持主动登录）
        
        Args:
            playwright_page: Playwright页面对象
            
        Returns:
            已设置Cookie的页面对象
        """
        utils.logger.info("[SogouWeixinLogin.begin] 开始设置搜狗微信访问状态...")
        
        try:
            # 导航到搜狗微信首页
            await playwright_page.goto("https://weixin.sogou.com", wait_until="networkidle")
            
            # 如果有预设的Cookie字符串，则设置
            if self.cookie_str:
                await self._set_cookies_from_string(playwright_page)
                utils.logger.info("[SogouWeixinLogin.begin] 已设置预配置的Cookie")
            else:
                utils.logger.info("[SogouWeixinLogin.begin] 未配置Cookie，将使用默认访问方式")
            
            # 等待页面稳定
            await asyncio.sleep(2)
            
            return playwright_page
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinLogin.begin] 登录失败: {e}")
            raise BrowserAutomationError(f"搜狗微信登录失败: {e}")
    
    async def _set_cookies_from_string(self, page: Page) -> None:
        """
        从Cookie字符串设置Cookie
        
        Args:
            page: 页面对象
        """
        if not self.cookie_str:
            return
        
        try:
            # 解析Cookie字符串
            cookies = []
            for cookie_pair in self.cookie_str.split(';'):
                if '=' in cookie_pair:
                    name, value = cookie_pair.strip().split('=', 1)
                    cookies.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.sogou.com',
                        'path': '/'
                    })
            
            # 设置Cookie
            if cookies:
                await page.context.add_cookies(cookies)
                utils.logger.info(f"[SogouWeixinLogin] 已设置 {len(cookies)} 个Cookie")
        
        except Exception as e:
            utils.logger.error(f"[SogouWeixinLogin] Cookie设置失败: {e}")
    
    @staticmethod  
    async def check_login_state(page: Page) -> bool:
        """
        检查登录状态（搜狗微信主要检查是否被反爬限制）
        
        Args:
            page: 页面对象
            
        Returns:
            是否可以正常访问
        """
        try:
            # 检查是否出现验证码
            captcha_element = await page.query_selector('.vcode-wrap')
            if captcha_element:
                utils.logger.warning("[SogouWeixinLogin] 检测到验证码，需要人工处理")
                return False
            
            # 检查是否被限制访问
            error_elements = await page.query_selector_all('.error, .block, .forbidden')
            if error_elements:
                utils.logger.warning("[SogouWeixinLogin] 检测到访问限制")
                return False
            
            return True
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinLogin] 登录状态检查失败: {e}")
            return False