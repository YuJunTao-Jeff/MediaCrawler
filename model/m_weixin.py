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
from typing import Optional
from pydantic import BaseModel, Field


class WeixinArticle(BaseModel):
    """
    微信公众号文章
    """
    article_id: str = Field(..., description="文章唯一ID(URL MD5)")
    title: str = Field(..., description="文章标题")
    content: str = Field(default="", description="文章正文内容")
    summary: str = Field(default="", description="文章摘要/描述")
    account_name: str = Field(..., description="公众号名称")
    account_id: str = Field(default="", description="公众号微信号")
    cover_image: str = Field(default="", description="封面图片URL")
    original_url: str = Field(..., description="原文链接")
    publish_time: str = Field(default="", description="发布时间")
    publish_timestamp: Optional[int] = Field(default=None, description="发布时间戳")
    read_count: str = Field(default="", description="阅读数")
    like_count: str = Field(default="", description="点赞数")
    source_keyword: str = Field(default="", description="搜索关键词")