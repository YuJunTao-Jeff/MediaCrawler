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
from typing import List, Dict
import config
from model.m_weixin import WeixinArticle
from var import source_keyword_var
from base.base_crawler import AbstractStore
from . import sogou_weixin_store_impl
from .sogou_weixin_store_impl import *


class SogouWeixinStoreFactory:
    STORES = {
        "csv": SogouWeixinCsvStoreImplement, 
        "db": SogouWeixinDbStoreImplement,
        "json": SogouWeixinJsonStoreImplement
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = SogouWeixinStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[SogouWeixinStoreFactory.create_store] Invalid save option only supported csv or db or json ...")
        return store_class()


async def update_weixin_article(article_data: Dict) -> None:
    """更新微信文章数据"""
    from tools import utils
    utils.logger.info(f"[store.sogou_weixin.update_weixin_article] 更新文章: {article_data.get('title', 'Unknown')}")
    
    store = SogouWeixinStoreFactory.create_store()
    await store.update_weixin_article(article_data)


async def batch_update_weixin_articles(articles_data: List[Dict]) -> None:
    """批量更新微信文章数据"""
    from tools import utils
    utils.logger.info(f"[store.sogou_weixin.batch_update_weixin_articles] 批量更新 {len(articles_data)} 篇文章")
    
    store = SogouWeixinStoreFactory.create_store()
    if hasattr(store, 'batch_update_weixin_articles'):
        await store.batch_update_weixin_articles(articles_data)
    else:
        # 如果存储层不支持批量操作，则逐个更新
        for article_data in articles_data:
            await store.update_weixin_article(article_data)