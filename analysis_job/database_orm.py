"""
基于SQLAlchemy ORM的数据库操作模块
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, BigInteger, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.mysql import LONGTEXT, JSON

from .config import DATABASE_CONFIG, PLATFORM_TABLES
from .models import ContentItem, AnalysisResult

logger = logging.getLogger(__name__)

Base = declarative_base()

class XhsNote(Base):
    __tablename__ = 'xhs_note'
    
    id = Column(Integer, primary_key=True)
    note_id = Column(String(64), nullable=False)
    title = Column(String(500))
    desc = Column(LONGTEXT)
    add_ts = Column(BigInteger)
    analysis_info = Column(JSON)

class XhsNoteComment(Base):
    __tablename__ = 'xhs_note_comment'
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(64), nullable=False)
    note_id = Column(String(64), nullable=False)
    content = Column(LONGTEXT)
    add_ts = Column(BigInteger)

class DouyinAweme(Base):
    __tablename__ = 'douyin_aweme'
    
    id = Column(Integer, primary_key=True)
    aweme_id = Column(String(64), nullable=False)
    title = Column(String(500))
    desc = Column(LONGTEXT)
    add_ts = Column(BigInteger)
    analysis_info = Column(JSON)

class DouyinAwemeComment(Base):
    __tablename__ = 'douyin_aweme_comment'
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(64), nullable=False)
    aweme_id = Column(String(64), nullable=False)
    content = Column(LONGTEXT)
    add_ts = Column(BigInteger)

class BilibiliVideo(Base):
    __tablename__ = 'bilibili_video'
    
    id = Column(Integer, primary_key=True)
    video_id = Column(String(64), nullable=False)
    title = Column(String(500))
    desc = Column(LONGTEXT)
    add_ts = Column(BigInteger)
    analysis_info = Column(JSON)

class BilibiliVideoComment(Base):
    __tablename__ = 'bilibili_video_comment'
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(64), nullable=False)
    video_id = Column(String(64), nullable=False)
    content = Column(LONGTEXT)
    add_ts = Column(BigInteger)

class WeiboNote(Base):
    __tablename__ = 'weibo_note'
    
    id = Column(Integer, primary_key=True)
    note_id = Column(String(64), nullable=False)
    content = Column(LONGTEXT)
    add_ts = Column(BigInteger)
    analysis_info = Column(JSON)

class WeiboNoteComment(Base):
    __tablename__ = 'weibo_note_comment'
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(64), nullable=False)
    note_id = Column(String(64), nullable=False)
    content = Column(LONGTEXT)
    add_ts = Column(BigInteger)

class KuaishouVideo(Base):
    __tablename__ = 'kuaishou_video'
    
    id = Column(Integer, primary_key=True)
    video_id = Column(String(64), nullable=False)
    title = Column(String(500))
    desc = Column(LONGTEXT)
    add_ts = Column(BigInteger)
    analysis_info = Column(JSON)

class KuaishouVideoComment(Base):
    __tablename__ = 'kuaishou_video_comment'
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(64), nullable=False)
    video_id = Column(String(64), nullable=False)
    content = Column(LONGTEXT)
    add_ts = Column(BigInteger)

class TiebaNote(Base):
    __tablename__ = 'tieba_note'
    
    id = Column(Integer, primary_key=True)
    note_id = Column(String(64), nullable=False)
    title = Column(String(500))
    desc = Column(LONGTEXT)
    add_ts = Column(BigInteger)
    analysis_info = Column(JSON)

class TiebaComment(Base):
    __tablename__ = 'tieba_comment'
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(64), nullable=False)
    note_id = Column(String(64), nullable=False)
    content = Column(LONGTEXT)
    add_ts = Column(BigInteger)

class ZhihuContent(Base):
    __tablename__ = 'zhihu_content'
    
    id = Column(Integer, primary_key=True)
    content_id = Column(String(64), nullable=False)
    title = Column(String(500))
    desc = Column(LONGTEXT)
    add_ts = Column(BigInteger)
    analysis_info = Column(JSON)

class ZhihuComment(Base):
    __tablename__ = 'zhihu_comment'
    
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(64), nullable=False)
    content_id = Column(String(64), nullable=False)
    content = Column(LONGTEXT)
    add_ts = Column(BigInteger)

# 平台模型映射
PLATFORM_MODELS = {
    'xhs': {'main': XhsNote, 'comment': XhsNoteComment, 'id_field': 'note_id'},
    'dy': {'main': DouyinAweme, 'comment': DouyinAwemeComment, 'id_field': 'aweme_id'},
    'bili': {'main': BilibiliVideo, 'comment': BilibiliVideoComment, 'id_field': 'video_id'},
    'wb': {'main': WeiboNote, 'comment': WeiboNoteComment, 'id_field': 'note_id'},
    'ks': {'main': KuaishouVideo, 'comment': KuaishouVideoComment, 'id_field': 'video_id'},
    'tieba': {'main': TiebaNote, 'comment': TiebaComment, 'id_field': 'note_id'},
    'zhihu': {'main': ZhihuContent, 'comment': ZhihuComment, 'id_field': 'content_id'},
}

class DatabaseManager:
    """基于SQLAlchemy的数据库管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or DATABASE_CONFIG
        self.engine = None
        self.session_factory = None
        self.connect()
    
    def connect(self):
        """建立数据库连接"""
        try:
            db_url = f"mysql+pymysql://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}?charset={self.config['charset']}"
            self.engine = create_engine(db_url, pool_recycle=3600)
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.session_factory()
    
    def get_unanalyzed_content(self, platform: str, limit: int = 10) -> List[ContentItem]:
        """获取未分析的内容"""
        if platform not in PLATFORM_MODELS:
            raise ValueError(f"不支持的平台: {platform}")
        
        model_info = PLATFORM_MODELS[platform]
        MainModel = model_info['main']
        
        session = self.get_session()
        try:
            # 查询未分析的内容
            query = session.query(MainModel).filter(
                (MainModel.analysis_info.is_(None))
            ).order_by(MainModel.add_ts.desc()).limit(limit)
            
            results = query.all()
            
            content_items = []
            for row in results:
                # 获取内容字段
                content_parts = []
                title = ""
                
                if hasattr(row, 'title') and row.title:
                    title = row.title
                    content_parts.append(row.title)
                
                if hasattr(row, 'desc') and row.desc:
                    content_parts.append(row.desc)
                elif hasattr(row, 'content') and row.content:
                    content_parts.append(row.content)
                
                content = " ".join(content_parts) if content_parts else ""
                content_id = getattr(row, model_info['id_field'])
                
                content_item = ContentItem(
                    content_id=content_id,
                    title=title,
                    content=content,
                    comments=[],
                    platform=platform,
                    content_length=len(content)
                )
                content_items.append(content_item)
            
            logger.info(f"获取到 {len(content_items)} 条未分析的 {platform} 内容")
            return content_items
            
        except Exception as e:
            logger.error(f"获取未分析内容失败: {e}")
            raise
        finally:
            session.close()
    
    def get_content_with_comments(self, platform: str, content_id: str) -> ContentItem:
        """获取带评论的内容"""
        if platform not in PLATFORM_MODELS:
            raise ValueError(f"不支持的平台: {platform}")
        
        model_info = PLATFORM_MODELS[platform]
        MainModel = model_info['main']
        CommentModel = model_info['comment']
        id_field = model_info['id_field']
        
        session = self.get_session()
        try:
            # 获取主内容
            main_content = session.query(MainModel).filter(
                getattr(MainModel, id_field) == content_id
            ).first()
            
            if not main_content:
                raise ValueError(f"未找到内容ID: {content_id}")
            
            # 获取内容字段
            content_parts = []
            title = ""
            
            if hasattr(main_content, 'title') and main_content.title:
                title = main_content.title
                content_parts.append(main_content.title)
            
            if hasattr(main_content, 'desc') and main_content.desc:
                content_parts.append(main_content.desc)
            elif hasattr(main_content, 'content') and main_content.content:
                content_parts.append(main_content.content)
            
            content = " ".join(content_parts) if content_parts else ""
            
            # 获取所有评论
            comments = session.query(CommentModel).filter(
                getattr(CommentModel, id_field) == content_id
            ).order_by(CommentModel.add_ts.desc()).all()
            
            comment_list = []
            for comment in comments:
                if comment.content:
                    comment_list.append({
                        'comment_id': comment.comment_id,
                        'content': comment.content
                    })
            
            content_item = ContentItem(
                content_id=content_id,
                title=title,
                content=content,
                comments=comment_list,
                platform=platform,
                content_length=len(content) + sum(len(c['content']) for c in comment_list)
            )
            
            return content_item
            
        except Exception as e:
            logger.error(f"获取内容和评论失败: {e}")
            logger.warning(f"获取内容 {content_id} 的评论失败: {e}")
            # 返回不含评论的内容
            return ContentItem(
                content_id=content_id,
                title="",
                content="",
                comments=[],
                platform=platform,
                content_length=0
            )
        finally:
            session.close()
    
    def batch_get_content_with_comments(self, platform: str, content_ids: List[str]) -> List[ContentItem]:
        """批量获取带评论的内容"""
        content_items = []
        for content_id in content_ids:
            try:
                content_item = self.get_content_with_comments(platform, content_id)
                content_items.append(content_item)
            except Exception as e:
                logger.warning(f"获取内容 {content_id} 失败: {e}")
                # 创建空的内容项
                content_item = ContentItem(
                    content_id=content_id,
                    title="",
                    content="",
                    comments=[],
                    platform=platform,
                    content_length=0
                )
                content_items.append(content_item)
        
        return content_items
    
    def batch_update_analysis_results(self, platform: str, results: List[AnalysisResult]) -> int:
        """批量更新分析结果"""
        if platform not in PLATFORM_MODELS:
            raise ValueError(f"不支持的平台: {platform}")
        
        model_info = PLATFORM_MODELS[platform]
        MainModel = model_info['main']
        id_field = model_info['id_field']
        
        session = self.get_session()
        try:
            updated_count = 0
            for result in results:
                # 更新单条记录
                session.query(MainModel).filter(
                    getattr(MainModel, id_field) == result.content_id
                ).update({
                    MainModel.analysis_info: result.to_dict()
                })
                updated_count += 1
            
            session.commit()
            logger.info(f"批量更新分析结果成功: {updated_count} 条记录")
            return updated_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"批量更新分析结果失败: {e}")
            raise
        finally:
            session.close()