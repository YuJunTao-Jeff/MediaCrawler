"""
数据查询逻辑
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import func, text, or_, and_
from sqlalchemy.orm import Session
from dataclasses import dataclass

from .connection import get_db_session, close_db_session
from .models import PLATFORM_MODELS, PLATFORM_NAMES, get_model_by_platform

logger = logging.getLogger(__name__)

def parse_relative_time(time_str: str) -> Optional[datetime]:
    """解析相对时间字符串，如'3天前', '2小时前'等"""
    if not time_str:
        return None
        
    time_str = time_str.strip()
    now = datetime.now()
    
    # 匹配模式：数字 + 时间单位 + "前"
    patterns = [
        (r'(\d+)年前', 'years'),
        (r'(\d+)个月前', 'months'), 
        (r'(\d+)月前', 'months'),
        (r'(\d+)天前', 'days'),
        (r'(\d+)小时前', 'hours'),
        (r'(\d+)分钟前', 'minutes'),
        (r'(\d+)秒前', 'seconds'),
    ]
    
    for pattern, unit in patterns:
        match = re.search(pattern, time_str)
        if match:
            num = int(match.group(1))
            if unit == 'years':
                return now - timedelta(days=num * 365)
            elif unit == 'months':
                return now - timedelta(days=num * 30)
            elif unit == 'days':
                return now - timedelta(days=num)
            elif unit == 'hours':
                return now - timedelta(hours=num)
            elif unit == 'minutes':
                return now - timedelta(minutes=num)
            elif unit == 'seconds':
                return now - timedelta(seconds=num)
    
    # 特殊情况
    if '刚刚' in time_str or '刚才' in time_str:
        return now - timedelta(minutes=1)
    elif '昨天' in time_str:
        return now - timedelta(days=1)
    elif '前天' in time_str:
        return now - timedelta(days=2)
    
    return None

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
    noise_filter: str = 'all'  # 噪音过滤: all, filter_noise, only_noise
    
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
    _model_instance: Any = None
    
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
                if isinstance(publish_time_value, str) and publish_time_value.strip():
                    # 尝试多种时间格式
                    time_formats = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%d %H:%M',
                        '%Y-%m-%d',
                        '%m-%d %H:%M',
                        '%Y年%m月%d日 %H:%M:%S',
                        '%Y年%m月%d日 %H:%M',
                        '%Y年%m月%d日',
                        '%m月%d日 %H:%M',
                        '%m月%d日',
                    ]
                    
                    parsed = False
                    for time_format in time_formats:
                        try:
                            publish_time = datetime.strptime(publish_time_value.strip(), time_format)
                            # 如果没有年份，添加当前年份
                            if 'Y' not in time_format:
                                current_year = datetime.now().year
                                publish_time = publish_time.replace(year=current_year)
                            parsed = True
                            break
                        except:
                            continue
                    
                    if not parsed:
                        # 尝试解析相对时间
                        publish_time = parse_relative_time(publish_time_value)
                        if publish_time is None:
                            # 如果都解析失败，返回一个较早的默认时间
                            publish_time = datetime(2020, 1, 1)
                else:
                    publish_time = datetime(2020, 1, 1)
            except:
                publish_time = datetime(2020, 1, 1)
        elif platform == 'zhihu':
            # 知乎的时间字段是Unix时间戳字符串格式
            try:
                if isinstance(publish_time_value, str) and publish_time_value.strip():
                    # 首先尝试Unix时间戳
                    try:
                        timestamp = int(publish_time_value.strip())
                        # 知乎使用10位时间戳（秒级）
                        if len(str(timestamp)) == 10:
                            publish_time = datetime.fromtimestamp(timestamp)
                        # 如果是13位时间戳（毫秒级）
                        elif len(str(timestamp)) == 13:
                            publish_time = datetime.fromtimestamp(timestamp / 1000)
                        else:
                            # 尝试其他格式
                            raise ValueError("不是标准时间戳格式")
                    except (ValueError, OSError):
                        # 如果不是时间戳，尝试其他时间格式
                        time_formats = [
                            '%Y-%m-%d %H:%M:%S',
                            '%Y-%m-%d',
                            '%Y-%m-%d %H:%M',
                            '%m-%d %H:%M',
                            '%Y年%m月%d日 %H:%M',
                            '%Y年%m月%d日',
                        ]
                        
                        parsed = False
                        for time_format in time_formats:
                            try:
                                publish_time = datetime.strptime(publish_time_value.strip(), time_format)
                                parsed = True
                                break
                            except:
                                continue
                        
                        if not parsed:
                            # 尝试解析相对时间
                            publish_time = parse_relative_time(publish_time_value)
                            if publish_time is None:
                                publish_time = datetime(2020, 1, 1)
                else:
                    publish_time = datetime(2020, 1, 1)
            except:
                publish_time = datetime(2020, 1, 1)
        elif platform == 'news':
            # 新闻的时间字段是datetime格式
            try:
                if publish_time_value:
                    publish_time = publish_time_value
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
        
        content_item = cls(
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
        # 添加模型实例引用以便获取analysis_info
        content_item._model_instance = model_instance
        return content_item

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
            'title': 'title',  # 使用实际表中的字段名
            'content': 'desc',  # 使用实际表中的字段名
            'author_name': 'nickname',  # 使用实际表中的字段名
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
        },
        'news': {
            'content_id': 'article_id',
            'title': 'title',
            'content': 'summary',  # 使用摘要作为内容，如果需要完整内容可改为'content'
            'author_name': 'source_site',  # 使用来源网站作为作者
            'publish_time': 'publish_date',
            'url': 'source_url'
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
            liked = int(getattr(model_instance, 'liked_count', '0') or '0')
            comments = int(getattr(model_instance, 'comments_count', '0') or '0')
            shared = int(getattr(model_instance, 'shared_count', '0') or '0')
            return liked + comments + shared
        elif platform == 'tieba':
            reply_num = getattr(model_instance, 'total_replay_num', 0) or 0
            return reply_num
        elif platform == 'zhihu':
            comment = getattr(model_instance, 'comment_count', 0) or 0
            voteup = getattr(model_instance, 'voteup_count', 0) or 0
            return comment + voteup
        elif platform == 'news':
            # 新闻文章没有互动计数，返回字数作为参考
            word_count = getattr(model_instance, 'word_count', 0) or 0
            return word_count // 100  # 字数除以100作为热度指标
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
                if platform == 'tieba':
                    # 贴吧时间筛选：尝试解析字符串时间进行筛选
                    if filters.start_time or filters.end_time:
                        # 获取所有记录，然后在应用层进行时间筛选
                        # 这样虽然效率较低，但能正确处理各种时间格式
                        pass  # 在后续处理中进行时间筛选
                elif platform == 'zhihu':
                    # 知乎时间筛选：类似处理
                    if filters.start_time or filters.end_time:
                        pass  # 在后续处理中进行时间筛选
                elif platform == 'news':
                    # news平台使用datetime字段
                    if filters.start_time:
                        query = query.filter(getattr(model, time_field) >= filters.start_time)
                    if filters.end_time:
                        query = query.filter(getattr(model, time_field) <= filters.end_time)
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
                    
                    # 支持逗号和空格分割的关键词
                    keywords = []
                    for part in filters.keywords.replace(',', ' ').split():
                        keyword = part.strip()
                        if keyword:
                            keywords.append(keyword)
                    
                    # 为每个关键词创建搜索条件
                    keyword_conditions = []
                    for keyword in keywords:
                        search_conditions = []
                        if title_field and hasattr(model, title_field):
                            search_conditions.append(getattr(model, title_field).contains(keyword))
                        if content_field and hasattr(model, content_field):
                            search_conditions.append(getattr(model, content_field).contains(keyword))
                        
                        if search_conditions:
                            keyword_conditions.append(or_(*search_conditions))
                    
                    if keyword_conditions:
                        # 使用OR条件，只要包含任一关键词即可
                        query = query.filter(or_(*keyword_conditions))
                
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
                        
                        # 对贴吧和知乎进行应用层时间筛选
                        if platform in ['tieba', 'zhihu'] and (filters.start_time or filters.end_time):
                            if filters.start_time and content_item.publish_time < filters.start_time:
                                continue
                            if filters.end_time and content_item.publish_time > filters.end_time:
                                continue
                        
                        # 噪音过滤逻辑 - 基于analysis_info中的相关性评分
                        if filters.noise_filter != 'all':
                            relevance_score = None
                            if hasattr(content_item, '_model_instance') and content_item._model_instance:
                                analysis_info = content_item._model_instance.get_analysis_info()
                                if analysis_info and 'relevance_score' in analysis_info:
                                    try:
                                        relevance_score = float(analysis_info['relevance_score'])
                                    except (ValueError, TypeError):
                                        relevance_score = None
                            
                            # 根据过滤选项决定是否包含此条结果
                            if filters.noise_filter == 'filter_noise':
                                # 过滤噪音：只保留相关性评分 > 0.6 的内容
                                if relevance_score is None or relevance_score <= 0.6:
                                    continue
                            elif filters.noise_filter == 'only_noise':
                                # 仅显示噪音：只保留相关性评分 <= 0.6 的内容或无评分的内容
                                if relevance_score is not None and relevance_score > 0.6:
                                    continue
                        
                        all_results.append(content_item)
                    except Exception as e:
                        logger.warning(f"转换数据失败: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"查询平台 {platform} 数据失败: {e}")
                continue
        
        # 去重逻辑 - 基于content_id去除重复数据
        seen_content_ids = set()
        unique_results = []
        for result in all_results:
            content_key = f"{result.platform}_{result.content_id}"
            if content_key not in seen_content_ids:
                seen_content_ids.add(content_key)
                unique_results.append(result)
        
        # 统一排序
        if filters.sort_by == 'time':
            unique_results.sort(
                key=lambda x: x.publish_time,
                reverse=(filters.sort_order == 'desc')
            )
        elif filters.sort_by == 'interaction':
            unique_results.sort(
                key=lambda x: x.interaction_count,
                reverse=(filters.sort_order == 'desc')
            )
        
        # 内存分页
        start_idx = (filters.page - 1) * filters.page_size
        end_idx = start_idx + filters.page_size
        paginated_results = unique_results[start_idx:end_idx]
        
        return paginated_results, len(unique_results)
    
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
                # 使用MySQL兼容的JSON语法
                query = self.session.query(
                    func.JSON_EXTRACT(model.analysis_info, '$.sentiment').label('sentiment'),
                    func.count().label('count')
                )
                
                # 关键词筛选
                if filters.keywords:
                    field_mapping = get_field_mapping(platform)
                    # 支持逗号和空格分割的关键词
                    keywords = []
                    for part in filters.keywords.replace(',', ' ').split():
                        keywords.append(part.strip())
                    
                    keyword_conditions = []
                    for keyword in keywords:
                        keyword = keyword.strip()
                        if keyword:
                            # 在标题和内容中搜索关键词
                            title_field = field_mapping.get('title')
                            content_field = field_mapping.get('content')
                            
                            conditions = []
                            if title_field and hasattr(model, title_field):
                                conditions.append(getattr(model, title_field).like(f'%{keyword}%'))
                            if content_field and hasattr(model, content_field):
                                conditions.append(getattr(model, content_field).like(f'%{keyword}%'))
                            
                            if conditions:
                                keyword_conditions.append(or_(*conditions))
                    
                    if keyword_conditions:
                        query = query.filter(or_(*keyword_conditions))
                
                # 时间筛选
                time_field = get_field_mapping(platform)['publish_time']
                if filters.start_time:
                    start_ts = int(filters.start_time.timestamp() * 1000)
                    query = query.filter(getattr(model, time_field) >= start_ts)
                
                if filters.end_time:
                    end_ts = int(filters.end_time.timestamp() * 1000)
                    query = query.filter(getattr(model, time_field) <= end_ts)
                
                # 过滤掉analysis_info为NULL的记录
                query = query.filter(model.analysis_info.isnot(None))
                
                # 分组统计
                results = query.group_by(
                    func.JSON_EXTRACT(model.analysis_info, '$.sentiment')
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