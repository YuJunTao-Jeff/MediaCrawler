# MediaCrawler Web监控平台技术方案

## 1. 技术架构概述

### 1.1 整体架构
```
┌─────────────────────────────────────────────────────────────┐
│                    Web Browser                              │
│                 (Chrome/Firefox/Safari)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                 Streamlit Web Server                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │    UI       │ │  Business   │ │      Static Files       │ │
│  │ Components  │ │   Logic     │ │   (CSS/JS/Images)       │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │ SQLAlchemy ORM
┌─────────────────────▼───────────────────────────────────────┐
│                   MySQL Database                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │    Data     │ │   Indexes   │ │      Connection         │ │
│  │   Tables    │ │             │ │        Pool             │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈选择

#### 前端技术栈
- **核心框架**: Streamlit 1.28+
- **样式定制**: Custom CSS + Streamlit Components
- **图表库**: Plotly (Streamlit内置)
- **响应式**: Streamlit的原生响应式支持

#### 后端技术栈
- **Web框架**: Streamlit (Python Web框架)
- **ORM框架**: SQLAlchemy 2.0+
- **数据库**: MySQL 8.0+ (复用现有数据库)
- **连接池**: SQLAlchemy连接池管理

#### 开发工具
- **包管理**: pip/conda
- **代码规范**: Black + Flake8
- **测试框架**: pytest
- **部署**: 直接运行/Docker可选

## 2. 数据层设计

### 2.1 数据库连接管理

#### 连接配置
```python
# database/connection.py
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'media_crawler',
    'username': 'root',
    'password': '',
    'charset': 'utf8mb4',
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 3600
}
```

#### 连接池策略
- **基础连接数**: 5个连接
- **最大连接数**: 20个连接
- **连接超时**: 30秒
- **连接回收**: 1小时
- **重连机制**: 自动重连 + 错误处理

### 2.2 ORM模型设计

#### 统一基类
```python
class BaseModel:
    """所有模型的基类"""
    id = Column(Integer, primary_key=True)
    add_ts = Column(BigInteger, nullable=False)
    last_modify_ts = Column(BigInteger, nullable=False)
    
    @classmethod
    def get_table_name(cls):
        return cls.__tablename__
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

#### 平台模型映射
```python
PLATFORM_MODELS = {
    'xhs': XhsNote,           # 小红书
    'douyin': DouyinAweme,    # 抖音
    'kuaishou': KuaishousVideo, # 快手
    'bilibili': BilibiliVideo, # 哔哩哔哩
    'weibo': WeiboNote,       # 微博
    'tieba': TiebaNote,       # 贴吧
    'zhihu': ZhihuContent     # 知乎
}
```

### 2.3 查询优化策略

#### 索引设计
```sql
-- 时间范围查询索引
CREATE INDEX idx_publish_time ON xhs_note(publish_time);
CREATE INDEX idx_add_ts ON xhs_note(add_ts);

-- 全文搜索索引
CREATE FULLTEXT INDEX idx_title_content ON xhs_note(title, desc);

-- 复合索引
CREATE INDEX idx_platform_time ON xhs_note(add_ts, publish_time);
```

#### 查询优化
- **分页查询**: LIMIT + OFFSET优化
- **条件查询**: 合理使用索引
- **排序优化**: 避免filesort
- **连接查询**: 适当使用JOIN

## 3. 业务逻辑层设计

### 3.1 数据查询服务

#### 查询接口设计
```python
class DataQueryService:
    """数据查询服务"""
    
    def search_content(self, filters: SearchFilters) -> PaginatedResult:
        """搜索内容"""
        pass
    
    def get_platform_stats(self) -> Dict[str, int]:
        """获取平台统计"""
        pass
    
    def get_sentiment_distribution(self, filters: SearchFilters) -> Dict:
        """获取情感分布"""
        pass
```

