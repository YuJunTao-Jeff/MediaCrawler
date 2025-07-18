"""
Token消耗和成本计算工具
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class TokenUsage:
    """Token使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens
    
    def add(self, other: 'TokenUsage') -> 'TokenUsage':
        """合并Token使用统计"""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens
        }

@dataclass
class CostInfo:
    """成本信息"""
    prompt_cost: float = 0.0
    completion_cost: float = 0.0
    total_cost: float = 0.0
    
    def __post_init__(self):
        if self.total_cost == 0:
            self.total_cost = self.prompt_cost + self.completion_cost
    
    def add(self, other: 'CostInfo') -> 'CostInfo':
        """合并成本信息"""
        return CostInfo(
            prompt_cost=self.prompt_cost + other.prompt_cost,
            completion_cost=self.completion_cost + other.completion_cost,
            total_cost=self.total_cost + other.total_cost
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'prompt_cost': round(self.prompt_cost, 6),
            'completion_cost': round(self.completion_cost, 6),
            'total_cost': round(self.total_cost, 6)
        }

class CostCalculator:
    """成本计算器"""
    
    # OpenAI模型价格表（每1000个token的价格，美元）
    MODEL_PRICING = {
        'gpt-4o-mini': {
            'input': 0.000150,   # $0.15 per 1M tokens
            'output': 0.000600,  # $0.60 per 1M tokens
        },
        'gpt-4o': {
            'input': 0.0025,     # $2.50 per 1M tokens
            'output': 0.0100,    # $10.00 per 1M tokens
        },
        'gpt-4': {
            'input': 0.0300,     # $30.00 per 1M tokens
            'output': 0.0600,    # $60.00 per 1M tokens
        },
        'gpt-3.5-turbo': {
            'input': 0.0010,     # $1.00 per 1M tokens
            'output': 0.0020,    # $2.00 per 1M tokens
        }
    }
    
    def __init__(self, model_name: str = 'gpt-4o-mini'):
        self.model_name = model_name
        self.pricing = self.MODEL_PRICING.get(model_name, self.MODEL_PRICING['gpt-4o-mini'])
        self.session_usage = TokenUsage()
        self.session_cost = CostInfo()
        self.start_time = time.time()
        
        logger.info(f"成本计算器初始化完成，模型: {model_name}")
    
    def calculate_cost(self, token_usage: TokenUsage) -> CostInfo:
        """计算成本"""
        # 计算成本（价格是每1000个token）
        prompt_cost = (token_usage.prompt_tokens / 1000) * self.pricing['input']
        completion_cost = (token_usage.completion_tokens / 1000) * self.pricing['output']
        total_cost = prompt_cost + completion_cost
        
        return CostInfo(
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=total_cost
        )
    
    def add_usage(self, token_usage: TokenUsage) -> CostInfo:
        """添加使用记录并计算成本"""
        # 计算这次的成本
        cost_info = self.calculate_cost(token_usage)
        
        # 累加到会话统计
        self.session_usage = self.session_usage.add(token_usage)
        self.session_cost = self.session_cost.add(cost_info)
        
        # 记录日志
        logger.info(
            f"Token使用: prompt={token_usage.prompt_tokens}, "
            f"completion={token_usage.completion_tokens}, "
            f"total={token_usage.total_tokens}"
        )
        logger.info(
            f"本次成本: ${cost_info.total_cost:.6f} "
            f"(prompt: ${cost_info.prompt_cost:.6f}, "
            f"completion: ${cost_info.completion_cost:.6f})"
        )
        
        return cost_info
    
    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话总结"""
        duration = time.time() - self.start_time
        
        summary = {
            'model': self.model_name,
            'duration_seconds': round(duration, 2),
            'token_usage': self.session_usage.to_dict(),
            'cost_info': self.session_cost.to_dict()
        }
        
        return summary
    
    def log_session_summary(self):
        """记录会话总结日志"""
        summary = self.get_session_summary()
        
        logger.info("=" * 50)
        logger.info("会话成本统计总结")
        logger.info("=" * 50)
        logger.info(f"模型: {summary['model']}")
        logger.info(f"总耗时: {summary['duration_seconds']}秒")
        logger.info(f"Token使用: {summary['token_usage']}")
        logger.info(f"总成本: ${summary['cost_info']['total_cost']:.6f}")
        logger.info(f"- Prompt成本: ${summary['cost_info']['prompt_cost']:.6f}")
        logger.info(f"- Completion成本: ${summary['cost_info']['completion_cost']:.6f}")
        logger.info("=" * 50)
    
    @staticmethod
    def extract_token_usage_from_response(response) -> Optional[TokenUsage]:
        """从LangChain响应中提取token使用情况"""
        try:
            # 尝试从response中提取token使用信息
            if hasattr(response, 'usage_metadata'):
                # 新版本LangChain
                usage = response.usage_metadata
                return TokenUsage(
                    prompt_tokens=usage.get('input_tokens', 0),
                    completion_tokens=usage.get('output_tokens', 0),
                    total_tokens=usage.get('total_tokens', 0)
                )
            elif hasattr(response, 'response_metadata'):
                # 从response_metadata中提取
                metadata = response.response_metadata
                if 'token_usage' in metadata:
                    token_usage = metadata['token_usage']
                    return TokenUsage(
                        prompt_tokens=token_usage.get('prompt_tokens', 0),
                        completion_tokens=token_usage.get('completion_tokens', 0),
                        total_tokens=token_usage.get('total_tokens', 0)
                    )
            
            # 如果没有找到token使用信息，返回None
            return None
            
        except Exception as e:
            logger.warning(f"提取token使用信息失败: {e}")
            return None

def format_cost_summary(cost_info: CostInfo, token_usage: TokenUsage) -> str:
    """格式化成本摘要"""
    return (
        f"Token: {token_usage.total_tokens} "
        f"(prompt: {token_usage.prompt_tokens}, completion: {token_usage.completion_tokens}) | "
        f"Cost: ${cost_info.total_cost:.6f}"
    )