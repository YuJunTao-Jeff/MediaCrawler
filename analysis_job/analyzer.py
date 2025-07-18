"""
AI分析器模块
"""

import json
import time
import logging
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from .config import ANALYSIS_CONFIG, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from .models import ContentItem, AnalysisResult, BatchAnalysisRequest
from .cost_calculator import CostCalculator, TokenUsage, format_cost_summary


logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI分析器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or ANALYSIS_CONFIG
        self.llm = ChatOpenAI(
            model=self.config["model"],
            temperature=self.config["temperature"],
            max_tokens=self.config["max_tokens"],
            timeout=self.config["timeout"],
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        self.cost_calculator = CostCalculator(self.config["model"])
        logger.info(f"AI分析器初始化完成，模型: {self.config['model']}")
    
    def _build_analysis_prompt(self, content_items: List[ContentItem], source_keywords: str = "") -> List[Any]:
        """构建分析提示词"""
        system_prompt = f"""你是一个专业的社交媒体内容分析师，需要对提供的内容进行全面分析。

分析要求：
1. 情感分析：判断内容的情感倾向（positive/negative/neutral）
2. 情感评分：给出-1到1之间的情感评分（-1表示极负面，0表示中性，1表示极正面）
   - 极负面内容：-1到-0.7（如投诉、愤怒、严重不满）
   - 负面内容：-0.6到-0.1（如轻微不满、质疑）
   - 中性内容：-0.1到0.1（如中性描述、客观陈述）
   - 正面内容：0.1到0.6（如满意、认可）
   - 极正面内容：0.7到1（如强烈推荐、赞美）
3. 内容总结：用1-2句话总结内容核心要点
4. 关键词提取：提取3-5个最重要的关键词
5. 内容分类：对内容进行分类（如：产品评价、服务体验、价格讨论、使用教程、问题反馈等）
6. 相关性评分：评估内容与源关键词的相关性（0-1之间，源关键词为：{source_keywords}）
7. 重点评论：如果有评论，识别最重要的评论ID（最多3个）

请严格按照以下JSON格式返回结果，不要包含任何其他文字："""
        
        # 准备内容数据
        content_data = []
        for item in content_items:
            # 分别处理主要内容和评论
            main_content = item.get_full_content()
            comments_data = []
            for comment in item.comments[:20]:  # 最多20个评论
                if isinstance(comment, dict) and 'comment_id' in comment:
                    comments_data.append({
                        "comment_id": comment['comment_id'],
                        "content": comment.get('content', '')[:200]  # 限制评论长度
                    })
            
            item_data = {
                "content_id": item.content_id,
                "platform": item.platform,
                "main_content": main_content[:2000],  # 限制主要内容长度
                "comments": comments_data,
                "comment_count": len(item.comments)
            }
            content_data.append(item_data)
        
        user_prompt = f"""
请分析以下{len(content_items)}条社交媒体内容：

{json.dumps(content_data, ensure_ascii=False, indent=2)}

数据结构说明：
- main_content: 主要内容（标题+正文）
- comments: 评论列表，每个评论包含comment_id和content
- 在分析时，请结合主要内容和评论进行综合评估
- key_comment_ids字段请填写最重要的评论的comment_id（从comments中选择）

输出格式：
[
  {{
    "content_id": "内容ID",
    "sentiment": "positive/negative/neutral",
    "sentiment_score": 0.85,
    "summary": "内容核心要点总结，如果评论比较重要，把评论也附上简要总结",
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "category": "内容分类",
    "relevance_score": 0.92,
    "key_comment_ids": ["评论ID1", "评论ID2"]
  }}
]

注意：
- sentiment_score必须是-1到1之间的浮点数（-1=极负面，-0.5=负面，0=中性，0.5=正面，1=极正面）
- relevance_score必须是0到1之间的浮点数（0=完全不相关，1=完全相关）

请确保返回有效的JSON格式，每个内容都要有对应的分析结果。"""
        
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
    
    def _parse_analysis_response(self, response: str, content_items: List[ContentItem]) -> List[AnalysisResult]:
        """解析分析响应"""
        try:
            # 尝试解析JSON
            response_data = json.loads(response)
            
            if not isinstance(response_data, list):
                raise ValueError("响应不是列表格式")
            
            results = []
            current_timestamp = int(time.time() * 1000)
            
            for i, item_data in enumerate(response_data):
                if i >= len(content_items):
                    break
                
                content_item = content_items[i]
                
                # 验证和清理数据
                sentiment_score = float(item_data.get("sentiment_score", 0.0))
                # 确保情感评分在-1到1之间
                if sentiment_score < -1:
                    sentiment_score = -1
                elif sentiment_score > 1:
                    sentiment_score = 1
                
                result = AnalysisResult(
                    content_id=item_data.get("content_id", content_item.content_id),
                    sentiment=item_data.get("sentiment", "neutral"),
                    sentiment_score=sentiment_score,
                    summary=item_data.get("summary", "")[:500],  # 限制长度
                    keywords=item_data.get("keywords", []),  
                    category=item_data.get("category", "其他"),
                    relevance_score=float(item_data.get("relevance_score", 0.5)),
                    key_comment_ids=item_data.get("key_comment_ids", []), 
                    analysis_timestamp=current_timestamp,
                    model_version=self.config["model"],
                    content_length=content_item.get_content_length(),
                    comment_count=len(content_item.comments),
                    source_keyword=getattr(self, '_current_source_keywords', "")
                )
                
                # 添加结果
                results.append(result)
            
            # 如果解析的结果少于输入项，为剩余项创建默认结果
            while len(results) < len(content_items):
                results.append(self._create_default_result(content_items[len(results)]))
            
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"原始响应: {response[:500]}...")
            # 返回默认结果
            return [self._create_default_result(item) for item in content_items]
        except Exception as e:
            logger.error(f"响应解析失败: {e}")
            return [self._create_default_result(item) for item in content_items]
    
    def _create_default_result(self, content_item: ContentItem) -> AnalysisResult:
        """创建默认分析结果"""
        return AnalysisResult(
            content_id=content_item.content_id,
            sentiment="neutral",
            sentiment_score=0.0,  # 默认中性评分
            summary="分析失败，无法生成总结",
            keywords=[],
            category="其他",
            relevance_score=0.0,  # 默认无相关性
            key_comment_ids=[],
            analysis_timestamp=int(time.time() * 1000),
            model_version=self.config["model"],
            content_length=content_item.get_content_length(),
            comment_count=len(content_item.comments),
            source_keyword=""  # 默认无源关键词
        )
    
    def analyze_batch(self, content_items: List[ContentItem], source_keywords: str = "", retry_count: int = 0) -> List[AnalysisResult]:
        """批量分析内容"""
        if not content_items:
            return []
        
        max_retries = self.config.get("max_retries", 3)
        retry_delay = self.config.get("retry_delay", 1.0)
        
        try:
            logger.info(f"开始分析批次: {len(content_items)} 条内容")
            
            # 存储当前源关键词，用于解析响应时使用
            self._current_source_keywords = source_keywords
            
            # 构建消息
            messages = self._build_analysis_prompt(content_items, source_keywords)
            
            # 调用模型
            response = self.llm.invoke(messages)
            
            # 提取token使用情况
            token_usage = self.cost_calculator.extract_token_usage_from_response(response)
            if token_usage:
                cost_info = self.cost_calculator.add_usage(token_usage)
                logger.info(f"API调用成本: {format_cost_summary(cost_info, token_usage)}")
            else:
                logger.warning("无法提取token使用信息")
            
            # 解析响应
            results = self._parse_analysis_response(response.content, content_items)
            
            logger.info(f"批次分析完成: {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"批次分析失败 (重试 {retry_count + 1}/{max_retries}): {e}")
            
            if retry_count < max_retries:
                # 等待后重试
                time.sleep(retry_delay * (2 ** retry_count))  # 指数退避
                return self.analyze_batch(content_items, source_keywords, retry_count + 1)
            else:
                # 达到最大重试次数，返回默认结果
                logger.error(f"达到最大重试次数，返回默认结果")
                return [self._create_default_result(item) for item in content_items]
    
    def analyze_single(self, content_item: ContentItem) -> AnalysisResult:
        """分析单个内容"""
        results = self.analyze_batch([content_item])
        return results[0] if results else self._create_default_result(content_item)
    
    def analyze_batch_request(self, request: BatchAnalysisRequest) -> List[AnalysisResult]:
        """分析批次请求"""
        return self.analyze_batch(request.content_items)
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """获取成本统计摘要"""
        return self.cost_calculator.get_session_summary()
    
    def log_cost_summary(self):
        """记录成本统计摘要"""
        self.cost_calculator.log_session_summary()
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            test_item = ContentItem(
                platform="test",
                content_id="test_001",
                title="测试标题",
                content="这是一个测试内容，用于验证AI分析器是否正常工作。"
            )
            
            result = self.analyze_single(test_item)
            
            if result and result.content_id == "test_001":
                logger.info("AI分析器连接测试成功")
                return True
            else:
                logger.error("AI分析器连接测试失败")
                return False
                
        except Exception as e:
            logger.error(f"AI分析器连接测试异常: {e}")
            return False