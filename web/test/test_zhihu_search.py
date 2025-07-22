"""
知乎搜索功能测试
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web.database.queries import DataQueryService, SearchFilters
from web.database.models import ZhihuContent
from web.database.connection import get_db_session


def test_zhihu_data_exists():
    """测试知乎数据是否存在"""
    print("=== 测试知乎数据是否存在 ===")
    
    try:
        with get_db_session() as session:
            # 查询知乎表总数据量
            total_count = session.query(ZhihuContent).count()
            print(f"知乎表总数据量: {total_count}")
            
            if total_count > 0:
                # 获取最新的几条数据
                latest_records = session.query(ZhihuContent).order_by(
                    ZhihuContent.id.desc()
                ).limit(5).all()
                
                print(f"\n最新的{len(latest_records)}条记录:")
                for i, record in enumerate(latest_records, 1):
                    print(f"{i}. ID: {record.content_id}")
                    print(f"   标题: {record.title[:50]}...")
                    print(f"   创建时间: {record.created_time}")
                    print(f"   关键词: {record.source_keyword}")
                    print("---")
                
                return True
            else:
                print("❌ 知乎表中没有数据")
                return False
                
    except Exception as e:
        print(f"❌ 查询知乎数据失败: {e}")
        return False


def test_zhihu_time_parsing():
    """测试知乎时间字段解析"""
    print("\n=== 测试知乎时间字段解析 ===")
    
    try:
        with get_db_session() as session:
            # 获取一些样本数据
            sample_records = session.query(ZhihuContent).limit(10).all()
            
            if not sample_records:
                print("❌ 没有找到知乎数据进行测试")
                return False
            
            print(f"分析 {len(sample_records)} 条样本数据的时间格式:")
            
            time_formats = {}
            for record in sample_records:
                time_str = record.created_time
                print(f"原始时间: '{time_str}' (类型: {type(time_str)})")
                
                # 尝试解析时间
                from web.database.queries import parse_time_for_platform
                try:
                    parsed_time = parse_time_for_platform('zhihu', time_str)
                    print(f"  -> 解析结果: {parsed_time}")
                    
                    time_format = str(type(time_str))
                    time_formats[time_format] = time_formats.get(time_format, 0) + 1
                    
                except Exception as e:
                    print(f"  -> 解析失败: {e}")
                
                print("---")
            
            print(f"\n时间格式统计: {time_formats}")
            return True
            
    except Exception as e:
        print(f"❌ 时间解析测试失败: {e}")
        return False


def test_zhihu_keyword_search():
    """测试知乎关键词搜索"""
    print("\n=== 测试知乎关键词搜索 ===")
    
    # 测试多个关键词
    test_keywords = ["澳鹏", "appen", "知乎", "技术"]
    
    for keyword in test_keywords:
        print(f"\n搜索关键词: '{keyword}'")
        
        try:
            with DataQueryService() as service:
                filters = SearchFilters(
                    platforms=['zhihu'],
                    keywords=keyword,
                    start_time=datetime.now() - timedelta(days=365*2),  # 最近2年
                    end_time=datetime.now(),
                    page=1,
                    page_size=10
                )
                
                results, total_count = service.search_content(filters)
                print(f"  找到 {total_count} 条结果")
                
                if results:
                    print("  样本结果:")
                    for i, item in enumerate(results[:3], 1):
                        print(f"    {i}. {item.title[:30]}...")
                        print(f"       时间: {item.publish_time}")
                        print(f"       作者: {item.author_name}")
                
        except Exception as e:
            print(f"  ❌ 搜索失败: {e}")


def test_zhihu_time_filter():
    """测试知乎时间筛选"""
    print("\n=== 测试知乎时间筛选 ===")
    
    # 测试不同的时间范围
    time_ranges = [
        ("最近7天", datetime.now() - timedelta(days=7), datetime.now()),
        ("最近30天", datetime.now() - timedelta(days=30), datetime.now()),
        ("最近1年", datetime.now() - timedelta(days=365), datetime.now()),
        ("最近2年", datetime.now() - timedelta(days=365*2), datetime.now()),
    ]
    
    for range_name, start_time, end_time in time_ranges:
        print(f"\n时间范围: {range_name}")
        print(f"  开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            with DataQueryService() as service:
                filters = SearchFilters(
                    platforms=['zhihu'],
                    keywords="",  # 不限关键词
                    start_time=start_time,
                    end_time=end_time,
                    page=1,
                    page_size=5
                )
                
                results, total_count = service.search_content(filters)
                print(f"  找到 {total_count} 条结果")
                
                if results:
                    print("  时间分布:")
                    for item in results:
                        print(f"    - {item.publish_time.strftime('%Y-%m-%d %H:%M')} | {item.title[:30]}...")
                
        except Exception as e:
            print(f"  ❌ 时间筛选失败: {e}")


def test_zhihu_analysis_info():
    """测试知乎analysis_info字段"""
    print("\n=== 测试知乎analysis_info字段 ===")
    
    try:
        with get_db_session() as session:
            # 查询有analysis_info的记录
            records_with_analysis = session.query(ZhihuContent).filter(
                ZhihuContent.analysis_info.isnot(None)
            ).limit(5).all()
            
            print(f"有analysis_info的记录数: {len(records_with_analysis)}")
            
            if records_with_analysis:
                for i, record in enumerate(records_with_analysis, 1):
                    print(f"\n记录 {i}:")
                    print(f"  标题: {record.title[:40]}...")
                    analysis_info = record.get_analysis_info()
                    if analysis_info:
                        print(f"  情感: {analysis_info.get('sentiment', 'N/A')}")
                        print(f"  评分: {analysis_info.get('sentiment_score', 'N/A')}")
                        print(f"  关键词: {analysis_info.get('keywords', 'N/A')}")
                    else:
                        print(f"  analysis_info解析失败: {record.analysis_info}")
            else:
                print("❌ 没有找到有analysis_info的知乎记录")
                
                # 查询所有记录的analysis_info状态
                all_records = session.query(ZhihuContent).limit(10).all()
                print(f"\n检查前10条记录的analysis_info状态:")
                for record in all_records:
                    status = "有数据" if record.analysis_info else "NULL"
                    print(f"  ID {record.content_id}: {status}")
                
        return len(records_with_analysis) > 0
        
    except Exception as e:
        print(f"❌ analysis_info测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("🧪 知乎搜索功能综合测试")
    print("=" * 50)
    
    # 运行所有测试
    tests = [
        test_zhihu_data_exists,
        test_zhihu_time_parsing,
        test_zhihu_keyword_search,
        test_zhihu_time_filter,
        test_zhihu_analysis_info,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 执行失败: {e}")
            results.append((test_func.__name__, False))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("🔍 测试结果汇总:")
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    # 提供建议
    failed_tests = [name for name, success in results if not success]
    if failed_tests:
        print(f"\n⚠️  需要关注的问题:")
        for test_name in failed_tests:
            if 'data_exists' in test_name:
                print("  - 知乎表可能没有数据，需要运行爬虫获取数据")
            elif 'time_parsing' in test_name:
                print("  - 知乎时间字段解析有问题，需要检查时间格式")
            elif 'keyword_search' in test_name:
                print("  - 知乎关键词搜索有问题，可能是查询逻辑错误")
            elif 'time_filter' in test_name:
                print("  - 知乎时间筛选有问题，可能是时间比较逻辑错误")
            elif 'analysis_info' in test_name:
                print("  - 知乎缺少AI分析数据，需要运行analysis_job")


if __name__ == "__main__":
    main()