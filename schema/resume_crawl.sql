-- ----------------------------
-- Table structure for crawl_task
-- ----------------------------
DROP TABLE IF EXISTS `crawl_task`;
CREATE TABLE `crawl_task`
(
    `id`                int         NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `task_id`           varchar(64) NOT NULL COMMENT '任务ID',
    `platform`          varchar(16) NOT NULL COMMENT '平台名称',
    `crawler_type`      varchar(16) NOT NULL COMMENT '爬取类型',
    `keywords`          text        NOT NULL COMMENT '关键词列表',
    `total_keywords`    int         NOT NULL DEFAULT 0 COMMENT '总关键词数',
    `completed_keywords` int        NOT NULL DEFAULT 0 COMMENT '已完成关键词数',
    `status`            varchar(16) NOT NULL DEFAULT 'running' COMMENT '任务状态 running/paused/completed/failed',
    `start_time`        bigint      NOT NULL COMMENT '开始时间',
    `last_update_time`  bigint      NOT NULL COMMENT '最后更新时间',
    `estimated_end_time` bigint     DEFAULT NULL COMMENT '预计结束时间',
    `total_items`       int         NOT NULL DEFAULT 0 COMMENT '总条目数',
    `config_snapshot`   text        DEFAULT NULL COMMENT '配置快照',
    `error_message`     text        DEFAULT NULL COMMENT '错误信息',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_task_id` (`task_id`),
    KEY `idx_platform_status` (`platform`, `status`),
    KEY `idx_start_time` (`start_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='爬取任务表';

-- ----------------------------
-- Table structure for keyword_progress
-- ----------------------------
DROP TABLE IF EXISTS `keyword_progress`;
CREATE TABLE `keyword_progress`
(
    `id`              int         NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `task_id`         varchar(64) NOT NULL COMMENT '任务ID',
    `keyword`         varchar(255) NOT NULL COMMENT '关键词',
    `platform`        varchar(16) NOT NULL COMMENT '平台名称',
    `current_page`    int         NOT NULL DEFAULT 1 COMMENT '当前页数',
    `total_pages`     int         DEFAULT NULL COMMENT '总页数',
    `items_count`     int         NOT NULL DEFAULT 0 COMMENT '已爬取条目数',
    `last_item_time`  bigint      DEFAULT NULL COMMENT '最后条目时间戳',
    `last_item_id`    varchar(255) DEFAULT NULL COMMENT '最后条目ID',
    `status`          varchar(16) NOT NULL DEFAULT 'running' COMMENT '关键词状态 running/completed/failed',
    `start_time`      bigint      NOT NULL COMMENT '开始时间',
    `last_update_time` bigint     NOT NULL COMMENT '最后更新时间',
    `completion_time` bigint      DEFAULT NULL COMMENT '完成时间',
    `error_message`   text        DEFAULT NULL COMMENT '错误信息',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_task_keyword` (`task_id`, `keyword`),
    KEY `idx_platform_status` (`platform`, `status`),
    KEY `idx_last_update_time` (`last_update_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='关键词进度表';

-- ----------------------------
-- Table structure for crawl_statistics
-- ----------------------------
DROP TABLE IF EXISTS `crawl_statistics`;
CREATE TABLE `crawl_statistics`
(
    `id`              int         NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `task_id`         varchar(64) NOT NULL COMMENT '任务ID',
    `platform`        varchar(16) NOT NULL COMMENT '平台名称',
    `stat_date`       date        NOT NULL COMMENT '统计日期',
    `total_items`     int         NOT NULL DEFAULT 0 COMMENT '总条目数',
    `new_items`       int         NOT NULL DEFAULT 0 COMMENT '新增条目数',
    `duplicate_items` int         NOT NULL DEFAULT 0 COMMENT '重复条目数',
    `failed_items`    int         NOT NULL DEFAULT 0 COMMENT '失败条目数',
    `avg_crawl_speed` decimal(10,2) DEFAULT NULL COMMENT '平均爬取速度(条/秒)',
    `total_time`      bigint      NOT NULL DEFAULT 0 COMMENT '总耗时(毫秒)',
    `create_time`     bigint      NOT NULL COMMENT '创建时间',
    `update_time`     bigint      NOT NULL COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_task_platform_date` (`task_id`, `platform`, `stat_date`),
    KEY `idx_stat_date` (`stat_date`),
    KEY `idx_platform` (`platform`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='爬取统计表';

-- ----------------------------
-- Table structure for crawl_checkpoints
-- ----------------------------
DROP TABLE IF EXISTS `crawl_checkpoints`;
CREATE TABLE `crawl_checkpoints`
(
    `id`              int         NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `task_id`         varchar(64) NOT NULL COMMENT '任务ID',
    `keyword`         varchar(255) NOT NULL COMMENT '关键词',
    `platform`        varchar(16) NOT NULL COMMENT '平台名称',
    `page_number`     int         NOT NULL COMMENT '页码',
    `checkpoint_data` text        NOT NULL COMMENT '检查点数据(JSON)',
    `items_processed` int         NOT NULL DEFAULT 0 COMMENT '已处理条目数',
    `last_item_hash`  varchar(64) DEFAULT NULL COMMENT '最后条目哈希',
    `created_time`    bigint      NOT NULL COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_task_keyword_page` (`task_id`, `keyword`, `page_number`),
    KEY `idx_platform_created` (`platform`, `created_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='爬取检查点表';