# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


class NewsStoreSql:
    """新闻存储SQL语句"""
    
    # 插入或更新新闻文章
    UPSERT_NEWS_ARTICLE = """
        INSERT INTO news_article (
            article_id, source_url, title, content, summary, keywords, authors, 
            publish_date, source_domain, source_site, top_image, word_count, 
            language, metadata, add_ts, last_modify_ts
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            content = VALUES(content),
            summary = VALUES(summary),
            keywords = VALUES(keywords),
            authors = VALUES(authors),
            publish_date = VALUES(publish_date),
            source_domain = VALUES(source_domain),
            source_site = VALUES(source_site),
            top_image = VALUES(top_image),
            word_count = VALUES(word_count),
            language = VALUES(language),
            metadata = VALUES(metadata),
            last_modify_ts = VALUES(last_modify_ts)
    """
    
    # 插入搜索结果
    INSERT_SEARCH_RESULT = """
        INSERT INTO news_search_result (
            search_keyword, search_engine, result_title, result_url, result_score, 
            result_description, article_id, add_ts, last_modify_ts
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    
    # 根据关键词查询文章
    SELECT_ARTICLES_BY_KEYWORD = """
        SELECT na.* FROM news_article na
        INNER JOIN news_search_result nsr ON na.article_id = nsr.article_id
        WHERE nsr.search_keyword = %s
        ORDER BY na.add_ts DESC
        LIMIT %s
    """
    
    # 根据文章ID查询文章
    SELECT_ARTICLE_BY_ID = """
        SELECT * FROM news_article WHERE article_id = %s
    """
    
    # 查询文章总数
    SELECT_ARTICLE_COUNT = """
        SELECT COUNT(*) as count FROM news_article
    """
    
    # 查询搜索结果总数
    SELECT_SEARCH_RESULT_COUNT = """
        SELECT COUNT(*) as count FROM news_search_result
    """
    
    # 根据域名查询文章
    SELECT_ARTICLES_BY_DOMAIN = """
        SELECT * FROM news_article 
        WHERE source_domain = %s 
        ORDER BY add_ts DESC 
        LIMIT %s
    """
    
    # 查询最新文章
    SELECT_LATEST_ARTICLES = """
        SELECT * FROM news_article 
        WHERE publish_date IS NOT NULL 
        ORDER BY publish_date DESC 
        LIMIT %s
    """
    
    # 插入或更新搜索任务
    UPSERT_SEARCH_TASK = """
        INSERT INTO news_search_task (
            task_id, keywords, search_engines, status, total_results, 
            extracted_articles, failed_extractions, start_time, end_time, 
            error_info, add_ts, last_modify_ts
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON DUPLICATE KEY UPDATE
            keywords = VALUES(keywords),
            search_engines = VALUES(search_engines),
            status = VALUES(status),
            total_results = VALUES(total_results),
            extracted_articles = VALUES(extracted_articles),
            failed_extractions = VALUES(failed_extractions),
            start_time = VALUES(start_time),
            end_time = VALUES(end_time),
            error_info = VALUES(error_info),
            last_modify_ts = VALUES(last_modify_ts)
    """
    
    # 查询搜索任务
    SELECT_SEARCH_TASK = """
        SELECT * FROM news_search_task WHERE task_id = %s
    """
    
    # 删除文章
    DELETE_ARTICLE = """
        DELETE FROM news_article WHERE article_id = %s
    """
    
    # 删除搜索结果
    DELETE_SEARCH_RESULTS_BY_ARTICLE = """
        DELETE FROM news_search_result WHERE article_id = %s
    """