#### 筛选条件处理
```python
@dataclass
class SearchFilters:
    """搜索筛选条件"""
    platforms: List[str] = None          # 平台筛选
    start_time: datetime = None          # 开始时间
    end_time: datetime = None            # 结束时间
    keywords: str = None                 # 关键词搜索
    sentiment: str = None                # 情感筛选
    page: int = 1                        # 页码
    page_size: int = 20                  # 页面大小
    sort_by: str = 'publish_time'        # 排序字段
    sort_order: str = 'desc'             # 排序方向
```

### 3.2 数据处理服务

#### 数据格式化
```python
class DataFormatter:
    """数据格式化器"""
    
    @staticmethod
    def format_number(num: int) -> str:
        """格式化数字显示"""
        if num >= 10000:
            return f"{num/10000:.1f}万"
        return str(num)
    
    @staticmethod
    def format_time(timestamp) -> str:
        """格式化时间显示"""
        return timestamp.strftime("%Y-%m-%d %H:%M")
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100) -> str:
        """截断文本"""
        return text[:max_length] + "..." if len(text) > max_length else text
```

### 3.3 缓存策略

#### 缓存配置
```python
CACHE_CONFIG = {
    'enable': True,
    'backend': 'memory',  # memory/redis
    'ttl': 300,          # 5分钟
    'max_size': 1000     # 最大缓存条目
}
```

#### 缓存策略
- **查询结果缓存**: 相同条件5分钟内复用结果
- **统计数据缓存**: 平台统计数据缓存10分钟
- **LRU淘汰**: 最近最少使用的数据优先淘汰

## 4. 前端界面设计

### 4.1 Streamlit组件架构

#### 页面布局
```python
def main_layout():
    """主页面布局"""
    # 页面配置
    st.set_page_config(
        page_title="MediaCrawler 监控平台",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 自定义CSS
    st.markdown(load_custom_css(), unsafe_allow_html=True)
    
    # 主要区域
    render_header()
    render_sidebar()
    render_main_content()
```

#### 组件化设计
```python
# components/filters.py
def render_platform_filter() -> List[str]:
    """渲染平台筛选组件"""
    pass

def render_time_filter() -> Tuple[datetime, datetime]:
    """渲染时间筛选组件"""
    pass

def render_search_box() -> str:
    """渲染搜索框组件"""
    pass
```

### 4.2 交互设计

#### 状态管理
```python
# 使用Streamlit Session State管理应用状态
def init_session_state():
    """初始化会话状态"""
    if 'search_filters' not in st.session_state:
        st.session_state.search_filters = SearchFilters()
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
```

#### 事件处理
- **筛选变更**: 自动触发数据重新查询
- **分页操作**: 更新当前页码和数据
- **搜索提交**: 实时搜索或按钮触发
- **排序切换**: 重新排序数据显示

### 4.3 样式定制

#### CSS样式策略
```css
/* static/styles.css */
:root {
    --primary-color: #1f77b4;
    --secondary-color: #ff7f0e;
    --background-color: #fafafa;
    --text-color: #262730;
    --border-color: #e0e0e0;
}

.main-header {
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
    padding: 1rem;
    margin-bottom: 2rem;
}

.filter-container {
    background: white;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
```

## 5. 性能优化方案

### 5.1 查询性能优化

#### 数据库优化
```python
# 查询优化示例
def optimized_search(filters: SearchFilters):
    """优化的搜索查询"""
    query = session.query(Model)
    
    # 1. 使用索引友好的查询条件
    if filters.start_time:
        query = query.filter(Model.publish_time >= filters.start_time)
    
    # 2. 分页查询优化
    offset = (filters.page - 1) * filters.page_size
    query = query.offset(offset).limit(filters.page_size)
    
    # 3. 只查询必要字段
    query = query.options(load_only('id', 'title', 'publish_time'))
    
    return query.all()
```

#### 缓存机制
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_platform_stats():
    """缓存平台统计数据"""
    return calculate_platform_stats()
