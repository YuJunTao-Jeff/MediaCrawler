# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-

from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


class NewsSearchResult(BaseModel):
    """新闻搜索结果"""
    search_keyword: str = Field(..., description="搜索关键词")
    search_engine: str = Field(..., description="搜索引擎")
    result_title: str = Field(..., description="搜索结果标题")
    result_url: str = Field(..., description="搜索结果URL")
    result_score: Optional[float] = Field(None, description="搜索结果评分")
    result_description: Optional[str] = Field(None, description="搜索结果描述")
    article_id: Optional[str] = Field(None, description="关联的文章ID")


class NewsArticle(BaseModel):
    """新闻文章"""
    article_id: str = Field(..., description="文章唯一ID")
    source_url: str = Field(..., description="原始URL")
    title: str = Field(..., description="文章标题")
    content: Optional[str] = Field(None, description="文章正文内容")
    summary: Optional[str] = Field(None, description="文章摘要")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")
    authors: Optional[List[str]] = Field(None, description="作者列表")
    publish_date: Optional[datetime] = Field(None, description="发布时间")
    source_domain: Optional[str] = Field(None, description="来源域名")
    source_site: Optional[str] = Field(None, description="来源网站名称")
    top_image: Optional[str] = Field(None, description="文章主图URL")
    word_count: Optional[int] = Field(None, description="字数统计")
    language: str = Field(default="zh", description="语言")
    metadata: Optional[dict] = Field(None, description="其他元数据")


class NewsSearchTask(BaseModel):
    """新闻搜索任务"""
    task_id: str = Field(..., description="任务唯一ID")
    keywords: List[str] = Field(..., description="搜索关键词列表")
    search_engines: List[str] = Field(..., description="搜索引擎列表")
    status: str = Field(default="pending", description="任务状态")
    total_results: int = Field(default=0, description="总搜索结果数")
    extracted_articles: int = Field(default=0, description="成功提取文章数")
    failed_extractions: int = Field(default=0, description="提取失败数")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    error_info: Optional[str] = Field(None, description="错误信息")