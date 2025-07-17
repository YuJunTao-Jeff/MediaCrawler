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

## 浏览器自动化+网络拦截通用爬取技术方案

### 技术方案概述
**记录时间**: 2025-07-17
**方案描述**: 一种更好更通用的爬取技术方案，使用真实浏览器自动化模拟用户操作，同时拦截网络请求数据进行解析存储。

### 核心技术优势

#### 1. 强反风控能力
- **真实浏览器环境**: 完整的JS执行环境、Cookie管理、渲染引擎
- **用户行为模拟**: 真实的鼠标点击、键盘输入、页面滚动等操作
- **指纹一致性**: 浏览器指纹、User-Agent、TLS指纹都是真实的
- **动态内容处理**: 能够处理复杂的SPA应用和动态加载的内容

#### 2. 技术实现栈
- **浏览器自动化**: Playwright (推荐) / Puppeteer / Selenium
- **网络拦截**: Playwright的network interception / Chrome DevTools Protocol
- **数据解析**: 从拦截的网络包中提取JSON数据
- **存储处理**: 标准化的数据存储流程

#### 3. 实现示例代码
```python
async def crawl_with_browser_automation(platform, keywords):
    """浏览器自动化+网络拦截的通用爬取实现"""
    
    # 1. 启动浏览器
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    
    # 2. 设置网络拦截
    intercepted_data = []
    
    async def handle_response(response):
        # 拦截目标API响应
        if any(api in response.url for api in ['api/search', 'api/list', 'api/feed']):
            try:
                data = await response.json()
                intercepted_data.append({
                    'url': response.url,
                    'data': data,
                    'timestamp': int(time.time())
                })
            except:
                pass
    
    page.on('response', handle_response)
    
    # 3. 模拟用户操作
    await page.goto(f'https://{platform}.com')
    await page.wait_for_load_state('networkidle')
    
    # 模拟搜索操作
    await page.fill('input[name="search"]', keywords)
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(2000)
    
    # 模拟滚动加载更多内容
    for i in range(3):
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(1000)
    
    # 4. 处理拦截到的数据
    for item in intercepted_data:
        await process_and_store_data(item['data'])
    
    await browser.close()
    return len(intercepted_data)
```

#### 4. 方案优势对比
| 维度 | 传统API爬取 | 浏览器自动化+网络拦截 |
|------|-------------|----------------------|
| 反风控检测 | 容易被检测 | 检测难度极高 |
| 性能效率 | 高 | 中等 |
| 维护成本 | 高(需要逆向API) | 低(跟随界面变化) |
| 稳定性 | 低(API经常变化) | 高(界面相对稳定) |
| 资源消耗 | 低 | 高 |
| 并发能力 | 强 | 受限 |

#### 5. 适用场景
- **现代SPA应用**: React、Vue、Angular等前端框架构建的应用
- **登录保护平台**: 需要用户登录才能访问的内容
- **强反爬机制**: 有复杂反爬虫检测的网站
- **动态内容**: 需要用户交互才能加载的内容
- **复杂操作流程**: 需要多步骤操作的爬取场景

### MediaCrawler项目应用策略

#### 1. 混合架构设计
```python
class UniversalCrawler:
    def __init__(self):
        self.browser_mode = True  # 优先使用浏览器模式
        self.api_fallback = True  # API模式作为备选
        self.adaptive_mode = True  # 智能模式选择
    
    async def crawl(self, platform, keywords):
        if self.adaptive_mode:
            # 根据平台特性自动选择模式
            mode = self.select_optimal_mode(platform)
        else:
            mode = 'browser' if self.browser_mode else 'api'
        
        try:
            if mode == 'browser':
                return await self.browser_crawl(platform, keywords)
            else:
                return await self.api_crawl(platform, keywords)
        except Exception as e:
            if self.api_fallback and mode == 'browser':
                return await self.api_crawl(platform, keywords)
            raise e
```

#### 2. 实施建议
1. **试点平台**: 选择小红书或抖音作为试点实现
2. **统一框架**: 建立统一的网络拦截和数据处理框架
3. **智能降级**: 浏览器模式失败时自动降级到API模式
4. **行为模式库**: 建立真实用户行为模式数据库
5. **分布式部署**: 通过分布式浏览器集群解决性能瓶颈

#### 3. 技术挑战与解决方案
**挑战1: 资源消耗大**
- 解决方案: 分布式浏览器集群、资源池管理、智能调度

**挑战2: 并发能力限制**
- 解决方案: 多浏览器实例、负载均衡、任务队列

**挑战3: 反检测进阶**
- 解决方案: 浏览器指纹随机化、操作时间随机化、代理IP轮换

**挑战4: 错误处理复杂**
- 解决方案: 完善的异常处理机制、自动重试、状态监控

### 项目集成计划

#### 阶段1: 基础框架搭建
1. 创建通用浏览器自动化基类
2. 实现网络拦截和数据解析框架
3. 建立用户行为模拟库

#### 阶段2: 试点平台实现
1. 选择一个平台进行完整实现
2. 验证技术方案的可行性
3. 优化性能和稳定性

#### 阶段3: 全平台推广
1. 将方案扩展到所有支持的平台
2. 建立统一的配置和管理系统
3. 实现智能模式选择和自动降级

#### 阶段4: 高级特性
1. 分布式部署和负载均衡
2. 机器学习驱动的行为模式优化
3. 实时监控和告警系统

### 配置参数扩展
```python
# 浏览器自动化配置
BROWSER_AUTOMATION_ENABLED = True
BROWSER_AUTOMATION_MODE = "playwright"  # playwright | puppeteer | selenium
BROWSER_CONCURRENCY = 3  # 并发浏览器数量
BROWSER_TIMEOUT = 30  # 浏览器操作超时时间

# 网络拦截配置
NETWORK_INTERCEPTION_ENABLED = True
NETWORK_INTERCEPTION_PATTERNS = ["*/api/*", "*/search/*", "*/list/*"]
NETWORK_RESPONSE_TIMEOUT = 10

# 用户行为模拟配置
USER_BEHAVIOR_SIMULATION = True
SCROLL_BEHAVIOR_ENABLED = True
CLICK_BEHAVIOR_ENABLED = True
TYPING_BEHAVIOR_ENABLED = True
BEHAVIOR_RANDOMIZATION = True

# 降级策略配置
AUTO_FALLBACK_ENABLED = True
FALLBACK_THRESHOLD = 3  # 失败次数阈值
FALLBACK_MODE = "api"  # 降级模式
```

### 使用示例
```bash
# 启用浏览器自动化模式
python main.py --platform xhs --type search --keywords "test" --browser_automation true

# 混合模式(浏览器+API降级)
python main.py --platform xhs --type search --keywords "test" --hybrid_mode true

# 指定浏览器并发数
python main.py --platform xhs --type search --keywords "test" --browser_concurrency 5
```

这种浏览器自动化+网络拦截的技术方案代表了现代爬虫技术的发展方向，能够有效应对日益复杂的反爬虫机制，是MediaCrawler项目未来发展的重要技术储备。