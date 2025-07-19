# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# 基础配置
PLATFORM = "xhs"
KEYWORDS = "appen,澳鹏,田小鹏,爱普恩,澳鹏大连,澳鹏无锡,澳鹏科技,澳鹏中国,澳鹏数据,澳鹏重庆"  # 关键词搜索配置，以英文逗号分隔
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookie
COOKIES = ""
# 具体值参见media_platform.xxx.field下的枚举值，暂时只支持小红书
SORT_TYPE = "popularity_descending"
# 具体值参见media_platform.xxx.field下的枚举值，暂时只支持抖音
PUBLISH_TIME_TYPE = 0
CRAWLER_TYPE = (
    "search"  # 爬取类型，search(关键词搜索) | detail(帖子详情)| creator(创作者主页数据)
)
# 微博搜索类型 default (综合) | real_time (实时) | popular (热门) | video (视频)
WEIBO_SEARCH_TYPE = "default"
# 自定义User Agent（暂时仅对XHS有效）
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 未启用代理时的最大爬取间隔，单位秒（暂时仅对XHS有效）
CRAWLER_MAX_SLEEP_SEC = 6

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = "kuaidaili"

# ==================== 快代理配置 ====================
# 快代理用户名
KDL_USER_NAME = "d2867368032"

# 快代理密码
KDL_USER_PWD = "0h39smdt"

# 快代理 Secret ID
KDL_SECRET_ID = "olj9unpyex5nffwhecl6"

# 快代理签名
KDL_SIGNATURE = "n1zziu4o3uqz7w23ct8fveqnwy9x07vr"

# 设置为True不会打开浏览器（无头浏览器）
# 设置False会打开一个浏览器
# 小红书如果一直扫码登录不通过，打开浏览器手动过一下滑动验证码
# 抖音如果一直提示失败，打开浏览器看下是否扫码登录之后出现了手机号验证，如果出现了手动过一下再试。
HEADLESS = False

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# ==================== CDP (Chrome DevTools Protocol) 配置 ====================
# 是否启用CDP模式 - 使用用户现有的Chrome/Edge浏览器进行爬取，提供更好的反检测能力
# 启用后将自动检测并启动用户的Chrome/Edge浏览器，通过CDP协议进行控制
# 这种方式使用真实的浏览器环境，包括用户的扩展、Cookie和设置，大大降低被检测的风险
ENABLE_CDP_MODE = True

# CDP调试端口，用于与浏览器通信
# 如果端口被占用，系统会自动尝试下一个可用端口
CDP_DEBUG_PORT = 9222

# 是否连接到已存在的浏览器实例（而不是启动新的）
# 设置为True时，将尝试连接到端口上已运行的浏览器
CONNECT_EXISTING_BROWSER = True

# 自定义浏览器路径（可选）
# 如果为空，系统会自动检测Chrome/Edge的安装路径
# Windows示例: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# macOS示例: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CUSTOM_BROWSER_PATH = "/home/jeff/.cache/ms-playwright/chromium-1124/chrome-linux/chrome"

# CDP模式下是否启用无头模式
# 注意：即使设置为True，某些反检测功能在无头模式下可能效果不佳
CDP_HEADLESS = False

# 浏览器启动超时时间（秒）
BROWSER_LAUNCH_TIMEOUT = 30

# 是否在程序结束时自动关闭浏览器
# 设置为False可以保持浏览器运行，便于调试
AUTO_CLOSE_BROWSER = True

# 数据保存类型选项配置,支持三种类型：csv、db、json, 最好保存到DB，有排重的功能。
SAVE_DATA_OPTION = "db"  # csv or db or json

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 爬取开始页数 默认从第一页开始
START_PAGE = 1

# 爬取页面数量限制 默认爬取100页
PAGE_LIMIT = 100

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 200

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 1

# 是否开启爬图片模式, 默认不开启爬图片
ENABLE_GET_IMAGES = False

# 是否开启爬评论模式, 默认开启爬评论
ENABLE_GET_COMMENTS = True

