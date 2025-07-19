"""
AI分析任务数据模型
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json


@dataclass
class ContentItem:
    """内容项数据模型"""
    platform: str
    content_id: str
    title: str = ""
    content: str = ""
    comments: List[Dict[str, Any]] = None
    create_time: int = 0
    content_length: int = 0
    source_keyword: str = ""  # 源关键词
    
    def __post_init__(self):
        if self.comments is None:
            self.comments = []
    
    def get_full_content(self) -> str:
        """获取完整内容（标题+正文）"""
        parts = []
        if self.title:
            parts.append(f"标题: {self.title}")
        if self.content:
            parts.append(f"内容: {self.content}")
        return "\n".join(parts)
    
    def get_content_with_comments(self) -> str:
        """获取带评论的完整内容"""
        content_parts = [self.get_full_content()]
        
        if self.comments:
            content_parts.append("评论:")
            for i, comment in enumerate(self.comments):  # 包含所有评论
                comment_text = comment.get('content', '')
                if comment_text:
                    content_parts.append(f"{i+1}. {comment_text}")
        
        return "\n".join(content_parts)
    
    def get_content_length(self) -> int:
        """获取内容总长度"""
        return len(self.get_content_with_comments())


@dataclass
class AnalysisResult:
    """分析结果数据模型"""
    content_id: str
    sentiment: str
    sentiment_score: float  # -1 to 1 (负面到正面)
    summary: str
    keywords: List[str]
    category: str
    relevance_score: float  # 0-1 (与source_keyword的相关性)
    key_comment_ids: List[str]
    analysis_timestamp: int
    model_version: str
    content_length: int
    comment_count: int
    source_keyword: str = ""  # 源关键词
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(asdict(self), ensure_ascii=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisResult':
        """从字典创建分析结果"""
        return cls(**data)
    
    def validate(self) -> bool:
        """验证分析结果的有效性"""
        if not self.content_id:
            return False
        if self.sentiment not in ['positive', 'negative', 'neutral']:
            return False
        if not 0 <= self.sentiment_score <= 1:
            return False
        if not 0 <= self.relevance_score <= 1:
            return False
        return True


@dataclass
class BatchAnalysisRequest:
    """批量分析请求模型"""
    platform: str
    content_items: List[ContentItem]
    batch_size: int = 5
    
    def get_total_length(self) -> int:
        """获取批次总长度"""
        return sum(item.get_content_length() for item in self.content_items)
    
    def split_to_batches(self, target_length: int = 6000) -> List['BatchAnalysisRequest']:
        """优先按数量拆分批次，同时考虑长度限制"""
        batches = []
        current_batch = []
        current_length = 0
        
        for item in self.content_items:
            item_length = item.get_content_length()
            
            # 如果单个内容就超过目标长度，单独成批
            if item_length > target_length:
                if current_batch:
                    batches.append(BatchAnalysisRequest(
                        platform=self.platform,
                        content_items=current_batch,
                        batch_size=len(current_batch)
                    ))
                    current_batch = []
                    current_length = 0
                
                batches.append(BatchAnalysisRequest(
                    platform=self.platform,
                    content_items=[item],
                    batch_size=1
                ))
                continue
            
            # 优先按数量拆分：如果当前批次已达到batch_size，提交批次
            if len(current_batch) >= self.batch_size:
                batches.append(BatchAnalysisRequest(
                    platform=self.platform,
                    content_items=current_batch,
                    batch_size=len(current_batch)
                ))
                current_batch = []
                current_length = 0
            
            # 如果添加当前项会超过目标长度，也要提交当前批次
            elif current_length + item_length > target_length and current_batch:
                batches.append(BatchAnalysisRequest(
                    platform=self.platform,
                    content_items=current_batch,
                    batch_size=len(current_batch)
                ))
                current_batch = []
                current_length = 0
            
            current_batch.append(item)
            current_length += item_length
        
        # 处理最后一个批次
        if current_batch:
            batches.append(BatchAnalysisRequest(
                platform=self.platform,
                content_items=current_batch,
                batch_size=len(current_batch)
            ))
        
        return batches


@dataclass
class ProcessingStats:
    """处理统计信息"""
    total_items: int = 0
    processed_items: int = 0
    success_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
    
    def add_success(self):
        """添加成功统计"""
        self.processed_items += 1
        self.success_items += 1
    
    def add_failure(self):
        """添加失败统计"""
        self.processed_items += 1
        self.failed_items += 1
    
    def add_skip(self):
        """添加跳过统计"""
        self.processed_items += 1
        self.skipped_items += 1
    
    def finish(self):
        """完成处理"""
        self.end_time = datetime.now()
    
    def get_duration(self) -> float:
        """获取处理时长（秒）"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.processed_items == 0:
            return 0.0
        return self.success_items / self.processed_items
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "success_items": self.success_items,
            "failed_items": self.failed_items,
            "skipped_items": self.skipped_items,
            "duration": self.get_duration(),
            "success_rate": self.get_success_rate(),
        }