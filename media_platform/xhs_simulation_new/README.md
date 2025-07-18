# 小红书模拟爬虫 (XHS Simulation New)

基于浏览器自动化+网络拦截技术的小红书爬虫，符合MediaCrawler项目代码风格。

## 🎯 核心特性

### 技术架构
- **浏览器自动化**: 使用Playwright控制真实浏览器
- **网络拦截**: 拦截API响应获取原始数据
- **用户行为模拟**: 模拟真实用户操作轨迹
- **反检测技术**: 隐藏自动化特征
- **断点续爬**: 集成现有续爬系统

### 模块组织
```
xhs_simulation_new/
├── core.py           # 主爬虫类 (继承AbstractCrawler)
├── client.py         # API客户端 (继承AbstractApiClient)
├── login.py          # 登录逻辑
├── exception.py      # 自定义异常
├── field.py          # 枚举和字段定义
└── help.py           # 辅助函数 (网络拦截、行为模拟、反检测)
```

## 🚀 使用方法

### 基础搜索
```bash
python main.py --platform xhs_simulation_new --type search --keywords "澳鹏科技" --lt qrcode
```

### 获取指定笔记
```bash
python main.py --platform xhs_simulation_new --type detail --lt cookie
```

### 获取创作者信息
```bash
python main.py --platform xhs_simulation_new --type creator --lt phone
```

## ⚙️ 配置参数

### 基础配置
```python
# 是否启用小红书模拟爬虫
XHS_SIMULATION_ENABLED = True

# 是否启用用户行为模拟
XHS_SIMULATION_USER_BEHAVIOR = True

# 是否启用反检测功能
XHS_SIMULATION_ANTI_DETECTION = True
```

### 高级配置
```python
# 反检测级别 (low, medium, high, extreme)
XHS_SIMULATION_ANTI_DETECTION_LEVEL = "medium"

# 用户行为延迟范围（秒）
XHS_SIMULATION_BEHAVIOR_DELAY = (1.0, 3.0)

# 滚动次数范围
XHS_SIMULATION_SCROLL_COUNT = (2, 5)
```

### 登录配置
```python
# 小红书登录手机号（手机号登录时使用）
XHS_LOGIN_PHONE = "13800138000"

# 小红书Cookie字符串（Cookie登录时使用）
XHS_COOKIE_STR = "a1=xxx; webId=xxx; ..."
```

## 🛡️ 反检测机制

### 浏览器指纹伪装
- 隐藏WebDriver特征
- 随机化视窗大小
- 伪造Canvas指纹
- 修改Navigator属性

### 用户行为模拟
- 随机鼠标移动轨迹
- 模拟人类滚动模式
- 真实阅读停顿时间
- 自然的点击延迟

### 网络层面
- 真实浏览器请求头
- 自然的请求频率
- 智能延迟控制

## 📊 数据获取流程

1. **启动浏览器**: 设置反检测和代理
2. **用户登录**: 支持二维码、手机号、Cookie登录
3. **设置拦截**: 监听目标API响应
4. **模拟操作**: 执行搜索、滚动、点击等操作
5. **数据提取**: 从拦截的响应中解析数据
6. **存储数据**: 使用统一的存储接口

## 🔧 开发说明

### 扩展新功能
1. 在`field.py`中定义新的枚举类型
2. 在`help.py`中添加辅助函数
3. 在`client.py`中实现新的API方法
4. 在`core.py`中集成新功能

### 调试技巧
```python
# 启用详细日志
import logging
logging.getLogger().setLevel(logging.DEBUG)

# 显示浏览器界面（非无头模式）
HEADLESS = False

# 降低反检测级别进行测试
XHS_SIMULATION_ANTI_DETECTION_LEVEL = "low"
```

## 📝 注意事项

### 合规使用
- 仅供学习和研究目的
- 遵守平台服务条款
- 控制请求频率
- 不得用于商业用途

### 性能优化
- 合理配置并发数
- 使用代理池分散请求
- 启用断点续爬
- 监控资源使用

### 错误处理
- 网络异常自动重试
- 反检测失败降级
- 登录状态监控
- 数据完整性检查

## 🚨 故障排除

### 常见问题
1. **登录失败**: 检查Cookie有效性或网络连接
2. **拦截失败**: 确认API URL匹配模式
3. **反检测被识别**: 提高反检测级别
4. **数据解析错误**: 检查API响应格式变化

### 调试方法
```bash
# 启用调试模式
python main.py --platform xhs_simulation_new --type search --keywords "test" --headless false

# 查看网络请求
# 在浏览器开发者工具中监控Network面板
```