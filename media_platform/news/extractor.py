# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import hashlib
import sys
import os
from datetime import datetime
from typing import Optional, Dict
from urllib.parse import urlparse

# 添加dataharvest到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'libs'))

from dataharvest.base import DataHarvest
from newspaper import Article
from tools import utils


class NewsArticleExtractor:
    """新闻文章内容提取器"""
    
    def __init__(self):
        self.harvester = DataHarvest()
    
    async def extract_article(self, url: str) -> Optional[Dict]:
        """
        提取文章完整信息
        
        Args:
            url: 文章URL
            
        Returns:
            包含文章信息的字典，提取失败返回None
        """
        try:
            utils.logger.info(f"[NewsArticleExtractor] 开始提取文章: {url}")
            
            # 1. 使用DataHarvest获取清洗后的内容
            doc = await self.harvester.a_crawl_and_purify(url)
            
            # 2. 使用newspaper3k提取结构化信息
            article = Article(url, language='zh')
            article.download()
            article.parse()
            article.nlp()
            
            # 3. 生成文章ID
            article_id = hashlib.md5(url.encode()).hexdigest()
            
            # 4. 解析URL获取域名信息
            parsed_url = urlparse(url)
            source_domain = parsed_url.netloc
            source_site = self._get_site_name(source_domain)
            
            # 5. 组装数据
            result = {
                'article_id': article_id,
                'source_url': url,
                'title': article.title or self._extract_title_from_content(doc.page_content),
                'content': doc.page_content,
                'summary': article.summary,
                'keywords': article.keywords,
                'authors': article.authors,
                'publish_date': article.publish_date,  # 直接使用newspaper3k结果
                'source_domain': source_domain,
                'source_site': source_site,
                'top_image': article.top_image,
                'word_count': len(doc.page_content) if doc.page_content else 0,
                'language': 'zh',
                'metadata': {
                    'extraction_method': 'dataharvest+newspaper3k',
                    'extraction_time': datetime.now().isoformat(),
                    **doc.metadata
                }
            }
            
            utils.logger.info(f"[NewsArticleExtractor] 成功提取文章: {url}")
            return result
            
        except Exception as e:
            utils.logger.error(f"[NewsArticleExtractor] 提取文章失败 {url}: {e}")
            return None
    
    def _extract_title_from_content(self, content: str) -> str:
        """从内容中提取标题"""
        if not content:
            return '未知标题'
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 10 and len(line) < 200:
                return line
        return '未知标题'
    
    def _get_site_name(self, domain: str) -> str:
        """根据域名获取网站名称"""
        site_map = {
            'news.sina.com.cn': '新浪新闻',
            'new.qq.com': '腾讯新闻',
            'news.163.com': '网易新闻',
            'news.sohu.com': '搜狐新闻',
            'people.com.cn': '人民网',
            'xinhuanet.com': '新华网',
            'chinanews.com': '中新网',
            'thepaper.cn': '澎湃新闻',
            'finance.sina.com.cn': '新浪财经',
            'finance.qq.com': '腾讯财经',
            'money.163.com': '网易财经',
            'business.sohu.com': '搜狐财经',
            'tech.sina.com.cn': '新浪科技',
            'tech.qq.com': '腾讯科技',
            'tech.163.com': '网易科技',
            'it.sohu.com': '搜狐科技'
        }
        return site_map.get(domain, domain)