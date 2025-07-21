-- ----------------------------
-- Table structure for news_search_result
-- ----------------------------
CREATE TABLE `news_search_result`
(
    `id`                  int          NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `search_keyword`      varchar(255) NOT NULL COMMENT '搜索关键词',
    `search_engine`       varchar(64)  NOT NULL COMMENT '搜索引擎',
    `result_title`        varchar(500) NOT NULL COMMENT '搜索结果标题',
    `result_url`          varchar(1000) NOT NULL COMMENT '搜索结果URL',
    `result_score`        float        DEFAULT NULL COMMENT '搜索结果评分',
    `result_description`  text         COMMENT '搜索结果描述',
    `article_id`          varchar(128) COMMENT '关联的文章ID',
    `add_ts`              bigint       NOT NULL COMMENT '记录添加时间戳',
    `last_modify_ts`      bigint       NOT NULL COMMENT '记录最后修改时间戳',
    PRIMARY KEY (`id`),
    KEY                   `idx_search_keyword` (`search_keyword`),
    KEY                   `idx_search_engine` (`search_engine`),
    KEY                   `idx_article_id` (`article_id`),
    KEY                   `idx_add_ts` (`add_ts`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='新闻搜索结果表';

-- ----------------------------
-- Table structure for news_article
-- ----------------------------
CREATE TABLE `news_article`
(
    `id`                  int          NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `article_id`          varchar(128) NOT NULL COMMENT '文章唯一ID(URL的MD5)',
    `source_url`          varchar(1000) NOT NULL COMMENT '原始URL',
    `title`               varchar(500) NOT NULL COMMENT '文章标题',
    `content`             longtext     COMMENT '文章正文内容',
    `summary`             text         COMMENT '文章摘要',
    `keywords`            json         COMMENT '关键词列表',
    `authors`             json         COMMENT '作者列表',
    `publish_date`        datetime     COMMENT '发布时间(newspaper3k提取)',
    `source_domain`       varchar(255) COMMENT '来源域名',
    `source_site`         varchar(255) COMMENT '来源网站名称',
    `source_keyword` varchar(64) DEFAULT NULL COMMENT '来源关键词',
    `top_image`           varchar(1000) COMMENT '文章主图URL',
    `word_count`          int          COMMENT '字数统计',
    `language`            varchar(32)  DEFAULT 'zh' COMMENT '语言',
    `metadata`            json         COMMENT '其他元数据',
    `add_ts`              bigint       NOT NULL COMMENT '记录添加时间戳',
    `last_modify_ts`      bigint       NOT NULL COMMENT '记录最后修改时间戳',
    PRIMARY KEY (`id`),
    UNIQUE KEY            `uk_article_id` (`article_id`),
    KEY                   `idx_source_domain` (`source_domain`),
    KEY                   `idx_source_site` (`source_site`),
    KEY                   `idx_publish_date` (`publish_date`),
    KEY                   `idx_add_ts` (`add_ts`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='新闻文章内容表';

-- ----------------------------
-- Table structure for news_search_task
-- ----------------------------
CREATE TABLE `news_search_task`
(
    `id`                  int          NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `task_id`             varchar(128) NOT NULL COMMENT '任务唯一ID',
    `keywords`            text         NOT NULL COMMENT '搜索关键词列表',
    `search_engines`      json         COMMENT '搜索引擎配置',
    `status`              varchar(32)  NOT NULL DEFAULT 'pending' COMMENT '任务状态',
    `total_results`       int          DEFAULT 0 COMMENT '总搜索结果数',
    `extracted_articles`  int          DEFAULT 0 COMMENT '成功提取文章数',
    `failed_extractions`  int          DEFAULT 0 COMMENT '提取失败数',
    `start_time`          datetime     COMMENT '开始时间',
    `end_time`            datetime     COMMENT '结束时间',
    `error_info`          text         COMMENT '错误信息',
    `add_ts`              bigint       NOT NULL COMMENT '记录添加时间戳',
    `last_modify_ts`      bigint       NOT NULL COMMENT '记录最后修改时间戳',
    PRIMARY KEY (`id`),
    UNIQUE KEY            `uk_task_id` (`task_id`),
    KEY                   `idx_status` (`status`),
    KEY                   `idx_start_time` (`start_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='新闻搜索任务表';