"""
工具函数模块
"""
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def safe_json_loads(text: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """安全的JSON解析"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default or {}


def safe_json_dumps(obj: Any, default: Optional[str] = None) -> str:
    """安全的JSON序列化"""
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return default or "{}"


def calculate_content_length(content: str, comments: list) -> int:
    """计算内容总长度"""
    total_length = len(content or "")
    for comment in comments:
        if isinstance(comment, dict):
            total_length += len(comment.get('content', ''))
        else:
            total_length += len(str(comment))
    return total_length


def format_timestamp(timestamp: Optional[int] = None) -> str:
    """格式化时间戳"""
    if timestamp is None:
        timestamp = int(time.time() * 1000)
    
    dt = datetime.fromtimestamp(timestamp / 1000)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def truncate_text(text: str, max_length: int = 100) -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def validate_analysis_result(result: Dict[str, Any]) -> bool:
    """验证分析结果格式"""
    required_fields = [
        'content_id', 'sentiment', 'sentiment_score', 
        'summary', 'keywords', 'category', 'relevance_score'
    ]
    
    for field in required_fields:
        if field not in result:
            return False
    
    # 检查sentiment值
    if result['sentiment'] not in ['positive', 'negative', 'neutral']:
        return False
    
    # 检查评分范围
    if not (0 <= result['sentiment_score'] <= 1):
        return False
    
    if not (0 <= result['relevance_score'] <= 1):
        return False
    
    # 检查关键词格式
    if not isinstance(result['keywords'], list):
        return False
    
    return True


def create_default_analysis_result(content_id: str, error_msg: str = "") -> Dict[str, Any]:
    """创建默认分析结果"""
    return {
        "content_id": content_id,
        "sentiment": "neutral",
        "sentiment_score": 0.5,
        "summary": f"分析失败: {error_msg}" if error_msg else "内容分析失败",
        "keywords": [],
        "category": "未分类",
        "relevance_score": 0.0,
        "key_comment_ids": [],
        "analysis_timestamp": int(time.time() * 1000),
        "model_version": "gpt-4o-mini",
        "content_length": 0,
        "comment_count": 0,
        "error": error_msg
    }


def batch_split_by_length(items: list, max_length: int = 8000) -> list:
    """根据内容长度分批"""
    batches = []
    current_batch = []
    current_length = 0
    
    for item in items:
        item_length = getattr(item, 'content_length', 0)
        
        if current_length + item_length > max_length and current_batch:
            batches.append(current_batch)
            current_batch = [item]
            current_length = item_length
        else:
            current_batch.append(item)
            current_length += item_length
    
    if current_batch:
        batches.append(current_batch)
    
    return batches


def format_processing_stats(stats: Dict[str, Any]) -> str:
    """格式化处理统计信息"""
    return f"""
处理统计:
- 总数: {stats.get('total', 0)}
- 成功: {stats.get('success', 0)}
- 失败: {stats.get('failed', 0)}
- 成功率: {stats.get('success_rate', 0):.1%}
- 耗时: {stats.get('duration', 0):.2f}秒
"""