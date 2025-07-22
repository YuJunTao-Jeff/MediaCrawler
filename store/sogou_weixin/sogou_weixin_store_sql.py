# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


# -*- coding: utf-8 -*-

class SogouWeixinStoreSql:
    """搜狗微信存储SQL语句"""
    
    # 插入或更新微信文章
    INSERT_WEIXIN_ARTICLE = """
        INSERT INTO weixin_article (
            article_id, title, content, summary, account_name, account_id,
            cover_image, original_url, publish_time, publish_timestamp,
            read_count, like_count, source_keyword, analysis_info, add_ts, last_modify_ts
        ) VALUES (
            %(article_id)s, %(title)s, %(content)s, %(summary)s, %(account_name)s, %(account_id)s,
            %(cover_image)s, %(original_url)s, %(publish_time)s, %(publish_timestamp)s,
            %(read_count)s, %(like_count)s, %(source_keyword)s, %(analysis_info)s, %(add_ts)s, %(last_modify_ts)s
        ) ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            content = VALUES(content),
            summary = VALUES(summary),
            account_name = VALUES(account_name),
            account_id = VALUES(account_id),
            cover_image = VALUES(cover_image),
            publish_time = VALUES(publish_time),
            publish_timestamp = VALUES(publish_timestamp),
            read_count = VALUES(read_count),
            like_count = VALUES(like_count),
            source_keyword = VALUES(source_keyword),
            analysis_info = VALUES(analysis_info),
            last_modify_ts = VALUES(last_modify_ts)
    """
    
    # 查询微信文章
    QUERY_WEIXIN_ARTICLE = """
        SELECT wa.* FROM weixin_article wa
        WHERE wa.add_ts BETWEEN %(begin_time)s AND %(end_time)s
        ORDER BY wa.add_ts DESC
        LIMIT %(size)s OFFSET %(offset)s
    """
    
    # 根据文章ID查询
    QUERY_WEIXIN_ARTICLE_BY_ID = """
        SELECT * FROM weixin_article WHERE article_id = %(article_id)s
    """
    
    # 统计文章数量
    COUNT_WEIXIN_ARTICLES = """
        SELECT COUNT(*) as count FROM weixin_article
        WHERE add_ts BETWEEN %(begin_time)s AND %(end_time)s
    """
    
    # 根据关键词查询文章
    QUERY_WEIXIN_ARTICLES_BY_KEYWORD = """
        SELECT * FROM weixin_article 
        WHERE source_keyword = %(keyword)s
        ORDER BY add_ts DESC
        LIMIT %(limit)s
    """
    
    # 根据公众号名称查询文章
    QUERY_WEIXIN_ARTICLES_BY_ACCOUNT = """
        SELECT * FROM weixin_article 
        WHERE account_name = %(account_name)s
        ORDER BY add_ts DESC
        LIMIT %(limit)s
    """
    
    # 删除微信文章
    DELETE_WEIXIN_ARTICLE = """
        DELETE FROM weixin_article WHERE article_id = %(article_id)s
    """
    
    # 批量插入文章（用于高效批量操作）
    BATCH_INSERT_WEIXIN_ARTICLES = """
        INSERT INTO weixin_article (
            article_id, title, content, summary, account_name, account_id,
            cover_image, original_url, publish_time, publish_timestamp,
            read_count, like_count, source_keyword, analysis_info, add_ts, last_modify_ts
        ) VALUES (
            %(article_id)s, %(title)s, %(content)s, %(summary)s, %(account_name)s, %(account_id)s,
            %(cover_image)s, %(original_url)s, %(publish_time)s, %(publish_timestamp)s,
            %(read_count)s, %(like_count)s, %(source_keyword)s, %(analysis_info)s, %(add_ts)s, %(last_modify_ts)s
        ) ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            content = VALUES(content),
            summary = VALUES(summary),
            account_name = VALUES(account_name),
            account_id = VALUES(account_id),
            cover_image = VALUES(cover_image),
            publish_time = VALUES(publish_time),
            publish_timestamp = VALUES(publish_timestamp),
            read_count = VALUES(read_count),
            like_count = VALUES(like_count),
            source_keyword = VALUES(source_keyword),
            analysis_info = VALUES(analysis_info),
            last_modify_ts = VALUES(last_modify_ts)
    """