"""
AI分析任务配置模块
"""

import os
from typing import Dict, Any

# OpenAI API配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-453FUd7Q4ArDvC2fD90e966fBc794f56Aa0cDaA7Eb85B1Bb")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://oneapi.dev.appendata.com/v1")
OPENAI_MODEL = "gpt-4o-mini"

# 分析配置
ANALYSIS_CONFIG = {
    "model": OPENAI_MODEL,
    "temperature": 0.1,
    "max_tokens": 4000,
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 1.0,
}

# 批量处理配置
BATCH_CONFIG = {
    "default_batch_size": 5,
    "max_batch_size": 10,
    "min_batch_size": 1,
    "max_content_length": 8000,  # 单次请求最大字符数
    "target_content_length": 6000,  # 目标字符数
}

# 数据库配置
DATABASE_CONFIG = {
    "host": os.getenv("RELATION_DB_HOST", "localhost"),
    "port": int(os.getenv("RELATION_DB_PORT", 3306)),
    "user": os.getenv("RELATION_DB_USER", "root"),
    "password": os.getenv("RELATION_DB_PWD", ""),
    "database": os.getenv("RELATION_DB_NAME", "media_crawler"),
    "charset": "utf8mb4",
    "autocommit": True,
}

# 支持的平台表映射
PLATFORM_TABLES = {
    "xhs": {
        "main_table": "xhs_note",
        "comment_table": "xhs_note_comment",
        "main_id_field": "note_id",
        "comment_id_field": "comment_id",
        "content_fields": ["title", "desc"],
        "comment_content_field": "content",
        "parent_id_field": "note_id",
    },
    "dy": {
        "main_table": "douyin_aweme",
        "comment_table": "douyin_aweme_comment",
        "main_id_field": "aweme_id",
        "comment_id_field": "comment_id",
        "content_fields": ["title", "desc"],
        "comment_content_field": "content",
        "parent_id_field": "aweme_id",
    },
    "bili": {
        "main_table": "bilibili_video",
        "comment_table": "bilibili_video_comment",
        "main_id_field": "video_id",
        "comment_id_field": "comment_id",
        "content_fields": ["title", "desc"],
        "comment_content_field": "content",
        "parent_id_field": "video_id",
    },
    "wb": {
        "main_table": "weibo_note",
        "comment_table": "weibo_note_comment",
        "main_id_field": "note_id",
        "comment_id_field": "comment_id",
        "content_fields": ["content"],
        "comment_content_field": "content",
        "parent_id_field": "note_id",
    },
    "ks": {
        "main_table": "kuaishou_video",
        "comment_table": "kuaishou_video_comment",
        "main_id_field": "video_id",
        "comment_id_field": "comment_id",
        "content_fields": ["title", "desc"],
        "comment_content_field": "content",
        "parent_id_field": "video_id",
    },
    "tieba": {
        "main_table": "tieba_note",
        "comment_table": "tieba_comment",
        "main_id_field": "note_id",
        "comment_id_field": "comment_id",
        "content_fields": ["title", "desc"],
        "comment_content_field": "content",
        "parent_id_field": "note_id",
    },
    "zhihu": {
        "main_table": "zhihu_content",
        "comment_table": "zhihu_comment",
        "main_id_field": "content_id",
        "comment_id_field": "comment_id",
        "content_fields": ["title", "desc"],
        "comment_content_field": "content",
        "parent_id_field": "content_id",
    },
    "sogou_weixin": {
        "main_table": "weixin_article",
        "comment_table": None,  # 微信文章平台无评论系统
        "main_id_field": "article_id",
        "comment_id_field": None,
        "content_fields": ["title", "summary", "content"],
        "comment_content_field": None,
        "parent_id_field": None,
    },
}

# 日志配置
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "filename": "analysis_job.log",
}