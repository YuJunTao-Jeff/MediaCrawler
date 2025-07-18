# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


from enum import Enum


class SearchSortType(Enum):
    """搜索结果排序类型"""
    TIME_DESC = "time_descending"        # 按时间降序
    REPLY_NUM = "reply_num"              # 按回复数排序  
    RELEVANCE = "relevance"              # 按相关性排序


class SearchNoteType(Enum):
    """搜索内容类型"""
    ALL = 0                              # 全部
    FIXED_THREAD = 1                     # 固定主题帖
    THREAD = 2                           # 主题帖


class InterceptType(Enum):
    """网络拦截类型"""
    SEARCH_POSTS = "search_posts"        # 搜索帖子
    POST_DETAIL = "post_detail"          # 帖子详情
    POST_COMMENTS = "post_comments"      # 帖子评论
    USER_PROFILE = "user_profile"        # 用户信息


class BehaviorType(Enum):
    """用户行为类型"""
    SCROLL = "scroll"                    # 滚动
    CLICK = "click"                      # 点击
    HOVER = "hover"                      # 悬停
    INPUT = "input"                      # 输入
    WAIT = "wait"                        # 等待


class AntiDetectionLevel(Enum):
    """反检测级别"""
    LOW = "low"                          # 低级
    MEDIUM = "medium"                    # 中级
    HIGH = "high"                        # 高级
    EXTREME = "extreme"                  # 极限