# 爬取一级评论的数量控制(单视频/帖子)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 20

# 是否开启爬二级评论模式, 默认不开启爬二级评论
# 老版本项目使用了 db, 则需参考 schema/tables.sql line 287 增加表字段
ENABLE_GET_SUB_COMMENTS = False

# 已废弃⚠️⚠️⚠️指定小红书需要爬虫的笔记ID列表
# 已废弃⚠️⚠️⚠️ 指定笔记ID笔记列表会因为缺少xsec_token和xsec_source参数导致爬取失败
# XHS_SPECIFIED_ID_LIST = [
#     "66fad51c000000001b0224b8",
#     # ........................
# ]

# 指定小红书需要爬虫的笔记URL列表, 目前要携带xsec_token和xsec_source参数
XHS_SPECIFIED_NOTE_URL_LIST = [
    "https://www.xiaohongshu.com/explore/66fad51c000000001b0224b8?xsec_token=AB3rO-QopW5sgrJ41GwN01WCXh6yWPxjSoFI9D5JIMgKw=&xsec_source=pc_search"
    # ........................
]

# 指定抖音需要爬取的ID列表
DY_SPECIFIED_ID_LIST = [
    "7280854932641664319",
    "7202432992642387233",
    # ........................
]

# 指定快手平台需要爬取的ID列表
KS_SPECIFIED_ID_LIST = ["3xf8enb8dbj6uig", "3x6zz972bchmvqe"]

# 指定B站平台需要爬取的视频bvid列表
BILI_SPECIFIED_ID_LIST = [
    "BV1d54y1g7db",
    "BV1Sz4y1U77N",
    "BV14Q4y1n7jz",
    # ........................
]

# 指定微博平台需要爬取的帖子列表
WEIBO_SPECIFIED_ID_LIST = [
    "4982041758140155",
    # ........................
]

# 指定weibo创作者ID列表
WEIBO_CREATOR_ID_LIST = [
    "5533390220",
    # ........................
]

# 指定贴吧需要爬取的帖子列表
TIEBA_SPECIFIED_ID_LIST = []

# 指定贴吧名称列表，爬取该贴吧下的帖子
TIEBA_NAME_LIST = [
    # "盗墓笔记"
]

# 指定贴吧创作者URL列表
TIEBA_CREATOR_URL_LIST = [
    "https://tieba.baidu.com/home/main/?id=tb.1.7f139e2e.6CyEwxu3VJruH_-QqpCi6g&fr=frs",
    # ........................
]

# 指定小红书创作者ID列表
XHS_CREATOR_ID_LIST = [
    "63e36c9a000000002703502b",
    # ........................
]

# 指定Dy创作者ID列表(sec_id)
DY_CREATOR_ID_LIST = [
    "MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE",
    # ........................
]

# 指定bili创作者ID列表(sec_id)
BILI_CREATOR_ID_LIST = [
    "20813884",
    # ........................
]

# 指定快手创作者ID列表
KS_CREATOR_ID_LIST = [
    "3x4sm73aye7jq7i",
    # ........................
]


# 指定知乎创作者主页url列表
ZHIHU_CREATOR_URL_LIST = [
    "https://www.zhihu.com/people/yd1234567",
    # ........................
]

# 指定知乎需要爬取的帖子ID列表
ZHIHU_SPECIFIED_ID_LIST = [
    "https://www.zhihu.com/question/826896610/answer/4885821440",  # 回答
    "https://zhuanlan.zhihu.com/p/673461588",  # 文章
    "https://www.zhihu.com/zvideo/1539542068422144000",  # 视频
]

# ==================== 小红书模拟爬虫配置 ====================
# 是否启用小红书模拟爬虫（浏览器自动化+网络拦截）
XHS_SIMULATION_ENABLED = False

# 小红书模拟爬虫是否启用无头模式
XHS_SIMULATION_HEADLESS = False

# 小红书模拟爬虫并发数量
XHS_SIMULATION_CONCURRENCY = 1

