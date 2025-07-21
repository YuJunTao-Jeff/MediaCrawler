"""
数据库模型定义
"""

from sqlalchemy import Column, Integer, String, Text, BigInteger, DateTime, JSON
from .connection import Base
from datetime import datetime
from typing import Dict, Any, Optional
import json

class BaseModel:
    """所有模型的基类"""
    id = Column(Integer, primary_key=True, autoincrement=True)
    add_ts = Column(BigInteger, nullable=False)
    last_modify_ts = Column(BigInteger, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result
    
    def get_analysis_info(self) -> Optional[Dict]:
        """获取分析信息"""
        if hasattr(self, 'analysis_info') and self.analysis_info:
            if isinstance(self.analysis_info, str):
                try:
                    return json.loads(self.analysis_info)
                except:
                    return None
            return self.analysis_info
        return None
    
    def get_sentiment(self) -> str:
        """获取情感倾向"""
        analysis = self.get_analysis_info()
        if analysis and 'sentiment' in analysis:
            return analysis['sentiment']
        return 'unknown'
    
    def get_sentiment_score(self) -> float:
        """获取情感评分"""
        analysis = self.get_analysis_info()
        if analysis and 'sentiment_score' in analysis:
            return float(analysis['sentiment_score'])
        return 0.0

class XhsNote(Base, BaseModel):
    """小红书笔记模型"""
    __tablename__ = 'xhs_note'
    
    note_id = Column(String(64), nullable=False, index=True)
    type = Column(String(16), nullable=False)
    title = Column(String(255), nullable=False)
    desc = Column(Text)
    time = Column(BigInteger, nullable=False)
    last_update_time = Column(BigInteger, nullable=False)
    user_id = Column(String(64), nullable=False, index=True)
    nickname = Column(String(64), nullable=False)
    avatar = Column(Text)
    liked_count = Column(String(16), nullable=False)
    collected_count = Column(String(16), nullable=False)
    comment_count = Column(String(16), nullable=False)
    share_count = Column(String(16), nullable=False)
    image_list = Column(Text)
    video_url = Column(Text)
    tag_list = Column(Text)
    note_url = Column(String(512), nullable=False)
    source_keyword = Column(String(255))
    analysis_info = Column(JSON)

class DouyinAweme(Base, BaseModel):
    """抖音视频模型"""
    __tablename__ = 'douyin_aweme'
    
    aweme_id = Column(String(64), nullable=False, index=True)
    aweme_type = Column(String(16), nullable=False)
    title = Column(String(1024), nullable=True)
    desc = Column(Text)
    create_time = Column(BigInteger, nullable=False)
    user_id = Column(String(64), nullable=True, index=True)
    sec_uid = Column(String(128), nullable=True)
    short_user_id = Column(String(64), nullable=True)
    user_unique_id = Column(String(64), nullable=True)
    user_signature = Column(String(500), nullable=True)
    nickname = Column(String(64), nullable=True)
    avatar = Column(String(255), nullable=True)
    liked_count = Column(String(16), nullable=True)
    comment_count = Column(String(16), nullable=True)
    share_count = Column(String(16), nullable=True)
    collected_count = Column(String(16), nullable=True)  # 修正字段名：collect_count -> collected_count
    aweme_url = Column(String(255), nullable=True)
    source_keyword = Column(String(255))
    analysis_info = Column(JSON)

class KuaishousVideo(Base, BaseModel):
    """快手视频模型"""
    __tablename__ = 'kuaishou_video'
    
    video_id = Column(String(64), nullable=False, index=True)
    video_type = Column(String(16), nullable=True)  # 使用实际表中的字段
    title = Column(String(500), nullable=True)  # 使用实际表中的字段名
    desc = Column(Text)
    create_time = Column(BigInteger, nullable=False)
    user_id = Column(String(64), nullable=True, index=True)
    nickname = Column(String(64), nullable=True)  # 使用实际表中的字段名
    avatar = Column(String(255), nullable=True)  # 使用实际表中的字段名
    liked_count = Column(String(16), nullable=True)
    viewd_count = Column(String(16), nullable=True)
    video_url = Column(String(512), nullable=True)  # 使用实际表中的字段长度
    video_cover_url = Column(String(512), nullable=True)  # 使用实际表中的字段长度
    video_play_url = Column(String(512), nullable=True)  # 新增实际表中的字段
    source_keyword = Column(String(255))
    analysis_info = Column(JSON)

class BilibiliVideo(Base, BaseModel):
    """哔哩哔哩视频模型"""
    __tablename__ = 'bilibili_video'
    
    video_id = Column(String(64), nullable=False, index=True)
    video_type = Column(String(16), nullable=False)
    title = Column(String(500), nullable=False)
    desc = Column(Text)
    create_time = Column(BigInteger, nullable=False)
    user_id = Column(String(64), nullable=False, index=True)
    nickname = Column(String(64), nullable=False)
    avatar = Column(Text)
    liked_count = Column(String(16), nullable=False)
    video_play_count = Column(String(16), nullable=False)
    video_danmaku = Column(String(16), nullable=False)
    video_comment = Column(String(16), nullable=False)
    video_url = Column(String(255), nullable=False)
    video_cover_url = Column(Text)
    source_keyword = Column(String(255))
    analysis_info = Column(JSON)

class WeiboNote(Base, BaseModel):
    """微博内容模型"""
    __tablename__ = 'weibo_note'
    
    note_id = Column(String(64), nullable=False, index=True)
    content = Column(Text)
    create_time = Column(BigInteger, nullable=False)
    create_date_time = Column(String(32), nullable=False)  # 使用实际表中的字段类型
    user_id = Column(String(64), nullable=True, index=True)
    nickname = Column(String(64), nullable=True)
    avatar = Column(String(255), nullable=True)  # 使用实际表中的字段类型和长度
    gender = Column(String(12), nullable=True)
    profile_url = Column(String(255), nullable=True)  # 新增实际表中的字段
    ip_location = Column(String(32), default='发布微博的地理信息')
    liked_count = Column(String(16), nullable=True)  # 使用实际表中的字段名
    comments_count = Column(String(16), nullable=True)  # 使用实际表中的字段类型
    shared_count = Column(String(16), nullable=True)  # 使用实际表中的字段名
    note_url = Column(String(512), nullable=True)
    source_keyword = Column(String(255))
    analysis_info = Column(JSON)

class TiebaNote(Base, BaseModel):
    """贴吧内容模型"""
    __tablename__ = 'tieba_note'
    
    note_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    desc = Column(Text)
    note_url = Column(String(255), nullable=False)
    publish_time = Column(String(255), nullable=False)  # 实际表中是varchar类型
    user_link = Column(String(255), nullable=False)
    user_nickname = Column(String(64), nullable=False)
    user_avatar = Column(Text)
    tieba_name = Column(String(64), nullable=False)
    tieba_link = Column(String(255), nullable=False)
    total_replay_num = Column(Integer, default=0)  # 使用实际表中的字段名
    source_keyword = Column(String(255))
    analysis_info = Column(JSON)

class ZhihuContent(Base, BaseModel):
    """知乎内容模型"""
    __tablename__ = 'zhihu_content'
    
    content_id = Column(String(64), nullable=False, index=True)
    content_type = Column(String(16), nullable=False)
    content_url = Column(String(512), nullable=False)
    title = Column(String(500), nullable=False)
    desc = Column(Text)
    created_time = Column(String(32), nullable=False)  # 使用实际表中的字段名和类型
    user_id = Column(String(64), nullable=False, index=True)
    user_link = Column(String(255), nullable=False)  # 使用实际表中的字段名
    user_nickname = Column(String(64), nullable=False)  # 使用实际表中的字段名
    user_avatar = Column(Text)
    comment_count = Column(Integer, nullable=False, default=0)  # 使用实际表中的类型
    voteup_count = Column(Integer, nullable=False, default=0)  # 使用实际表中的字段名
    source_keyword = Column(String(255))
    analysis_info = Column(JSON)

class NewsArticle(Base, BaseModel):
    """新闻文章模型"""
    __tablename__ = 'news_article'
    
    article_id = Column(String(128), nullable=False, index=True)
    source_url = Column(String(1000), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    summary = Column(Text)
    keywords = Column(JSON)
    authors = Column(JSON)
    publish_date = Column(DateTime)
    source_domain = Column(String(255))
    source_site = Column(String(255))
    top_image = Column(String(1000))
    word_count = Column(Integer)
    language = Column(String(32), default='zh')
    article_metadata = Column('metadata', JSON)  # 使用column别名映射到metadata字段
    source_keyword = Column(String(255))  # 添加source_keyword字段
    analysis_info = Column(JSON)

# 平台模型映射
PLATFORM_MODELS = {
    'xhs': XhsNote,
    'douyin': DouyinAweme,
    'kuaishou': KuaishousVideo,
    'bilibili': BilibiliVideo,
    'weibo': WeiboNote,
    'tieba': TiebaNote,
    'zhihu': ZhihuContent,
    'news': NewsArticle
}

# 平台中文名称映射
PLATFORM_NAMES = {
    'xhs': '小红书',
    'douyin': '抖音',
    'kuaishou': '快手',
    'bilibili': '哔哩哔哩',
    'weibo': '微博',
    'tieba': '贴吧',
    'zhihu': '知乎',
    'news': '新闻'
}

def get_model_by_platform(platform: str):
    """根据平台名称获取对应的模型类"""
    return PLATFORM_MODELS.get(platform)

def get_platform_name(platform: str) -> str:
    """获取平台中文名称"""
    return PLATFORM_NAMES.get(platform, platform)