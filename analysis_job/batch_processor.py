"""
批量处理器模块
"""

import logging
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import BATCH_CONFIG, PLATFORM_TABLES
from .database_orm import DatabaseManager
from .analyzer import AIAnalyzer
from .models import ContentItem, BatchAnalysisRequest, ProcessingStats


logger = logging.getLogger(__name__)


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or BATCH_CONFIG
        self.db_manager = DatabaseManager()
        self.analyzer = AIAnalyzer()
        self.stats = ProcessingStats()
        
        logger.info("批量处理器初始化完成")
    
    def process_platform(self, platform: str, limit: int = 10) -> ProcessingStats:
        """处理指定平台的内容"""
        if platform not in PLATFORM_TABLES:
            raise ValueError(f"不支持的平台: {platform}")
        
        logger.info(f"开始处理平台: {platform}, 限制: {limit}")
        
        # 重置统计
        self.stats = ProcessingStats()
        
        try:
            # 获取未分析的内容
            unanalyzed_content = self.db_manager.get_unanalyzed_content(platform, limit)
            
            # 批量获取内容和评论
            content_ids = [item.content_id for item in unanalyzed_content]
            content_items = self.db_manager.batch_get_content_with_comments(platform, content_ids)
            
            if not content_items:
                logger.info(f"平台 {platform} 没有需要分析的内容")
                return self.stats
            
            self.stats.total_items = len(content_items)
            logger.info(f"获取到 {len(content_items)} 条待分析内容")
            
            # 创建批次请求
            batch_request = BatchAnalysisRequest(
                platform=platform,
                content_items=content_items,
                batch_size=self.config["default_batch_size"]
            )
            
            # 动态拆分批次
            batches = self._split_to_optimal_batches(batch_request)
            logger.info(f"拆分为 {len(batches)} 个批次")
            
            # 处理每个批次
            all_results = []
            for i, batch in enumerate(batches, 1):
                logger.info(f"处理批次 {i}/{len(batches)}: {len(batch.content_items)} 条内容")
                
                try:
                    # 分析批次
                    results = self.analyzer.analyze_batch_request(batch)
                    
                    # 批量更新数据库
                    updated_count = self.db_manager.batch_update_analysis_results(platform, results)
                    
                    if updated_count > 0:
                        self.stats.success_items += updated_count
                        logger.info(f"批次 {i} 成功更新 {updated_count} 条记录")
                    else:
                        self.stats.failed_items += len(batch.content_items)
                        logger.error(f"批次 {i} 更新失败")
                    
                    all_results.extend(results)
                    
                except Exception as e:
                    logger.error(f"批次 {i} 处理失败: {e}")
                    self.stats.failed_items += len(batch.content_items)
                    continue
            
            self.stats.processed_items = self.stats.success_items + self.stats.failed_items
            self.stats.finish()
            
            logger.info(f"平台 {platform} 处理完成: {self.stats.to_dict()}")
            return self.stats
            
        except Exception as e:
            logger.error(f"处理平台 {platform} 失败: {e}")
            self.stats.finish()
            raise
        finally:
            # 断开数据库连接
            # ORM版本不需要手动断开连接
            pass
    
    def _split_to_optimal_batches(self, request: BatchAnalysisRequest) -> List[BatchAnalysisRequest]:
        """拆分为最优批次"""
        target_length = self.config["target_content_length"]
        max_length = self.config["max_content_length"]
        
        # 先按目标长度拆分
        batches = request.split_to_batches(target_length)
        
        # 进一步检查是否有批次过大
        final_batches = []
        for batch in batches:
            if batch.get_total_length() > max_length:
                # 如果批次仍然过大，按最大长度重新拆分
                sub_batches = batch.split_to_batches(max_length)
                final_batches.extend(sub_batches)
            else:
                final_batches.append(batch)
        
        return final_batches
    
    def process_specific_content(self, platform: str, content_ids: List[str]) -> ProcessingStats:
        """处理指定的内容"""
        if platform not in PLATFORM_TABLES:
            raise ValueError(f"不支持的平台: {platform}")
        
        logger.info(f"开始处理指定内容: {platform}, {len(content_ids)} 条")
        
        # 重置统计
        self.stats = ProcessingStats()
        self.stats.total_items = len(content_ids)
        
        try:
            # 获取指定内容
            content_items = []
            for content_id in content_ids:
                try:
                    item = self.db_manager.get_content_with_comments(platform, content_id)
                    content_items.append(item)
                except Exception as e:
                    logger.warning(f"获取内容 {content_id} 失败: {e}")
                    self.stats.add_skip()
                    continue
            
            if not content_items:
                logger.info("没有有效的内容需要处理")
                return self.stats
            
            # 创建和处理批次
            batch_request = BatchAnalysisRequest(
                platform=platform,
                content_items=content_items,
                batch_size=self.config["default_batch_size"]
            )
            
            batches = self._split_to_optimal_batches(batch_request)
            
            # 处理每个批次
            for i, batch in enumerate(batches, 1):
                try:
                    results = self.analyzer.analyze_batch_request(batch)
                    
                    # 更新数据库
                    update_data = []
                    for j, result in enumerate(results):
                        if j < len(batch.content_items):
                            content_id = batch.content_items[j].content_id
                            update_data.append((content_id, result))
                    
                    updated_count = self.db_manager.batch_update_analysis_results(platform, update_data)
                    
                    if updated_count > 0:
                        self.stats.success_items += updated_count
                    else:
                        self.stats.failed_items += len(batch.content_items)
                        
                except Exception as e:
                    logger.error(f"批次 {i} 处理失败: {e}")
                    self.stats.failed_items += len(batch.content_items)
            
            self.stats.processed_items = self.stats.success_items + self.stats.failed_items
            self.stats.finish()
            
            logger.info(f"指定内容处理完成: {self.stats.to_dict()}")
            return self.stats
            
        except Exception as e:
            logger.error(f"处理指定内容失败: {e}")
            self.stats.finish()
            raise
        finally:
            # ORM版本不需要手动断开连接
            pass
    
    def get_platform_stats(self, platform: str) -> Dict[str, Any]:
        """获取平台统计信息"""
        try:
            return self.db_manager.get_analysis_stats(platform)
        except Exception as e:
            logger.error(f"获取平台统计失败: {e}")
            return {}
        finally:
            # ORM版本不需要手动断开连接
            pass
    
    def test_processing(self, platform: str) -> bool:
        """测试处理功能"""
        try:
            # 测试数据库连接
            self.db_manager.connect()
            
            # 测试AI分析器
            if not self.analyzer.test_connection():
                return False
            
            # 获取一条内容进行测试
            test_items = self.db_manager.get_unanalyzed_content(platform, 1)
            
            if test_items:
                result = self.analyzer.analyze_single(test_items[0])
                if result and result.validate():
                    logger.info("处理功能测试成功")
                    return True
            
            logger.warning("没有找到测试数据")
            return True  # 没有数据也算测试通过
            
        except Exception as e:
            logger.error(f"处理功能测试失败: {e}")
            return False
        finally:
            # ORM版本不需要手动断开连接
            pass


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="AI内容分析批量处理器")
    parser.add_argument("--platform", required=True, choices=list(PLATFORM_TABLES.keys()), 
                       help="平台名称")
    parser.add_argument("--limit", type=int, default=10, help="处理数量限制")
    parser.add_argument("--content-ids", nargs="+", help="指定要处理的内容ID")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--test", action="store_true", help="运行测试")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="日志级别")
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 创建处理器
    processor = BatchProcessor()
    
    try:
        if args.test:
            # 运行测试
            if processor.test_processing(args.platform):
                print(f"✓ 平台 {args.platform} 测试通过")
            else:
                print(f"✗ 平台 {args.platform} 测试失败")
                return 1
        
        elif args.stats:
            # 显示统计信息
            stats = processor.get_platform_stats(args.platform)
            print(f"平台 {args.platform} 统计信息:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        elif args.content_ids:
            # 处理指定内容
            stats = processor.process_specific_content(args.platform, args.content_ids)
            print(f"处理完成: {stats.to_dict()}")
        
        else:
            # 批量处理
            stats = processor.process_platform(args.platform, args.limit)
            print(f"处理完成: {stats.to_dict()}")
        
        return 0
        
    except Exception as e:
        print(f"处理失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())