"""
数据查询逻辑
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import func, text, or_, and_
from sqlalchemy.orm import Session
from dataclasses import dataclass

from .connection import get_db_session, close_db_session
from .models import PLATFORM_MODELS, PLATFORM_NAMES, get_model_by_platform

logger = logging.getLogger(__name__)

@dataclass
class SearchFilters:
    """搜索筛选条件"""
    platforms: List[str] = None
    start_time: datetime = None
    end_time: datetime = None
    keywords: str = None
    sentiment: str = None
    page: int = 1
    page_size: int = 20
    sort_by: str = 'time'
    sort_order: str = 'desc'
    
    def __post_init__(self):
        if self.platforms is None:
            self.platforms = []
        if self.start_time is None:
            self.start_time = datetime.now() - timedelta(days=7)
        if self.end_time is None:
            self.end_time = datetime.now()

@dataclass
class ContentItem:
    """内容项目数据结构"""
    id: int
    platform: str
    platform_name: str
    content_id: str
    title: str
    content: str
    author_name: str
    publish_time: datetime
    interaction_count: int
    sentiment: str
    sentiment_score: float
    url: str
    
    @classmethod
    def from_model(cls, model_instance, platform: str):
        """从模型实例创建ContentItem"""
        # 获取统一的字段映射
        field_mapping = get_field_mapping(platform)
        
        # 处理发布时间字段
        publish_time_value = getattr(model_instance, field_mapping['publish_time'])
        if platform == 'tieba':
            # 贴吧的时间字段是字符串格式，需要特殊处理
            try:
                if isinstance(publish_time_value, str):
                    # 假设是 "YYYY-MM-DD HH:MM:SS" 格式
                    publish_time = datetime.strptime(publish_time_value, '%Y-%m-%d %H:%M:%S')
                else:
                    publish_time = datetime.now()
            except:
                publish_time = datetime.now()
        elif platform == 'zhihu':
            # 知乎的时间字段也是字符串格式
            try:
                if isinstance(publish_time_value, str):
                    publish_time = datetime.strptime(publish_time_value, '%Y-%m-%d %H:%M:%S')
                else:
                    publish_time = datetime.now()
            except:
                publish_time = datetime.now()
        else:
            # 其他平台使用时间戳
            try:
                publish_time = datetime.fromtimestamp(publish_time_value / 1000)
            except:
                publish_time = datetime.now()
        
        return cls(
            id=model_instance.id,
            platform=platform,
            platform_name=PLATFORM_NAMES.get(platform, platform),
            content_id=getattr(model_instance, field_mapping['content_id']),
            title=getattr(model_instance, field_mapping['title'], ''),
            content=getattr(model_instance, field_mapping['content'], ''),
            author_name=getattr(model_instance, field_mapping['author_name'], ''),
            publish_time=publish_time,
            interaction_count=get_interaction_count(model_instance, platform),
            sentiment=model_instance.get_sentiment(),
            sentiment_score=model_instance.get_sentiment_score(),
            url=getattr(model_instance, field_mapping['url'], '')
        )

def get_field_mapping(platform: str) -> Dict[str, str]:
    """获取平台字段映射"""
    mappings = {
        'xhs': {
            'content_id': 'note_id',
            'title': 'title',
            'content': 'desc',
            'author_name': 'nickname',
            'publish_time': 'time',
            'url': 'note_url'
        },
        'douyin': {
            'content_id': 'aweme_id',
            'title': 'title',
            'content': 'desc',
            'author_name': 'nickname',
            'publish_time': 'create_time',
            'url': 'aweme_url'
        },
        'kuaishou': {
            'content_id': 'video_id',
            'title': 'video_title',
            'content': 'video_desc',
            'author_name': 'user_name',
            'publish_time': 'create_time',
            'url': 'video_url'
        },
        'bilibili': {
            'content_id': 'video_id',
            'title': 'title',
            'content': 'desc',
            'author_name': 'nickname',
            'publish_time': 'create_time',
            'url': 'video_url'
        },
        'weibo': {
            'content_id': 'note_id',
            'title': 'content',  # 微博没有标题，使用内容
            'content': 'content',
            'author_name': 'nickname',
            'publish_time': 'create_time',
            'url': 'note_url'
        },
        'tieba': {
            'content_id': 'note_id',
            'title': 'title',
            'content': 'desc',
            'author_name': 'user_nickname',
            'publish_time': 'publish_time',
            'url': 'note_url'
        },
        'zhihu': {
            'content_id': 'content_id',
            'title': 'title',
            'content': 'desc',
            'author_name': 'user_nickname',
            'publish_time': 'created_time',
            'url': 'content_url'
        }
    }
    return mappings.get(platform, {})

def get_interaction_count(model_instance, platform: str) -> int:
    """获取互动数量总和"""
    try:
        if platform == 'xhs':
            liked = int(getattr(model_instance, 'liked_count', '0') or '0')
            collected = int(getattr(model_instance, 'collected_count', '0') or '0')
            comment = int(getattr(model_instance, 'comment_count', '0') or '0')
            return liked + collected + comment
        elif platform == 'douyin':
            liked = int(getattr(model_instance, 'liked_count', '0') or '0')
            comment = int(getattr(model_instance, 'comment_count', '0') or '0')
            share = int(getattr(model_instance, 'share_count', '0') or '0')
            return liked + comment + share
        elif platform == 'kuaishou':
            liked = int(getattr(model_instance, 'liked_count', '0') or '0')
            viewed = int(getattr(model_instance, 'viewd_count', '0') or '0')
            return liked + viewed // 100  # 播放量按百分之一计算，快手表中没有comment_count字段
        elif platform == 'bilibili':
            liked = int(getattr(model_instance, 'liked_count', '0') or '0')
            play = int(getattr(model_instance, 'video_play_count', '0') or '0')
            comment = int(getattr(model_instance, 'video_comment', '0') or '0')
            return liked + comment + play // 100  # 播放量按百分之一计算
        elif platform == 'weibo':
            reposts = getattr(model_instance, 'reposts_count', 0)
            comments = getattr(model_instance, 'comments_count', 0)
            attitudes = getattr(model_instance, 'attitudes_count', 0)
            return reposts + comments + attitudes
        elif platform == 'tieba':
            reply_num = getattr(model_instance, 'total_replay_num', 0) or 0
            return reply_num
        elif platform == 'zhihu':
            comment = getattr(model_instance, 'comment_count', 0) or 0
            voteup = getattr(model_instance, 'voteup_count', 0) or 0
            return comment + voteup
    except (ValueError, TypeError):
        return 0
    return 0

class DataQueryService:
    """数据查询服务"""
    
    def __init__(self):
        self.session: Optional[Session] = None
    
    def __enter__(self):
        self.session = get_db_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            close_db_session(self.session)
    
    def search_content(self, filters: SearchFilters) -> Tuple[List[ContentItem], int]:
        """搜索内容"""
        if not self.session:
            raise RuntimeError("数据库会话未初始化")
        
        all_results = []
        total_count = 0
        
        # 如果没有指定平台，查询所有平台
        platforms = filters.platforms if filters.platforms else list(PLATFORM_MODELS.keys())
        
        for platform in platforms:
            model = get_model_by_platform(platform)
            if not model:
                continue
            
            try:
                # 构建查询
                query = self.session.query(model)
                
                # 时间筛选
                time_field = get_field_mapping(platform)['publish_time']
                if platform in ['tieba', 'zhihu']:
                    # 对于时间字段是字符串的平台，暂时跳过时间筛选
                    pass
                else:
                    # 其他平台使用时间戳筛选
                    if filters.start_time:
                        start_ts = int(filters.start_time.timestamp() * 1000)
                        query = query.filter(getattr(model, time_field) >= start_ts)
                    
                    if filters.end_time:
                        end_ts = int(filters.end_time.timestamp() * 1000)
                        query = query.filter(getattr(model, time_field) <= end_ts)
                
                # 关键词搜索
                if filters.keywords:
                    field_mapping = get_field_mapping(platform)
                    title_field = field_mapping.get('title')
                    content_field = field_mapping.get('content')
                    
                    search_conditions = []
                    if title_field and hasattr(model, title_field):
                        search_conditions.append(getattr(model, title_field).contains(filters.keywords))
                    if content_field and hasattr(model, content_field):
                        search_conditions.append(getattr(model, content_field).contains(filters.keywords))
                    
                    if search_conditions:
                        query = query.filter(or_(*search_conditions))
                
                # 情感筛选
                if filters.sentiment and filters.sentiment != 'all':
                    if hasattr(model, 'analysis_info'):
                        query = query.filter(
                            func.json_extract(model.analysis_info, '$.sentiment') == filters.sentiment
                        )
                
                # 获取总数
                platform_count = query.count()
                total_count += platform_count
                
                # 排序
                time_field_obj = getattr(model, time_field)
                if filters.sort_order == 'desc':
                    query = query.order_by(time_field_obj.desc())
                else:
                    query = query.order_by(time_field_obj.asc())
                
                # 分页（暂时获取所有数据，后续在内存中分页）
                results = query.all()
                
                # 转换为ContentItem
                for result in results:
                    try:
                        content_item = ContentItem.from_model(result, platform)
                        all_results.append(content_item)
                    except Exception as e:
                        logger.warning(f"转换数据失败: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"查询平台 {platform} 数据失败: {e}")
                continue
        
        # 统一排序
        if filters.sort_by == 'time':
            all_results.sort(
                key=lambda x: x.publish_time,
                reverse=(filters.sort_order == 'desc')
            )
        elif filters.sort_by == 'interaction':
            all_results.sort(
                key=lambda x: x.interaction_count,
                reverse=(filters.sort_order == 'desc')
            )
        
        # 内存分页
        start_idx = (filters.page - 1) * filters.page_size
        end_idx = start_idx + filters.page_size
        paginated_results = all_results[start_idx:end_idx]
        
        return paginated_results, len(all_results)
    
    def get_platform_stats(self) -> Dict[str, int]:
        """获取平台统计"""
        if not self.session:
            raise RuntimeError("数据库会话未初始化")
        
        stats = {}
        platform_status = {}  # 记录每个平台的查询状态
        
        for platform, model in PLATFORM_MODELS.items():
            try:
                # 检查表是否存在
                table_name = model.__tablename__
                try:
                    # 尝试查询表结构来验证表是否存在
                    self.session.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
                    table_exists = True
                except Exception as table_check_error:
                    logger.warning(f"平台 {platform} 的表 {table_name} 不存在或无法访问: {table_check_error}")
                    table_exists = False
                    platform_status[platform] = f"表不存在: {table_check_error}"
                    stats[platform] = 0
                    continue
                
                if table_exists:
                    # 查询数据量
                    count = self.session.query(model).count()
                    stats[platform] = count
                    platform_status[platform] = f"查询成功: {count} 条记录"
                    logger.info(f"平台 {platform} 统计: {count} 条记录")
                
            except Exception as e:
                error_msg = f"查询失败: {str(e)}"
                logger.error(f"获取平台 {platform} 统计失败: {e}")
                platform_status[platform] = error_msg
                stats[platform] = 0
        
        # 记录总体统计结果
        total_count = sum(stats.values())
        successful_platforms = [p for p, status in platform_status.items() if "查询成功" in status]
        failed_platforms = [p for p, status in platform_status.items() if "查询成功" not in status]
        
        logger.info(f"平台统计完成 - 总数据量: {total_count}, 成功平台: {successful_platforms}, 失败平台: {failed_platforms}")
        
        # 将状态信息添加到stats中，供调试使用
        stats['_platform_status'] = platform_status
        stats['_summary'] = {
            'total_count': total_count,
            'successful_platforms': successful_platforms,
            'failed_platforms': failed_platforms
        }
        
        return stats
    
    def get_sentiment_distribution(self, filters: SearchFilters) -> Dict[str, int]:
        """获取情感分布"""
        if not self.session:
            raise RuntimeError("数据库会话未初始化")
        
        sentiment_stats = {'positive': 0, 'negative': 0, 'neutral': 0, 'unknown': 0}
        
        platforms = filters.platforms if filters.platforms else list(PLATFORM_MODELS.keys())
        
        for platform in platforms:
            model = get_model_by_platform(platform)
            if not model or not hasattr(model, 'analysis_info'):
                continue
            
            try:
                # 构建基础查询
                query = self.session.query(
                    func.json_extract(model.analysis_info, '$.sentiment').label('sentiment'),
                    func.count().label('count')
                )
                
                # 时间筛选
                time_field = get_field_mapping(platform)['publish_time']
                if filters.start_time:
                    start_ts = int(filters.start_time.timestamp() * 1000)
                    query = query.filter(getattr(model, time_field) >= start_ts)
                
                if filters.end_time:
                    end_ts = int(filters.end_time.timestamp() * 1000)
                    query = query.filter(getattr(model, time_field) <= end_ts)
                
                # 分组统计
                results = query.group_by(
                    func.json_extract(model.analysis_info, '$.sentiment')
                ).all()
                
                for sentiment, count in results:
                    if sentiment in sentiment_stats:
                        sentiment_stats[sentiment] += count
                    else:
                        sentiment_stats['unknown'] += count
                        
            except Exception as e:
                logger.error(f"获取平台 {platform} 情感分布失败: {e}")
                continue
        
        return sentiment_stats
    
    def get_recent_keywords(self, limit: int = 10) -> List[str]:
        """获取最近的搜索关键词"""
        if not self.session:
            raise RuntimeError("数据库会话未初始化")
        
        keywords = set()
        
        for platform, model in PLATFORM_MODELS.items():
            if not hasattr(model, 'source_keyword'):
                continue
            
            try:
                results = self.session.query(model.source_keyword).filter(
                    model.source_keyword.isnot(None)
                ).distinct().limit(limit).all()
                
                for (keyword,) in results:
                    if keyword:
                        keywords.update(keyword.split(','))
                        
            except Exception as e:
                logger.error(f"获取平台 {platform} 关键词失败: {e}")
                continue
        
        return list(keywords)[:limit]