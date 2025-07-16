# -*- coding: utf-8 -*-
"""
断点续爬集成模板
各平台爬虫可以参考此模板实现断点续爬功能
"""

from typing import Dict, Optional, List
from base.base_crawler import AbstractCrawler
import config


class ResumeCrawlTemplate(AbstractCrawler):
    """断点续爬集成模板示例"""
    
    def __init__(self, platform_name: str):
        super().__init__()
        self.platform_name = platform_name
        
    async def start(self):
        """启动爬虫的集成示例"""
        # 1. 初始化断点续爬功能
        await self.init_resume_crawl(self.platform_name, config.RESUME_TASK_ID)
        
        # 2. 执行搜索
        await self.search()
        
        # 3. 清理资源
        await self.cleanup_crawl_progress()
    
    async def search(self):
        """搜索集成示例"""
        if not config.KEYWORDS:
            return
        
        keywords = config.KEYWORDS.split(',')
        
        for keyword in keywords:
            await self.search_keyword(keyword.strip())
    
    async def search_keyword(self, keyword: str):
        """单个关键词搜索的集成示例"""
        # 1. 获取断点续爬起始页
        start_page = await self.get_resume_start_page(keyword)
        
        # 如果起始页是999999，表示该关键词已完成
        if start_page >= 999999:
            return
        
        page = start_page
        total_items = 0
        new_items = 0
        duplicate_items = 0
        failed_items = 0
        empty_page_count = 0
        
        while page <= config.CRAWLER_MAX_NOTES_COUNT // 20:  # 假设每页20条
            # 2. 检查是否应该停止
            if await self.should_stop_keyword_crawl(keyword, page):
                break
            
            # 3. 爬取页面数据
            page_items = await self.crawl_page(keyword, page)
            
            # 4. 处理空页面
            if not page_items:
                empty_page_count += 1
                if empty_page_count >= config.EMPTY_PAGE_THRESHOLD:
                    break
                page += 1
                continue
            else:
                empty_page_count = 0
            
            # 5. 批量处理数据
            processed_items = await self.process_crawl_batch(keyword, page, page_items)
            
            # 6. 去重和存储
            page_new_items = 0
            page_duplicate_items = 0
            page_failed_items = 0
            
            for item in processed_items:
                total_items += 1
                
                # 检查是否应该跳过（去重）
                if await self.should_skip_content(item, keyword):
                    duplicate_items += 1
                    page_duplicate_items += 1
                    continue
                
                # 存储数据
                try:
                    await self.store_content_item(item)
                    new_items += 1
                    page_new_items += 1
                except Exception as e:
                    failed_items += 1
                    page_failed_items += 1
                    print(f"存储失败: {e}")
            
            # 7. 更新进度
            last_item = processed_items[-1] if processed_items else None
            await self.update_crawl_progress(keyword, page, len(processed_items), last_item)
            
            # 8. 保存检查点
            checkpoint_data = {
                'items': processed_items,
                'page_stats': {
                    'new': page_new_items,
                    'duplicate': page_duplicate_items,
                    'failed': page_failed_items
                }
            }
            await self.save_crawl_checkpoint(keyword, page, checkpoint_data)
            
            page += 1
        
        # 9. 标记关键词完成
        await self.mark_keyword_completed(keyword)
        
        # 10. 更新统计信息
        await self.update_crawl_statistics(total_items, new_items, duplicate_items, failed_items)
    
    async def crawl_page(self, keyword: str, page: int) -> List[Dict]:
        """爬取单页数据 - 需要子类实现"""
        # 这里应该实现具体的页面爬取逻辑
        # 返回该页面的数据列表
        return []
    
    async def store_content_item(self, item: Dict):
        """存储内容项 - 需要子类实现"""
        # 这里应该实现具体的数据存储逻辑
        pass
    
    # 必须实现的抽象方法
    def extract_item_id(self, content_item: Dict) -> Optional[str]:
        """
        提取内容项的唯一ID
        需要根据具体平台的数据结构来实现
        """
        # 示例实现，需要根据实际平台数据结构调整
        return content_item.get('id') or content_item.get('note_id') or content_item.get('aweme_id')
    
    def extract_item_timestamp(self, content_item: Dict) -> Optional[int]:
        """
        提取内容项的时间戳
        需要根据具体平台的数据结构来实现
        """
        # 示例实现，需要根据实际平台数据结构调整
        timestamp = content_item.get('timestamp') or content_item.get('create_time') or content_item.get('time')
        if timestamp:
            # 确保返回毫秒级时间戳
            if isinstance(timestamp, str):
                # 如果是字符串，需要转换
                import time
                from datetime import datetime
                try:
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    return int(dt.timestamp() * 1000)
                except:
                    pass
            elif isinstance(timestamp, int):
                # 如果是秒级时间戳，转换为毫秒
                if timestamp < 10000000000:  # 小于10位数，可能是秒级
                    return timestamp * 1000
                return timestamp
        return None
    
    # 可选实现的方法
    async def smart_search_optimization(self, keyword: str, page: int) -> tuple:
        """智能搜索优化示例"""
        if not config.ENABLE_SMART_SEARCH:
            return False, {}
        
        # 示例：根据爬取进度调整搜索策略
        if page > 50:  # 如果已经爬取了很多页
            # 可以调整搜索参数，比如排序方式等
            return True, {'sort_type': 'time_descending'}
        
        return False, {}
    
    async def handle_empty_page(self, keyword: str, page: int) -> bool:
        """处理空页面的示例"""
        # 调用父类的默认实现
        return await super().handle_empty_page(keyword, page)
    
    async def process_crawl_batch(self, keyword: str, page: int, items: List[Dict]) -> List[Dict]:
        """批量处理数据的示例"""
        # 可以在这里进行数据清洗、格式化等处理
        processed_items = []
        
        for item in items:
            # 示例：添加爬取元数据
            item['crawl_keyword'] = keyword
            item['crawl_page'] = page
            item['crawl_time'] = int(time.time() * 1000)
            
            processed_items.append(item)
        
        return processed_items
    
    # 需要实现的抽象方法（基类要求）
    async def launch_browser(self, chromium, playwright_proxy, user_agent, headless=True):
        """启动浏览器 - 需要子类实现"""
        pass