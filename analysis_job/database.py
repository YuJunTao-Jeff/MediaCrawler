"""
数据库操作模块
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager

from .config import DATABASE_CONFIG, PLATFORM_TABLES
from .models import ContentItem, AnalysisResult


logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or DATABASE_CONFIG
        self.connection = None
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"],
                charset=self.config["charset"],
                cursorclass=DictCursor,
                autocommit=self.config.get("autocommit", True)
            )
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def disconnect(self):
        """断开数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("数据库连接已断开")
    
    @contextmanager
    def get_cursor(self):
        """获取数据库游标上下文管理器"""
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cursor:
                yield cursor
        except Exception as e:
            logger.error(f"数据库操作失败: {e}")
            if self.connection:
                self.connection.rollback()
            raise
    
    def get_unanalyzed_content(self, platform: str, limit: int = 10) -> List[ContentItem]:
        """获取未分析的内容"""
        if platform not in PLATFORM_TABLES:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = PLATFORM_TABLES[platform]
        main_table = config["main_table"]
        main_id_field = config["main_id_field"]
        content_fields = config["content_fields"]
        
        # 构建查询字段
        select_fields = [f"m.{main_id_field}"]
        for field in content_fields:
            # 处理MySQL保留字
            if field in ['desc', 'order', 'group', 'limit']:
                select_fields.append(f"m.`{field}`")
            else:
                select_fields.append(f"m.{field}")
        select_fields.append("m.add_ts")
        
        query = f"""
        SELECT {', '.join(select_fields)}
        FROM {main_table} m
        WHERE m.analysis_info IS NULL
        ORDER BY m.add_ts DESC
        LIMIT %s
        """
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (limit,))
                results = cursor.fetchall()
                
                content_items = []
                for row in results:
                    # 合并内容字段
                    content_parts = []
                    title = ""
                    
                    for field in content_fields:
                        value = row.get(field, "")
                        if value:
                            if field in ["title"]:
                                title = value
                            else:
                                content_parts.append(str(value))
                    
                    content_item = ContentItem(
                        platform=platform,
                        content_id=row[main_id_field],
                        title=title,
                        content="\n".join(content_parts),
                        create_time=row.get("create_time", 0)
                    )
                    content_items.append(content_item)
                
                logger.info(f"获取到 {len(content_items)} 条未分析的 {platform} 内容")
                return content_items
                
        except Exception as e:
            logger.error(f"获取未分析内容失败: {e}")
            raise
    
    def get_content_with_comments(self, platform: str, content_id: str) -> ContentItem:
        """获取带评论的内容"""
        if platform not in PLATFORM_TABLES:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = PLATFORM_TABLES[platform]
        main_table = config["main_table"]
        comment_table = config["comment_table"]
        main_id_field = config["main_id_field"]
        comment_id_field = config["comment_id_field"]
        content_fields = config["content_fields"]
        comment_content_field = config["comment_content_field"]
        parent_id_field = config["parent_id_field"]
        
        # 获取主内容
        main_query = f"""
        SELECT {main_id_field}, {', '.join(content_fields)}, create_time
        FROM {main_table}
        WHERE {main_id_field} = %s
        """
        
        # 获取评论
        comment_query = f"""
        SELECT {comment_id_field}, {comment_content_field}, create_time
        FROM {comment_table}
        WHERE {parent_id_field} = %s
        ORDER BY create_time DESC
        LIMIT 20
        """
        
        try:
            with self.get_cursor() as cursor:
                # 获取主内容
                cursor.execute(main_query, (content_id,))
                main_result = cursor.fetchone()
                
                if not main_result:
                    raise ValueError(f"未找到内容ID: {content_id}")
                
                # 合并内容字段
                content_parts = []
                title = ""
                
                for field in content_fields:
                    value = main_result.get(field, "")
                    if value:
                        if field in ["title"]:
                            title = value
                        else:
                            content_parts.append(str(value))
                
                # 获取评论
                cursor.execute(comment_query, (content_id,))
                comment_results = cursor.fetchall()
                
                comments = []
                for comment in comment_results:
                    comments.append({
                        "comment_id": comment[comment_id_field],
                        "content": comment[comment_content_field],
                        "create_time": comment.get("create_time", 0)
                    })
                
                content_item = ContentItem(
                    platform=platform,
                    content_id=content_id,
                    title=title,
                    content="\n".join(content_parts),
                    comments=comments,
                    create_time=main_result.get("create_time", 0)
                )
                
                logger.info(f"获取到内容 {content_id} 及其 {len(comments)} 条评论")
                return content_item
                
        except Exception as e:
            logger.error(f"获取内容和评论失败: {e}")
            raise
    
    def batch_get_content_with_comments(self, platform: str, limit: int = 10) -> List[ContentItem]:
        """批量获取带评论的内容"""
        # 先获取未分析的内容ID
        unanalyzed_items = self.get_unanalyzed_content(platform, limit)
        
        # 为每个内容获取评论
        result_items = []
        for item in unanalyzed_items:
            try:
                full_item = self.get_content_with_comments(platform, item.content_id)
                result_items.append(full_item)
            except Exception as e:
                logger.warning(f"获取内容 {item.content_id} 的评论失败: {e}")
                # 如果获取评论失败，使用原始内容
                result_items.append(item)
        
        return result_items
    
    def update_analysis_result(self, platform: str, content_id: str, result: AnalysisResult) -> bool:
        """更新分析结果"""
        if platform not in PLATFORM_TABLES:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = PLATFORM_TABLES[platform]
        main_table = config["main_table"]
        main_id_field = config["main_id_field"]
        
        query = f"""
        UPDATE {main_table}
        SET analysis_info = %s, last_modify_ts = %s
        WHERE {main_id_field} = %s
        """
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, (
                    result.to_json(),
                    result.analysis_timestamp,
                    content_id
                ))
                
                if cursor.rowcount > 0:
                    logger.info(f"更新分析结果成功: {platform} - {content_id}")
                    return True
                else:
                    logger.warning(f"未找到要更新的记录: {platform} - {content_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"更新分析结果失败: {e}")
            return False
    
    def batch_update_analysis_results(self, platform: str, results: List[Tuple[str, AnalysisResult]]) -> int:
        """批量更新分析结果"""
        if platform not in PLATFORM_TABLES:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = PLATFORM_TABLES[platform]
        main_table = config["main_table"]
        main_id_field = config["main_id_field"]
        
        query = f"""
        UPDATE {main_table}
        SET analysis_info = %s, last_modify_ts = %s
        WHERE {main_id_field} = %s
        """
        
        try:
            with self.get_cursor() as cursor:
                update_data = []
                for content_id, result in results:
                    update_data.append((
                        result.to_json(),
                        result.analysis_timestamp,
                        content_id
                    ))
                
                cursor.executemany(query, update_data)
                updated_count = cursor.rowcount
                
                logger.info(f"批量更新分析结果成功: {updated_count} 条记录")
                return updated_count
                
        except Exception as e:
            logger.error(f"批量更新分析结果失败: {e}")
            return 0
    
    def get_analysis_stats(self, platform: str) -> Dict[str, Any]:
        """获取分析统计信息"""
        if platform not in PLATFORM_TABLES:
            raise ValueError(f"不支持的平台: {platform}")
        
        config = PLATFORM_TABLES[platform]
        main_table = config["main_table"]
        
        query = f"""
        SELECT 
            COUNT(*) as total_count,
            SUM(CASE WHEN analysis_info IS NOT NULL THEN 1 ELSE 0 END) as analyzed_count,
            SUM(CASE WHEN analysis_info IS NULL THEN 1 ELSE 0 END) as unanalyzed_count
        FROM {main_table}
        """
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                
                stats = {
                    "platform": platform,
                    "total_count": result["total_count"],
                    "analyzed_count": result["analyzed_count"],
                    "unanalyzed_count": result["unanalyzed_count"],
                    "analysis_rate": result["analyzed_count"] / result["total_count"] if result["total_count"] > 0 else 0
                }
                
                logger.info(f"获取 {platform} 分析统计: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"获取分析统计失败: {e}")
            return {}