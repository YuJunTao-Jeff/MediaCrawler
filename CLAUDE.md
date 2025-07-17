# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MediaCrawler is a multi-platform social media data collection tool that supports major Chinese platforms including XHS (小红书), Douyin (抖音), Kuaishou (快手), Bilibili, Weibo (微博), Tieba (贴吧), and Zhihu (知乎). The project uses Playwright for browser automation and provides robust anti-detection capabilities.

## Essential Commands

### Environment Setup
```bash
# Install dependencies (recommended)
uv sync

# Install browser drivers
uv run playwright install

# Alternative: Using Python venv (not recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
playwright install
```

### Running the Crawler
```bash
# Basic usage
uv run main.py --platform xhs --lt qrcode --type search

# Using the launch script (recommended)
./scripts/run.sh --platform xhs --keywords "澳鹏科技"

# Common parameters
--platform: xhs | dy | ks | bili | wb | tieba | zhihu
--lt: qrcode | phone | cookie (login type)
--type: search | detail | creator (crawler type)
--cdp_mode: true | false (Chrome DevTools Protocol mode)
--resume_crawl: true | false (enable resume crawling)
```

### Database Operations
```bash
# Initialize database tables (first time only)
python db.py

# MySQL service management
sudo service mysql start
sudo service mysql status
```

### Testing and Development
```bash
# Run specific platform with debugging
python main.py --platform xhs --lt qrcode --type search --keywords "test"

# Show platform configuration
./scripts/run.sh --platform xhs --show-config

# Browser management for CDP mode
./scripts/start_browser.sh
./scripts/stop_browser.sh
```

## Core Architecture

### Factory Pattern
- **CrawlerFactory**: Creates platform-specific crawler instances
- **AbstractCrawler**: Base class defining common crawler interface
- All platform crawlers inherit from `AbstractCrawler`

