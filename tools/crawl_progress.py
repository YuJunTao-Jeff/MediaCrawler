# -*- coding: utf-8 -*-
"""
断点续爬进度管理器
"""
import json
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date

import config
from tools import utils
from var import media_crawler_db_var


class CrawlProgressManager:
    """爬取进度管理器"""
    
    def __init__(self, platform: str, task_id: Optional[str] = None):
        self.platform = platform
        self.task_id = task_id or self._generate_task_id()
        self.db = None
        self.current_task = None
        self.keyword_progress = {}
        
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        timestamp = str(int(time.time() * 1000))
        platform_hash = hashlib.md5(self.platform.encode()).hexdigest()[:8]
        return f"{self.platform}_{platform_hash}_{timestamp}"
    
    async def initialize(self) -> None:
        """初始化进度管理器"""
        self.db = media_crawler_db_var.get()
        if not self.db:
            raise Exception("Database connection not available")
        
        # 创建或获取任务记录
        await self._init_task_record()
        
        # 加载已有进度
        await self._load_keyword_progress()
    
    async def _init_task_record(self) -> None:
        """初始化任务记录"""
        current_time = int(time.time() * 1000)
        
        # 检查是否已存在任务
        existing_task = await self.db.query(
            "SELECT * FROM crawl_task WHERE task_id = %s",
            self.task_id
        )
        
        if existing_task:
            self.current_task = existing_task[0]
            # 更新任务状态为运行中
            await self.db.execute(
                "UPDATE crawl_task SET status = 'running', last_update_time = %s WHERE task_id = %s",
                current_time, self.task_id
            )
        else:
            # 创建新任务
            keywords = config.KEYWORDS.split(',') if config.KEYWORDS else []
            config_snapshot = json.dumps({
                'PLATFORM': config.PLATFORM,
                'CRAWLER_TYPE': config.CRAWLER_TYPE,
                'CRAWLER_MAX_NOTES_COUNT': config.CRAWLER_MAX_NOTES_COUNT,
                'START_PAGE': config.START_PAGE,
                'ENABLE_GET_COMMENTS': config.ENABLE_GET_COMMENTS,
                'SAVE_DATA_OPTION': config.SAVE_DATA_OPTION
            }, ensure_ascii=False)
            
            await self.db.execute(
                """INSERT INTO crawl_task 
                   (task_id, platform, crawler_type, keywords, total_keywords, 
                    completed_keywords, status, start_time, last_update_time, config_snapshot)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                self.task_id, self.platform, config.CRAWLER_TYPE, 
                config.KEYWORDS, len(keywords), 0, 'running', 
                current_time, current_time, config_snapshot
            )
            
            self.current_task = {
                'task_id': self.task_id,
                'platform': self.platform,
                'total_keywords': len(keywords),
                'completed_keywords': 0,
                'status': 'running'
            }
    
    async def _load_keyword_progress(self) -> None:
        """加载关键词进度"""
        progress_records = await self.db.query(
            "SELECT * FROM keyword_progress WHERE task_id = %s",
            self.task_id
        )
        
        for record in progress_records:
            self.keyword_progress[record['keyword']] = {
                'current_page': record['current_page'],
                'total_pages': record['total_pages'],
                'items_count': record['items_count'],
                'last_item_time': record['last_item_time'],
                'last_item_id': record['last_item_id'],
                'status': record['status']
            }
    
    async def get_resume_page(self, keyword: str) -> int:
        """获取续爬起始页"""
        if not config.ENABLE_RESUME_CRAWL:
            return config.START_PAGE
        
        progress = self.keyword_progress.get(keyword)
        if not progress:
            return config.START_PAGE
        
        # 如果已完成，返回一个很大的数字表示跳过
        if progress['status'] == 'completed':
            return 999999
        
        # 从上次中断的页面开始
        resume_page = progress['current_page']
        
        utils.logger.info(f"[CrawlProgressManager] Resume crawling keyword '{keyword}' from page {resume_page}")
        return resume_page
    
    async def should_skip_item(self, item_id: str, item_timestamp: int, keyword: str) -> bool:
        """判断是否应该跳过该条目"""
        if not config.ENABLE_RESUME_CRAWL:
            return False
        
        progress = self.keyword_progress.get(keyword)
        if not progress:
            return False
        
        # 如果时间戳早于上次记录的时间，跳过
        if progress['last_item_time'] and item_timestamp <= progress['last_item_time']:
            return True
        
        # 如果ID相同，跳过
        if progress['last_item_id'] and item_id == progress['last_item_id']:
            return True
        
        return False
    
    async def update_keyword_progress(self, keyword: str, page: int, items_count: int, 
                                    last_item_id: Optional[str] = None, last_item_time: Optional[int] = None) -> None:
        """更新关键词进度"""
        current_time = int(time.time() * 1000)
        
        # 更新内存中的进度
        if keyword not in self.keyword_progress:
            self.keyword_progress[keyword] = {
                'current_page': page,
                'total_pages': None,
                'items_count': 0,
                'last_item_time': None,
                'last_item_id': None,
                'status': 'running'
            }
        
        progress = self.keyword_progress[keyword]
        progress['current_page'] = page
        progress['items_count'] += items_count
        
        if last_item_id:
            progress['last_item_id'] = last_item_id
        if last_item_time:
            progress['last_item_time'] = last_item_time
        
        # 更新数据库
        await self.db.execute(
            """INSERT INTO keyword_progress 
               (task_id, keyword, platform, current_page, items_count, 
                last_item_time, last_item_id, status, start_time, last_update_time)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               current_page = VALUES(current_page),
               items_count = VALUES(items_count),
               last_item_time = VALUES(last_item_time),
               last_item_id = VALUES(last_item_id),
               last_update_time = VALUES(last_update_time)""",
            self.task_id, keyword, self.platform, page, progress['items_count'],
            last_item_time, last_item_id, 'running', current_time, current_time
        )
    
    async def mark_keyword_completed(self, keyword: str) -> None:
        """标记关键词完成"""
        current_time = int(time.time() * 1000)
        
        # 更新内存状态
        if keyword in self.keyword_progress:
            self.keyword_progress[keyword]['status'] = 'completed'
        
        # 更新数据库
        await self.db.execute(
            """UPDATE keyword_progress 
               SET status = 'completed', completion_time = %s, last_update_time = %s
               WHERE task_id = %s AND keyword = %s""",
            current_time, current_time, self.task_id, keyword
        )
        
        # 更新任务完成进度
        completed_count = sum(1 for p in self.keyword_progress.values() if p['status'] == 'completed')
        await self.db.execute(
            """UPDATE crawl_task 
               SET completed_keywords = %s, last_update_time = %s
               WHERE task_id = %s""",
            completed_count, current_time, self.task_id
        )
        
        utils.logger.info(f"[CrawlProgressManager] Keyword '{keyword}' completed")
    
    async def should_stop_crawling(self, keyword: str, page: int) -> bool:
        """判断是否应该停止爬取"""
        if not config.ENABLE_RESUME_CRAWL:
            return False
        
        # 检查是否连续多页没有新内容
        progress = self.keyword_progress.get(keyword)
        if not progress:
            return False
        
        # 如果已经超过配置的最大页数
        max_pages = config.CRAWLER_MAX_NOTES_COUNT // 20  # 假设每页20条
        if page > max_pages:
            await self.mark_keyword_completed(keyword)
            return True
        
        return False
    
    async def save_checkpoint(self, keyword: str, page: int, checkpoint_data: Dict[str, Any]) -> None:
        """保存检查点"""
        current_time = int(time.time() * 1000)
        
        # 计算数据哈希
        data_hash = hashlib.md5(json.dumps(checkpoint_data, sort_keys=True).encode()).hexdigest()
        
        await self.db.execute(
            """INSERT INTO crawl_checkpoints 
               (task_id, keyword, platform, page_number, checkpoint_data, 
                items_processed, last_item_hash, created_time)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               checkpoint_data = VALUES(checkpoint_data),
               items_processed = VALUES(items_processed),
               last_item_hash = VALUES(last_item_hash),
               created_time = VALUES(created_time)""",
            (self.task_id, keyword, self.platform, page, 
             json.dumps(checkpoint_data), len(checkpoint_data.get('items', [])), 
             data_hash, current_time)
        )
    
    async def get_checkpoint(self, keyword: str, page: int) -> Optional[Dict[str, Any]]:
        """获取检查点"""
        result = await self.db.query(
            """SELECT checkpoint_data FROM crawl_checkpoints 
               WHERE task_id = %s AND keyword = %s AND page_number = %s""",
            self.task_id, keyword, page
        )
        
        if result:
            return json.loads(result[0]['checkpoint_data'])
        return None
    
    async def update_statistics(self, total_items: int, new_items: int, 
                              duplicate_items: int, failed_items: int) -> None:
        """更新统计信息"""
        current_time = int(time.time() * 1000)
        stat_date = date.today()
        
        await self.db.execute(
            """INSERT INTO crawl_statistics 
               (task_id, platform, stat_date, total_items, new_items, 
                duplicate_items, failed_items, create_time, update_time)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               total_items = VALUES(total_items),
               new_items = VALUES(new_items),
               duplicate_items = VALUES(duplicate_items),
               failed_items = VALUES(failed_items),
               update_time = VALUES(update_time)""",
            self.task_id, self.platform, stat_date, total_items, new_items,
            duplicate_items, failed_items, current_time, current_time
        )
    
    async def get_task_summary(self) -> Dict[str, Any]:
        """获取任务摘要"""
        # 获取任务信息
        task_info = await self.db.query(
            "SELECT * FROM crawl_task WHERE task_id = %s",
            self.task_id
        )
        
        # 获取关键词进度
        keyword_progress = await self.db.query(
            "SELECT * FROM keyword_progress WHERE task_id = %s",
            self.task_id
        )
        
        # 获取统计信息
        stats = await self.db.query(
            "SELECT * FROM crawl_statistics WHERE task_id = %s ORDER BY stat_date DESC LIMIT 1",
            self.task_id
        )
        
        return {
            'task_info': task_info[0] if task_info else None,
            'keyword_progress': keyword_progress,
            'statistics': stats[0] if stats else None
        }
    
    async def reset_progress(self, keyword: str = None) -> None:
        """重置进度"""
        if keyword:
            # 重置特定关键词
            await self.db.execute(
                "DELETE FROM keyword_progress WHERE task_id = %s AND keyword = %s",
                (self.task_id, keyword)
            )
            await self.db.execute(
                "DELETE FROM crawl_checkpoints WHERE task_id = %s AND keyword = %s",
                (self.task_id, keyword)
            )
            if keyword in self.keyword_progress:
                del self.keyword_progress[keyword]
        else:
            # 重置整个任务
            await self.db.execute(
                "DELETE FROM keyword_progress WHERE task_id = %s",
                self.task_id
            )
            await self.db.execute(
                "DELETE FROM crawl_checkpoints WHERE task_id = %s",
                self.task_id
            )
            await self.db.execute(
                "DELETE FROM crawl_statistics WHERE task_id = %s",
                self.task_id
            )
            await self.db.execute(
                "DELETE FROM crawl_task WHERE task_id = %s",
                self.task_id
            )
            self.keyword_progress.clear()
    
    async def cleanup(self) -> None:
        """清理资源"""
        # 标记任务状态
        if self.current_task:
            current_time = int(time.time() * 1000)
            await self.db.execute(
                "UPDATE crawl_task SET status = 'completed', last_update_time = %s WHERE task_id = %s",
                (current_time, self.task_id)
            )