# 是否启用用户行为模拟
XHS_SIMULATION_USER_BEHAVIOR = True

# 是否启用反检测策略
XHS_SIMULATION_ANTI_DETECTION = True

# 滚动次数配置
XHS_SIMULATION_SCROLL_COUNT = 5

# 页面加载超时时间（秒）
XHS_SIMULATION_PAGE_LOAD_TIMEOUT = 30

# 操作延迟范围（秒）
XHS_SIMULATION_OPERATION_DELAY_RANGE = (1, 3)

# 最大重试次数
XHS_SIMULATION_MAX_RETRY_COUNT = 3

# 检测检查间隔（秒）
XHS_SIMULATION_DETECTION_CHECK_INTERVAL = 10

# 基础延迟时间（秒）
XHS_SIMULATION_BASE_DELAY = 2.0

# 网络拦截的目标API模式
XHS_SIMULATION_NETWORK_PATTERNS = [
    "*/api/sns/web/v1/search/notes*",
    "*/api/sns/web/v1/note/detail*",
    "*/api/sns/web/v1/feed*",
    "*/api/sns/web/v1/user/notes*",
    "*/api/sns/web/v1/comment/list*"
]

# 用户行为模拟配置
XHS_SIMULATION_SCROLL_BEHAVIOR_RANDOM = True
XHS_SIMULATION_TYPING_BEHAVIOR_RANDOM = True
XHS_SIMULATION_MOUSE_BEHAVIOR_RANDOM = True

# 反检测配置
XHS_SIMULATION_FINGERPRINT_RANDOMIZATION = True
XHS_SIMULATION_REQUEST_HEADER_RANDOMIZATION = True
XHS_SIMULATION_VIEWPORT_RANDOMIZATION = True

# 词云相关
# 是否开启生成评论词云图
ENABLE_GET_WORDCLOUD = False
# 自定义词语及其分组
# 添加规则：xx:yy 其中xx为自定义添加的词组，yy为将xx该词组分到的组名。
CUSTOM_WORDS = {
    "零几": "年份",  # 将“零几”识别为一个整体
    "高频词": "专业术语",  # 示例自定义词
}

# 停用(禁用)词文件路径
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# 中文字体文件路径
FONT_PATH = "./docs/STZHONGS.TTF"

# 爬取开始的天数，仅支持 bilibili 关键字搜索，YYYY-MM-DD 格式，若为 None 则表示不设置时间范围，按照默认关键字最多返回 1000 条视频的结果处理
START_DAY = "2024-01-01"

# 爬取结束的天数，仅支持 bilibili 关键字搜索，YYYY-MM-DD 格式，若为 None 则表示不设置时间范围，按照默认关键字最多返回 1000 条视频的结果处理
END_DAY = "2024-01-01"

# 是否开启按每一天进行爬取的选项，仅支持 bilibili 关键字搜索
# 若为 False，则忽略 START_DAY 与 END_DAY 设置的值
# 若为 True，则按照 START_DAY 至 END_DAY 按照每一天进行筛选，这样能够突破 1000 条视频的限制，最大程度爬取该关键词下的所有视频
ALL_DAY = False

#!!! 下面仅支持 bilibili creator搜索
# 爬取评论creator主页还是爬取creator动态和关系列表(True为前者)
CREATOR_MODE = True

# 爬取creator粉丝列表时起始爬取页数
START_CONTACTS_PAGE = 1

# 爬取作者粉丝和关注列表数量控制(单作者)
CRAWLER_MAX_CONTACTS_COUNT_SINGLENOTES = 100

# 爬取作者动态数量控制(单作者)
CRAWLER_MAX_DYNAMICS_COUNT_SINGLENOTES = 50

# ==================== 断点续爬配置 ====================
# 是否启用断点续爬功能
ENABLE_RESUME_CRAWL = True

# 断点续爬任务ID（如果不指定，系统会自动生成）
RESUME_TASK_ID = None