### Key Components
- **media_platform/**: Platform-specific implementations
  - `core.py`: Main crawler logic
  - `client.py`: HTTP client for API calls
  - `field.py`: Data field definitions
  - `help.py`: Utility functions
  - `login.py`: Authentication logic

- **store/**: Database storage implementations
  - Platform-specific SQL operations
  - Data persistence layer

- **model/**: Pydantic data models
  - `m_[platform].py`: Platform-specific data structures

- **config/**: Configuration management
  - `base_config.py`: Main configuration file
  - Platform-specific settings

### Resume Crawling System
The project includes a sophisticated resume crawling system:
- **Progress Tracking**: `tools/crawl_progress.py`
- **Database Schema**: `schema/resume_crawl.sql`
- **Automatic Resumption**: Continues from last crawled position
- **Platform Integration**: All platforms support resume crawling

### Browser Automation Modes
1. **Standard Mode**: Uses Playwright's built-in browser
2. **CDP Mode**: Connects to user's existing Chrome/Edge browser
   - Better anti-detection capabilities
   - Uses real browser environment with extensions
   - Configured via `ENABLE_CDP_MODE` in config

## Configuration System

### Main Configuration (`config/base_config.py`)
```python
# Platform and crawling settings
PLATFORM = "xhs"
KEYWORDS = "search,keywords,here"
CRAWLER_TYPE = "search"  # search | detail | creator

# Browser and automation
HEADLESS = False
ENABLE_CDP_MODE = False
SAVE_LOGIN_STATE = True

# Resume crawling
ENABLE_RESUME_CRAWL = True
RESUME_TASK_ID = None

# Data storage
SAVE_DATA_OPTION = "db"  # csv | db | json

# Proxy settings
ENABLE_IP_PROXY = True
IP_PROXY_POOL_COUNT = 2
IP_PROXY_PROVIDER_NAME = "kuaidaili"
```

### Platform-Specific Configurations
Located in `scripts/config/[platform].json`:
- CDP mode settings
- Default parameters
- Platform-specific options

## Database Schema

### Core Tables
- Each platform has dedicated tables for posts, comments, and user info
- Common fields: `id`, `add_ts`, `last_modify_ts`
- Platform-specific fields defined in `schema/tables.sql`

### Resume Crawling Tables
- `crawl_progress`: Tracks crawling progress per keyword
- `crawl_tasks`: Manages crawling tasks
- `crawl_statistics`: Stores crawling statistics

## DataHarvest Integration Plan

### Overview
Integration of DataHarvest (~/appen/dataharvest) for news search engine functionality:

### New Platform: News
Create `media_platform/news/` module with:
- **NewsSearchClient**: Multi-search engine support (Tavily, Tiangong)
- **NewsArticleExtractor**: Content extraction using DataHarvest + newspaper3k
- **NewsStorageLayer**: Database operations for news data

### Database Schema Extensions
```sql
-- News search results table
CREATE TABLE `news_search_result` (
    `id` int NOT NULL AUTO_INCREMENT,
    `search_keyword` varchar(255) NOT NULL,
    `search_engine` varchar(64) NOT NULL,
    `result_title` varchar(500) NOT NULL,
    `result_url` varchar(1000) NOT NULL,
    `result_score` float DEFAULT NULL,
    `result_description` text,
    `article_id` varchar(128),
    `add_ts` bigint NOT NULL,
    `last_modify_ts` bigint NOT NULL,
    PRIMARY KEY (`id`)
);

-- News articles table
CREATE TABLE `news_article` (
    `id` int NOT NULL AUTO_INCREMENT,
    `article_id` varchar(128) NOT NULL,
    `source_url` varchar(1000) NOT NULL,
    `title` varchar(500) NOT NULL,
    `content` longtext,
    `summary` text,
    `keywords` json,
    `authors` json,
    `publish_date` datetime,  -- Using newspaper3k extraction
    `source_domain` varchar(255),
    `source_site` varchar(255),
    `top_image` varchar(1000),
    `word_count` int,
    `language` varchar(32) DEFAULT 'zh',
    `metadata` json,
    `add_ts` bigint NOT NULL,
    `last_modify_ts` bigint NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_article_id` (`article_id`)
);
```

### Implementation Strategy
1. **Content Extraction**: Use DataHarvest for web scraping, newspaper3k for article parsing
2. **Publication Time**: Rely on newspaper3k's built-in time extraction (returns None if not found)
3. **Multi-Engine Search**: Support multiple search engines with unified interface
4. **Resume Crawling**: Full integration with existing resume crawling system

### Configuration Extensions
```python
# News search configuration
NEWS_SEARCH_ENGINES = ["tavily", "tiangong"]
NEWS_MAX_RESULTS_PER_KEYWORD = 10
TAVILY_API_KEY = ""
TIANGONG_API_KEY = ""
```

### Usage Examples
```bash
# News search with DataHarvest
python main.py --platform news --type search --keywords "澳鹏,AI公司"

# With resume crawling
python main.py --platform news --type search --keywords "澳鹏,AI公司" --resume_crawl true

# Using launch script
./scripts/run.sh --platform news --type search --keywords "澳鹏,AI公司"
```

## Development Guidelines

### Adding New Platforms
1. Create module in `media_platform/[platform]/`
2. Implement `AbstractCrawler` interface
3. Add data models in `model/m_[platform].py`
4. Create storage layer in `store/[platform]/`
5. Update `CrawlerFactory.CRAWLERS` mapping
6. Add database schema in `schema/tables.sql`

### Testing Platforms
```bash
# Test platform startup
python main.py --platform [platform] --lt qrcode --type search --keywords "test"

# Use launch script for full testing
./scripts/run.sh --platform [platform]
```

### Proxy System
- Supports multiple proxy providers
- Configuration in `proxy/providers/`
- IP pool management with automatic rotation
- Provider-specific implementations (kuaidaili, etc.)

## Important Notes

### Legal Compliance
- **学习研究目的**: This project is for educational and research purposes only
- **遵守平台规则**: Must comply with platform terms of service and robots.txt
- **合理请求频率**: Control request frequency to avoid platform interference
- **禁止商业用途**: No commercial use allowed

### Browser Configuration
- **CDP Mode**: Better anti-detection, uses real browser environment
- **Standard Mode**: Uses Playwright's built-in browser
- **Login State**: Automatically saved and restored
- **User Data**: Stored in `browser_data/[platform]_user_data_dir/`

### Data Storage
- **MySQL**: Recommended for production use (has deduplication)
- **CSV/JSON**: For simple data export
- **Database**: Initialize with `python db.py` before first use

### Resume Crawling
- **Automatic**: Continues from last position on restart
- **Progress Tracking**: Saves progress per keyword and page
- **Statistics**: Tracks success/failure rates
- **Configuration**: Enable via `ENABLE_RESUME_CRAWL = True`

This architecture provides a robust foundation for multi-platform social media crawling with excellent extensibility for adding new platforms and features like the planned DataHarvest news search integration.