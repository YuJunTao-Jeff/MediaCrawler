-- 为news_article表添加source_keyword字段
-- 执行时间: 2025-07-21

ALTER TABLE `news_article` 
ADD COLUMN `source_keyword` varchar(255) DEFAULT NULL COMMENT '搜索关键词' 
AFTER `article_metadata`;