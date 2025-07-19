# MediaCrawler Web监控平台

## 项目简介

MediaCrawler Web监控平台是基于MediaCrawler多平台社交媒体数据采集工具构建的专业级Web监控和分析系统。提供直观的数据查询、筛选、搜索和分析功能。

## 功能特性

### 🎯 核心功能
- **多平台数据查询**: 支持小红书、抖音、快手、哔哩哔哩、微博、贴吧、知乎等7大主流平台
- **智能筛选系统**: 平台筛选、时间范围、情感分析、关键词搜索等多维度筛选
- **实时数据展示**: 内容列表、统计图表、趋势分析等多种展示方式
- **情感分析**: 基于AI分析的内容情感倾向识别和评分

### 📊 数据展示
- **内容卡片**: 精美的内容展示卡片，包含标题、摘要、作者、互动数据等
- **统计概览**: 实时数据统计、平台分布、情感分布等关键指标
- **分页浏览**: 高效的分页机制，支持大数据量浏览
- **响应式设计**: 适配不同屏幕尺寸的专业界面

### 🔍 搜索功能
- **关键词搜索**: 支持标题、内容、作者等多字段搜索
- **智能匹配**: 精确匹配、模糊匹配、智能搜索等多种模式
- **搜索历史**: 自动保存搜索历史，支持快速重复搜索
- **热门关键词**: 智能推荐热门搜索关键词

## 技术架构

### 前端技术
- **Streamlit**: 现代化Web框架，快速构建数据应用
- **Custom CSS**: 专业级界面样式定制
- **响应式设计**: 支持多设备访问

### 后端技术
- **SQLAlchemy ORM**: 安全可靠的数据库访问层
- **MySQL**: 生产级数据库支持
- **连接池**: 高效的数据库连接管理

### 数据处理
- **智能缓存**: 查询结果缓存，提升响应速度
- **批量处理**: 高效的数据批量查询和处理
- **错误处理**: 完善的异常处理和恢复机制

## 安装部署

### 环境要求
```bash
Python >= 3.8
MySQL >= 8.0
pip >= 21.0
```

### 快速开始

#### 1. 安装依赖
```bash
cd web
pip install -r requirements.txt
```

#### 2. 配置数据库
确保MediaCrawler主项目的数据库配置正确，Web平台将复用相同的数据库连接。

#### 3. 启动应用
```bash
# 使用启动脚本（推荐）
./run.sh

# 或直接使用streamlit
streamlit run app.py --server.port 8501
```

#### 4. 访问应用
在浏览器中访问: http://localhost:8501

### 配置说明

#### 数据库配置
Web平台自动读取MediaCrawler主项目的数据库配置文件：
```python
# config/db_config.py
RELATION_DB_HOST = "localhost"
RELATION_DB_PORT = 3306
RELATION_DB_USER = "root"
RELATION_DB_PWD = ""
RELATION_DB_NAME = "media_crawler"
```

#### Web应用配置
在 `web/config.py` 中可以调整：
```python
WEB_CONFIG = {
    'app_title': 'MediaCrawler 监控平台',
    'default_page_size': 20,
    'enable_cache': True,
    'cache_ttl': 300,
    # 更多配置项...
}
```

## 使用指南

### 基础操作

#### 1. 平台筛选
- 在侧边栏选择要查看的平台
- 支持单选或多选平台
- 实时显示各平台数据统计

#### 2. 时间筛选
- 支持快捷时间选项：今天、昨天、最近7天等
- 自定义时间范围选择
- 时间范围最大支持1年

#### 3. 关键词搜索
- 在搜索框输入关键词
- 支持多个关键词（空格分隔）
- 智能搜索建议和历史记录

#### 4. 情感筛选
- 根据AI分析结果筛选内容情感
- 支持正面、负面、中性、未知等分类
- 实时显示情感分布统计

### 高级功能

#### 1. 内容分析
- 点击内容卡片的"分析"按钮
- 查看详细的AI分析结果
- 包含情感评分、关键词提取等

#### 2. 数据导出
- 支持搜索结果导出（开发中）
- 多种格式：Excel、CSV、PDF等
- 自定义导出字段和范围

#### 3. 统计分析
- 实时数据统计概览
- 平台分布分析
- 情感趋势分析
- 互动数据统计

## API文档

### 数据查询接口