```

### 5.2 前端性能优化

#### 懒加载策略
- **数据分页**: 避免一次性加载大量数据
- **图片延迟**: 内容图片按需加载
- **组件缓存**: Streamlit组件缓存机制

#### 响应优化
- **异步加载**: 非关键数据异步获取
- **加载状态**: 显示加载进度和状态
- **错误处理**: 友好的错误提示和重试机制

## 6. 安全设计

### 6.1 数据安全

#### SQL注入防护
```python
# 使用SQLAlchemy ORM自动防护SQL注入
def safe_search(keyword: str):
    """安全的搜索查询"""
    return session.query(Model).filter(
        Model.title.contains(keyword)  # 自动参数化查询
    )
```

#### 数据访问控制
- **只读权限**: Web界面只提供数据查询
- **字段过滤**: 敏感字段不返回前端
- **访问日志**: 记录数据访问日志

### 6.2 应用安全

#### 访问控制
```python
# 基础的访问控制
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

def check_access():
    """检查访问权限"""
    client_ip = get_client_ip()
    if client_ip not in ALLOWED_HOSTS:
        st.error("Access denied")
        st.stop()
```

## 7. 部署方案

### 7.1 本地部署

#### 环境要求
```bash
# Python环境
Python >= 3.8
pip >= 21.0

# 依赖包
streamlit >= 1.28.0
sqlalchemy >= 2.0.0
pymysql >= 1.0.0
pandas >= 1.5.0
plotly >= 5.0.0
```

#### 启动命令
```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
streamlit run web/app.py --server.port 8501 --server.address localhost
```

### 7.2 生产部署

#### Docker部署 (可选)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "web/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

#### 进程管理
- **Supervisor**: 进程守护和自动重启
- **Nginx**: 反向代理和负载均衡 (可选)
- **日志管理**: 结构化日志和轮转

## 8. 监控和维护

### 8.1 应用监控

#### 性能指标
- **响应时间**: 页面加载和查询响应时间
- **错误率**: 应用错误和数据库错误率
- **并发数**: 同时在线用户数
- **资源使用**: CPU、内存、数据库连接数

#### 日志管理
```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('web_app.log'),
        logging.StreamHandler()
    ]
)
```

### 8.2 数据库监控

#### 查询性能
- **慢查询**: 监控执行时间超过2秒的查询
- **索引使用**: 确保查询使用合适的索引
- **连接池**: 监控连接池使用情况

## 9. 扩展规划

### 9.1 功能扩展

#### 短期扩展 (1-2个月)
- **数据导出**: Excel、PDF报告生成
- **图表可视化**: 趋势图、饼图、柱状图
- **实时更新**: WebSocket实时数据推送

#### 中期扩展 (3-6个月)
- **用户系统**: 多用户访问和权限管理
- **API接口**: RESTful API提供数据服务
- **移动端**: 响应式设计优化

#### 长期扩展 (6个月以上)
- **智能分析**: 更多AI分析维度
- **告警系统**: 关键词监控和实时告警
- **数据可视化**: 复杂的数据大屏和仪表板

### 9.2 技术扩展

#### 架构升级
- **微服务**: 拆分为独立的服务模块
- **消息队列**: 异步任务处理
- **分布式**: 支持分布式部署

## 10. 风险评估和应对

### 10.1 技术风险

#### 性能风险
- **风险**: 大数据量查询导致响应慢
- **应对**: 查询优化、分页、缓存

#### 稳定性风险
- **风险**: 数据库连接异常
- **应对**: 连接池、重试机制、监控告警

### 10.2 业务风险

#### 数据一致性
- **风险**: 爬虫数据更新与Web展示不同步
- **应对**: 定期数据同步检查

#### 用户体验
- **风险**: 界面复杂度影响使用
- **应对**: 用户反馈收集、界面持续优化

这个技术方案确保了MediaCrawler Web监控平台的技术可行性、性能可靠性和未来扩展性，为项目的成功实施提供了坚实的技术基础。