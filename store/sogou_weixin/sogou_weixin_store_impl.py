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
import csv
import json
import os
import time
from typing import Dict, List, Optional

import aiofiles

import config
from base.base_crawler import AbstractStore
from model.m_weixin import WeixinArticle
from store.sogou_weixin.sogou_weixin_store_sql import SogouWeixinStoreSql
from tools import utils
from var import media_crawler_db_var


class SogouWeixinDbStoreImplement(AbstractStore):
    """搜狗微信数据库存储实现"""
    
    def __init__(self):
        self.mysql_db_var = media_crawler_db_var
        self.table_name = "weixin_article"
    
    async def update_weixin_article(self, article_data: Dict) -> None:
        """
        更新微信文章
        
        Args:
            article_data: 文章数据字典
        """
        try:
            current_ts = int(time.time() * 1000)
            
            # 确保必要字段存在
            article_data['add_ts'] = current_ts
            article_data['last_modify_ts'] = current_ts
            
            # 处理可能为空的字段
            for field in ['content', 'summary', 'account_id', 'cover_image', 
                         'publish_time', 'read_count', 'like_count']:
                if field not in article_data or article_data[field] is None:
                    article_data[field] = ""
            
            # 处理数值字段
            if 'publish_timestamp' not in article_data or article_data['publish_timestamp'] is None or article_data['publish_timestamp'] == '':
                article_data['publish_timestamp'] = 0
            
            # 处理analysis_info字段
            if 'analysis_info' not in article_data or article_data['analysis_info'] is None:
                article_data['analysis_info'] = None
            
            # 使用item_to_table方法，更简单安全
            await self.mysql_db_var.get().item_to_table("weixin_article", article_data)
            
            utils.logger.debug(f"[SogouWeixinDbStoreImplement] 文章已存储: {article_data.get('title', 'Unknown')}")
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinDbStoreImplement] 存储文章失败: {e}")
            raise
    
    async def batch_update_weixin_articles(self, articles_data: List[Dict]) -> None:
        """
        批量更新微信文章
        
        Args:
            articles_data: 文章数据列表
        """
        if not articles_data:
            return
            
        try:
            current_ts = int(time.time() * 1000)
            
            # 批量处理数据
            processed_data = []
            for article_data in articles_data:
                # 确保必要字段存在
                article_data['add_ts'] = current_ts
                article_data['last_modify_ts'] = current_ts
                
                # 处理可能为空的字段
                for field in ['content', 'summary', 'account_id', 'cover_image',
                             'publish_timestamp', 'read_count', 'like_count']:
                    if field not in article_data or article_data[field] is None:
                        article_data[field] = ""
                
                processed_data.append(article_data)
            
            # 批量执行SQL
            await self.mysql_db_var.get().executemany(
                SogouWeixinStoreSql.BATCH_INSERT_WEIXIN_ARTICLES,
                processed_data
            )
            
            utils.logger.info(f"[SogouWeixinDbStoreImplement] 批量存储 {len(processed_data)} 篇文章完成")
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinDbStoreImplement] 批量存储文章失败: {e}")
            raise
    
    async def query_weixin_articles(self, 
                                   begin_time: int,
                                   end_time: int,
                                   size: int = 10,
                                   offset: int = 0) -> List[WeixinArticle]:
        """
        查询微信文章
        
        Args:
            begin_time: 开始时间戳
            end_time: 结束时间戳
            size: 查询数量
            offset: 偏移量
            
        Returns:
            文章列表
        """
        try:
            result = await self.mysql_db_var.get().fetchall(
                SogouWeixinStoreSql.QUERY_WEIXIN_ARTICLE,
                {
                    'begin_time': begin_time,
                    'end_time': end_time,
                    'size': size,
                    'offset': offset
                }
            )
            
            articles = []
            for row in result:
                try:
                    article = WeixinArticle(**row)
                    articles.append(article)
                except Exception as e:
                    utils.logger.warning(f"[SogouWeixinDbStoreImplement] 创建WeixinArticle对象失败: {e}")
                    continue
            
            return articles
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinDbStoreImplement] 查询文章失败: {e}")
            return []
    
    async def get_article_by_id(self, article_id: str) -> Optional[WeixinArticle]:
        """根据文章ID获取文章"""
        try:
            result = await self.mysql_db_var.get().fetchone(
                SogouWeixinStoreSql.QUERY_WEIXIN_ARTICLE_BY_ID,
                {'article_id': article_id}
            )
            
            if result:
                return WeixinArticle(**result)
            return None
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinDbStoreImplement] 根据ID查询文章失败: {e}")
            return None
    
    # ==================== 抽象方法实现 ====================
    
    async def store_content(self, content_item: Dict):
        """存储内容项（重定向到微信文章存储）"""
        await self.update_weixin_article(content_item)
    
    async def store_comment(self, comment_item: Dict):
        """存储评论项（搜狗微信不支持评论）"""
        pass
    
    async def store_creator(self, creator: Dict):
        """存储创作者信息（暂不支持）"""
        pass