# 爬取进度保存间隔（处理多少条数据后保存一次进度）
PROGRESS_SAVE_INTERVAL = 10

# 智能去重时间窗口（秒）- 判断内容是否重复的时间窗口
SMART_DEDUP_TIME_WINDOW = 86400  # 24小时

# 是否启用智能搜索优化（根据爬取进度调整搜索策略）
ENABLE_SMART_SEARCH = True

# 连续空页面阈值（连续遇到多少个空页面后停止该关键词）
EMPTY_PAGE_THRESHOLD = 3

# 重试失败任务的最大次数
MAX_RETRY_COUNT = 3

# 任务超时时间（秒）
TASK_TIMEOUT = 3600  # 1小时

# 是否在启动时清理历史任务
CLEANUP_HISTORY_TASKS = False

# ==================== 小红书模拟爬虫配置 ====================
# 是否启用小红书模拟爬虫
XHS_SIMULATION_ENABLED = True

# 是否启用用户行为模拟
XHS_SIMULATION_USER_BEHAVIOR = True

# 是否启用反检测功能
XHS_SIMULATION_ANTI_DETECTION = True

# 反检测级别 (low, medium, high, extreme)
XHS_SIMULATION_ANTI_DETECTION_LEVEL = "medium"

# 用户行为延迟范围（秒）
XHS_SIMULATION_BEHAVIOR_DELAY = (1.0, 3.0)

# 滚动次数范围
XHS_SIMULATION_SCROLL_COUNT = (2, 5)

# 小红书登录手机号（手机号登录时使用）
XHS_LOGIN_PHONE = ""

# 小红书Cookie字符串（Cookie登录时使用）
XHS_COOKIE_STR = ""

# ==================== 贴吧模拟爬虫配置 ====================
# 是否启用贴吧模拟爬虫
TIEBA_SIMULATION_ENABLED = True

# 是否启用用户行为模拟
TIEBA_SIMULATION_USER_BEHAVIOR = True

# 是否启用反检测功能
TIEBA_SIMULATION_ANTI_DETECTION = True

# 反检测级别 (low, medium, high, extreme)
TIEBA_SIMULATION_ANTI_DETECTION_LEVEL = "medium"

# 用户行为延迟范围（秒）
TIEBA_SIMULATION_BEHAVIOR_DELAY = (1.0, 3.0)

# 滚动次数范围
TIEBA_SIMULATION_SCROLL_COUNT = (2, 5)

# 贴吧登录手机号（手机号登录时使用）
TIEBA_LOGIN_PHONE = ""

# 贴吧Cookie字符串（Cookie登录时使用）
TIEBA_COOKIE_STR = ""

# ==================== 新闻平台配置 ====================
# Tavily搜索引擎API密钥
TAVILY_API_KEY = "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"

# 天工搜索引擎API密钥
TIANGONG_API_KEY = ""

# 新闻搜索每个关键词的最大结果数
NEWS_MAX_RESULTS_PER_KEYWORD = 100

# 新闻内容提取的最大并发数
NEWS_MAX_CONCURRENT_EXTRACTIONS = 5

# 新闻文章内容最小长度（字符数）
NEWS_MIN_CONTENT_LENGTH = 100

# 新闻文章标题最大长度（字符数）
NEWS_MAX_TITLE_LENGTH = 2000

# 是否启用新闻发布时间提取
NEWS_ENABLE_PUBLISH_TIME = True

# 是否启用新闻关键词提取
NEWS_ENABLE_KEYWORD_EXTRACTION = True

# 是否启用新闻摘要生成
NEWS_ENABLE_SUMMARY_GENERATION = True

# 新闻提取超时时间（秒）
NEWS_EXTRACTION_TIMEOUT = 30

# 新闻平台默认语言
NEWS_DEFAULT_LANGUAGE = "zh"

# 指定新闻平台需要爬取的URL列表
NEWS_SPECIFIED_URL_LIST = [
    # "https://example.com/news/article1",
    # "https://example.com/news/article2",
    # ........................
]
