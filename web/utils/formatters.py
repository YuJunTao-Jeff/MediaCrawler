"""
数据格式化工具
"""

from datetime import datetime
from typing import Union

def format_number(num: Union[int, str]) -> str:
    """格式化数字显示"""
    try:
        if isinstance(num, str):
            num = int(num)
        
        if num >= 100000000:  # 1亿
            return f"{num/100000000:.1f}亿"
        elif num >= 10000:  # 1万
            return f"{num/10000:.1f}万"
        elif num >= 1000:  # 1千
            return f"{num/1000:.1f}k"
        else:
            return str(num)
    except (ValueError, TypeError):
        return "0"

def format_time(timestamp: Union[int, float, datetime], format_str: str = "%Y-%m-%d %H:%M") -> str:
    """格式化时间显示"""
    try:
        if isinstance(timestamp, (int, float)):
            # 假设时间戳是毫秒级
            if timestamp > 1e12:
                dt = datetime.fromtimestamp(timestamp / 1000)
            else:
                dt = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            return "未知时间"
        
        return dt.strftime(format_str)
    except:
        return "未知时间"

def format_time_ago(publish_time: datetime) -> str:
    """格式化时间为相对时间"""
    try:
        now = datetime.now()
        diff = now - publish_time
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years}年前"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months}个月前"
        elif diff.days > 0:
            return f"{diff.days}天前"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}小时前"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}分钟前"
        else:
            return "刚刚"
    except:
        return "未知时间"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def format_percentage(value: float, decimal_places: int = 1) -> str:
    """格式化百分比"""
    try:
        return f"{value:.{decimal_places}f}%"
    except:
        return "0%"

def format_sentiment_text(sentiment: str) -> str:
    """格式化情感文本"""
    sentiment_map = {
        'positive': '正面',
        'negative': '负面',
        'neutral': '中性',
        'unknown': '未知'
    }
    return sentiment_map.get(sentiment.lower(), '未知')

def format_platform_name(platform: str) -> str:
    """格式化平台名称"""
    from web.database.models import PLATFORM_NAMES
    return PLATFORM_NAMES.get(platform, platform)

def safe_int(value: Union[str, int, None], default: int = 0) -> int:
    """安全转换为整数"""
    try:
        if value is None:
            return default
        if isinstance(value, str):
            # 移除可能的非数字字符
            cleaned = ''.join(filter(str.isdigit, value))
            return int(cleaned) if cleaned else default
        return int(value)
    except:
        return default

def safe_float(value: Union[str, float, None], default: float = 0.0) -> float:
    """安全转换为浮点数"""
    try:
        if value is None:
            return default
        return float(value)
    except:
        return default