class SogouWeixinCsvStoreImplement(AbstractStore):
    """搜狗微信CSV存储实现"""
    
    def __init__(self):
        self.csv_dir = "data/csv"
        self.csv_file = "weixin_articles.csv"
        self._ensure_csv_dir()
    
    def _ensure_csv_dir(self):
        """确保CSV目录存在"""
        os.makedirs(self.csv_dir, exist_ok=True)
    
    async def update_weixin_article(self, article_data: Dict) -> None:
        """更新微信文章到CSV"""
        try:
            csv_path = os.path.join(self.csv_dir, self.csv_file)
            
            # 定义CSV字段
            fieldnames = [
                'article_id', 'title', 'content', 'summary', 'account_name', 
                'account_id', 'cover_image', 'original_url', 'publish_time',
                'publish_timestamp', 'read_count', 'like_count', 'source_keyword',
                'add_ts', 'last_modify_ts'
            ]
            
            # 检查文件是否存在，如果不存在则创建并写入头部
            file_exists = os.path.exists(csv_path)
            
            async with aiofiles.open(csv_path, mode='a', encoding='utf-8', newline='') as f:
                if not file_exists:
                    # 写入CSV头部
                    header = ','.join(fieldnames) + '\n'
                    await f.write(header)
                
                # 准备数据行
                row_data = []
                current_ts = int(time.time() * 1000)
                article_data['add_ts'] = current_ts
                article_data['last_modify_ts'] = current_ts
                
                for field in fieldnames:
                    value = article_data.get(field, "")
                    # 处理CSV中的特殊字符
                    if isinstance(value, str):
                        value = value.replace('"', '""').replace('\n', ' ').replace('\r', ' ')
                        if ',' in value or '"' in value:
                            value = f'"{value}"'
                    row_data.append(str(value))
                
                # 写入数据行
                row = ','.join(row_data) + '\n'
                await f.write(row)
            
            utils.logger.debug(f"[SogouWeixinCsvStoreImplement] 文章已保存到CSV: {article_data.get('title', 'Unknown')}")
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinCsvStoreImplement] 保存文章到CSV失败: {e}")
            raise
    
    # ==================== 抽象方法实现 ====================
    
    async def store_content(self, content_item: Dict):
        """存储内容项（重定向到微信文章存储）"""
        await self.update_weixin_article(content_item)
    
    async def store_comment(self, comment_item: Dict):
        """存储评论项（搜狗微信不支持评论）"""
        pass
    
    async def store_creator(self, creator: Dict):
        """存储创作者信息（暂不支持）"""
        pass


class SogouWeixinJsonStoreImplement(AbstractStore):
    """搜狗微信JSON存储实现"""
    
    def __init__(self):
        self.json_dir = "data/json"
        self.json_file = "weixin_articles.json"
        self._ensure_json_dir()
    
    def _ensure_json_dir(self):
        """确保JSON目录存在"""
        os.makedirs(self.json_dir, exist_ok=True)
    
    async def update_weixin_article(self, article_data: Dict) -> None:
        """更新微信文章到JSON"""
        try:
            json_path = os.path.join(self.json_dir, self.json_file)
            
            # 添加时间戳
            current_ts = int(time.time() * 1000)
            article_data['add_ts'] = current_ts
            article_data['last_modify_ts'] = current_ts
            
            # 读取现有数据
            articles = []
            if os.path.exists(json_path):
                async with aiofiles.open(json_path, mode='r', encoding='utf-8') as f:
                    content = await f.read()
                    if content.strip():
                        articles = json.loads(content)
            
            # 检查文章是否已存在
            article_id = article_data.get('article_id')
            existing_index = -1
            for i, existing_article in enumerate(articles):
                if existing_article.get('article_id') == article_id:
                    existing_index = i
                    break
            
            # 更新或添加文章
            if existing_index >= 0:
                articles[existing_index] = article_data
            else:
                articles.append(article_data)
            
            # 写入文件
            async with aiofiles.open(json_path, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(articles, ensure_ascii=False, indent=2))
            
            utils.logger.debug(f"[SogouWeixinJsonStoreImplement] 文章已保存到JSON: {article_data.get('title', 'Unknown')}")
            
        except Exception as e:
            utils.logger.error(f"[SogouWeixinJsonStoreImplement] 保存文章到JSON失败: {e}")
            raise
    
    # ==================== 抽象方法实现 ====================
    
    async def store_content(self, content_item: Dict):
        """存储内容项（重定向到微信文章存储）"""
        await self.update_weixin_article(content_item)
    
    async def store_comment(self, comment_item: Dict):
        """存储评论项（搜狗微信不支持评论）"""
        pass
    
    async def store_creator(self, creator: Dict):
        """存储创作者信息（暂不支持）"""
        pass