#### SearchFilters 筛选条件
```python
@dataclass
class SearchFilters:
    platforms: List[str]      # 平台列表
    start_time: datetime      # 开始时间
    end_time: datetime        # 结束时间
    keywords: str             # 搜索关键词
    sentiment: str            # 情感筛选
    page: int                 # 页码
    page_size: int           # 页面大小
    sort_by: str             # 排序字段
    sort_order: str          # 排序方向
```

#### ContentItem 内容项
```python
@dataclass
class ContentItem:
    id: int                   # 内容ID
    platform: str            # 平台标识
    platform_name: str       # 平台名称
    content_id: str          # 平台内容ID
    title: str               # 标题
    content: str             # 内容
    author_name: str         # 作者名称
    publish_time: datetime   # 发布时间
    interaction_count: int   # 互动数量
    sentiment: str           # 情感倾向
    sentiment_score: float   # 情感评分
    url: str                 # 原文链接
```

## 开发指南

### 项目结构
```
web/
├── app.py                    # 主应用入口
├── config.py                 # 配置文件
├── requirements.txt          # 依赖包列表
├── run.sh                   # 启动脚本
├── database/                # 数据库层
│   ├── connection.py        # 数据库连接
│   ├── models.py            # 数据模型
│   └── queries.py           # 查询逻辑
├── components/              # UI组件
│   ├── filters.py           # 筛选组件
│   ├── search.py            # 搜索组件
│   └── data_display.py      # 数据展示组件
├── utils/                   # 工具函数
│   ├── data_processor.py    # 数据处理
│   └── formatters.py        # 格式化工具
└── static/                  # 静态资源
    └── styles.css           # 自定义样式
```

### 扩展开发

#### 添加新的筛选器
1. 在 `components/filters.py` 中添加新的筛选组件
2. 在 `database/queries.py` 中更新 `SearchFilters` 和查询逻辑
3. 在 `app.py` 中集成新的筛选器

#### 添加新的数据展示
1. 在 `components/data_display.py` 中创建新的展示组件
2. 在 `utils/formatters.py` 中添加相应的格式化函数
3. 在主应用中调用新的展示组件

#### 添加新的平台支持
1. 在 `database/models.py` 中添加新的平台模型
2. 在 `PLATFORM_MODELS` 和 `PLATFORM_NAMES` 中注册新平台
3. 在 `database/queries.py` 中更新字段映射

## 性能优化

### 查询优化
- 使用数据库索引优化查询性能
- 实施查询结果缓存机制
- 合理的分页大小控制

### 缓存策略
- 查询结果缓存5分钟
- 平台统计缓存10分钟
- LRU缓存淘汰策略

### 内存管理
- 控制单次查询结果数量
- 及时释放数据库连接
- 优化大数据量的内存使用

## 安全考虑

### 数据安全
- 只读数据访问，不允许修改数据库
- SQL注入防护（使用ORM）
- 敏感信息过滤

### 访问控制
- 默认仅允许本地访问
- 可配置的访问IP白名单
- 后续支持用户认证系统

## 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查数据库配置
cat ../config/db_config.py

# 测试数据库连接
python3 -c "from web.database.connection import db_manager; print(db_manager.test_connection())"
```

#### 2. 页面加载慢
- 检查数据库查询性能
- 清除应用缓存
- 减少查询数据量

#### 3. 搜索结果为空
- 确认数据库中有相应平台数据
- 检查时间范围设置
- 验证搜索关键词

### 日志查看
```bash
# 查看应用日志
tail -f web_app.log

# 查看Streamlit日志
streamlit run app.py --logger.level debug
```

## 更新日志

### v1.0.0 (2025-01-19)
- ✅ 初始版本发布
- ✅ 支持7大主流平台数据查询
- ✅ 完整的筛选和搜索功能
- ✅ 响应式界面设计
- ✅ 情感分析支持
- ✅ 缓存机制优化

## 贡献指南

### 开发环境
1. Fork项目仓库
2. 创建功能分支
3. 提交代码更改
4. 创建Pull Request

### 代码规范
- 使用Black进行代码格式化
- 使用Flake8进行代码检查
- 编写清晰的注释和文档
- 遵循PEP 8编码规范

## 许可证

本项目仅供学习和研究目的使用，请遵守以下原则：
1. 不得用于任何商业用途
2. 使用时应遵守目标平台的使用条款
3. 不得进行大规模爬取或对平台造成干扰
4. 应合理控制请求频率

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 邮箱: your-email@example.com

---

🚀 **MediaCrawler Web监控平台** - 让数据监控更简单、更专业！