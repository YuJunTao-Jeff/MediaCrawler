"""
数据库连接管理
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from typing import Optional
import sys
import os

# 直接配置数据库参数，避免复杂的导入问题
RELATION_DB_HOST = os.getenv("RELATION_DB_HOST", "localhost")
RELATION_DB_PORT = int(os.getenv("RELATION_DB_PORT", 3306))
RELATION_DB_USER = os.getenv("RELATION_DB_USER", "root")
RELATION_DB_PWD = os.getenv("RELATION_DB_PWD", "")
RELATION_DB_NAME = os.getenv("RELATION_DB_NAME", "media_crawler")

logger = logging.getLogger(__name__)

# 创建基类
Base = declarative_base()

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.engine: Optional[object] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库连接"""
        try:
            # 构建数据库URL
            database_url = f"mysql+pymysql://{RELATION_DB_USER}:{RELATION_DB_PWD}@{RELATION_DB_HOST}:{RELATION_DB_PORT}/{RELATION_DB_NAME}?charset=utf8mb4"
            
            # 创建数据库引擎
            self.engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600,
                echo=False,  # 生产环境关闭SQL日志
                isolation_level="READ_COMMITTED"
            )
            
            # 创建会话工厂
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("数据库连接初始化成功")
            
        except Exception as e:
            logger.error(f"数据库连接初始化失败: {e}")
            raise
    
    def get_session(self):
        """获取数据库会话"""
        if not self.SessionLocal:
            raise RuntimeError("数据库未初始化")
        
        session = self.SessionLocal()
        try:
            return session
        except Exception as e:
            session.close()
            logger.error(f"获取数据库会话失败: {e}")
            raise
    
    def close_session(self, session):
        """关闭数据库会话"""
        try:
            if session:
                session.close()
        except Exception as e:
            logger.error(f"关闭数据库会话失败: {e}")
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            session = self.get_session()
            session.execute(text("SELECT 1"))
            self.close_session(session)
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def get_engine(self):
        """获取数据库引擎"""
        return self.engine

# 全局数据库管理器实例
db_manager = DatabaseManager()

def get_db_session():
    """获取数据库会话的便捷函数"""
    return db_manager.get_session()

def close_db_session(session):
    """关闭数据库会话的便捷函数"""
    db_manager.close_session(session)