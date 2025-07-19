"""
数据处理工具
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import time

from web.database.queries import DataQueryService, SearchFilters, ContentItem

logger = logging.getLogger(__name__)

class WebDataProcessor:
    """Web数据处理器"""
    
    def __init__(self):
        self.last_query_time = 0
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存
    
    def search_with_cache(self, filters: SearchFilters) -> Tuple[List[ContentItem], int, float]:
        """带缓存的搜索"""
        start_time = time.time()
        
        # 生成缓存键
        cache_key = self._generate_cache_key(filters)
        
        # 检查缓存
        if self._is_cache_valid(cache_key):
            logger.info("从缓存返回搜索结果")
            cached_data = self.cache[cache_key]
            query_time = time.time() - start_time
            return cached_data['results'], cached_data['total'], query_time
        
        # 执行搜索
        try:
            with DataQueryService() as service:
                results, total = service.search_content(filters)
                
                # 缓存结果
                self.cache[cache_key] = {
                    'results': results,
                    'total': total,
                    'timestamp': time.time()
                }
                
                query_time = time.time() - start_time
                logger.info(f"搜索完成，耗时: {query_time:.2f}秒，结果: {total}条")
                
                return results, total, query_time
                
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            query_time = time.time() - start_time
            return [], 0, query_time
    
    def get_platform_statistics(self) -> Dict[str, int]:
        """获取平台统计数据"""
        cache_key = "platform_stats"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            with DataQueryService() as service:
                stats = service.get_platform_stats()
                
                self.cache[cache_key] = {
                    'data': stats,
                    'timestamp': time.time()
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"获取平台统计失败: {e}")
            return {}
    
    def get_sentiment_statistics(self, filters: SearchFilters) -> Dict[str, int]:
        """获取情感统计数据"""
        cache_key = f"sentiment_stats_{self._generate_cache_key(filters)}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            with DataQueryService() as service:
                stats = service.get_sentiment_distribution(filters)
                
                self.cache[cache_key] = {
                    'data': stats,
                    'timestamp': time.time()
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"获取情感统计失败: {e}")
            return {'positive': 0, 'negative': 0, 'neutral': 0, 'unknown': 0}
    
    def get_recent_keywords(self, limit: int = 10) -> List[str]:
        """获取最近的关键词"""
        cache_key = f"recent_keywords_{limit}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            with DataQueryService() as service:
                keywords = service.get_recent_keywords(limit)
                
                self.cache[cache_key] = {
                    'data': keywords,
                    'timestamp': time.time()
                }
                
                return keywords
                
        except Exception as e:
            logger.error(f"获取最近关键词失败: {e}")
            return []
    
    def validate_search_filters(self, filters: SearchFilters) -> Tuple[bool, str]:
        """验证搜索筛选条件"""
        
        # 检查时间范围
        if filters.start_time and filters.end_time:
            if filters.start_time > filters.end_time:
                return False, "开始时间不能大于结束时间"
            
            # 检查时间范围是否过大（超过1年）
            if filters.end_time - filters.start_time > timedelta(days=365):
                return False, "时间范围不能超过1年"
        
        # 检查分页参数
        if filters.page < 1:
            return False, "页码必须大于0"
        
        if filters.page_size < 1 or filters.page_size > 100:
            return False, "每页大小必须在1-100之间"
        
        # 检查关键词长度
        if filters.keywords and len(filters.keywords) > 200:
            return False, "关键词长度不能超过200字符"
        
        return True, ""
    
    def _generate_cache_key(self, filters: SearchFilters) -> str:
        """生成缓存键"""
        key_parts = [
            f"platforms:{','.join(sorted(filters.platforms)) if filters.platforms else 'all'}",
            f"start:{filters.start_time.isoformat() if filters.start_time else 'none'}",
            f"end:{filters.end_time.isoformat() if filters.end_time else 'none'}",
            f"keywords:{filters.keywords or 'none'}",
            f"sentiment:{filters.sentiment or 'all'}",
            f"page:{filters.page}",
            f"size:{filters.page_size}",
            f"sort:{filters.sort_by}_{filters.sort_order}"
        ]
        return "|".join(key_parts)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self.cache:
            return False
        
        cache_time = self.cache[cache_key]['timestamp']
        return time.time() - cache_time < self.cache_ttl
    
    def clear_cache(self):
        """清除缓存"""
        self.cache.clear()
        logger.info("缓存已清除")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        valid_items = 0
        for key, data in self.cache.items():
            if time.time() - data['timestamp'] < self.cache_ttl:
                valid_items += 1
        
        return {
            'total_items': len(self.cache),
            'valid_items': valid_items,
            'cache_ttl': self.cache_ttl
        }

# 全局数据处理器实例
data_processor = WebDataProcessor()

def get_data_processor() -> WebDataProcessor:
    """获取数据处理器实例"""
    return data_processor