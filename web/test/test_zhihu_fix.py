"""
知乎修复验证测试
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web.database.queries import DataQueryService, SearchFilters


def test_zhihu_timestamp_parsing():
    """测试知乎时间戳解析"""
    print("=== 测试知乎时间戳解析 ===")
    
    # 测试时间戳转换
    test_timestamps = [
        "1653555566",  # 2022-05-26
        "1654420610",  # 2022-06-05  
        "1748509104",  # 2025-01-28
        "1751858725",  # 2025-07-06
    ]
    
    for ts_str in test_timestamps:
        try:
            timestamp = int(ts_str)
            dt = datetime.fromtimestamp(timestamp)
            print(f"时间戳 {ts_str} -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"时间戳 {ts_str} 解析失败: {e}")


def test_zhihu_search_with_fix():
    """测试修复后的知乎搜索"""
    print("\n=== 测试修复后的知乎搜索 ===")
    
    # 测试不同的关键词
    test_keywords = ["appen", "澳鹏", "澳鹏科技"]
    
    for keyword in test_keywords:
        print(f"\n🔍 搜索关键词: '{keyword}'")
        
        try:
            with DataQueryService() as service:
                # 使用较大的时间范围
                filters = SearchFilters(
                    platforms=['zhihu'],
                    keywords=keyword,
                    start_time=datetime(2020, 1, 1),  # 从2020年开始
                    end_time=datetime.now(),
                    page=1,
                    page_size=5
                )
                
                results, total_count = service.search_content(filters)
                print(f"  📊 找到 {total_count} 条结果")
                
                if results:
                    print("  📝 样本结果:")
                    for i, item in enumerate(results, 1):
                        print(f"    {i}. {item.title[:50]}...")
                        print(f"       ⏰ 时间: {item.publish_time.strftime('%Y-%m-%d %H:%M')}")
                        print(f"       👤 作者: {item.author_name}")
                        print(f"       📊 互动: {item.interaction_count}")
                        print(f"       😊 情感: {item.sentiment}")
                        print("       ---")
                else:
                    print("  ❌ 没有找到结果")
                
        except Exception as e:
            print(f"  ❌ 搜索失败: {e}")
            import traceback
            traceback.print_exc()


def test_zhihu_time_range():
    """测试知乎时间范围搜索"""
    print("\n=== 测试知乎时间范围搜索 ===")
    
    # 测试不同时间范围
    time_ranges = [
        ("2020年以来", datetime(2020, 1, 1), datetime.now()),
        ("2022年", datetime(2022, 1, 1), datetime(2022, 12, 31)),
        ("2024年以来", datetime(2024, 1, 1), datetime.now()),
        ("最近1年", datetime.now() - timedelta(days=365), datetime.now()),
    ]
    
    for range_name, start_time, end_time in time_ranges:
        print(f"\n📅 时间范围: {range_name}")
        print(f"   开始: {start_time.strftime('%Y-%m-%d')}")
        print(f"   结束: {end_time.strftime('%Y-%m-%d')}")
        
        try:
            with DataQueryService() as service:
                filters = SearchFilters(
                    platforms=['zhihu'],
                    keywords="",  # 不限关键词
                    start_time=start_time,
                    end_time=end_time,
                    page=1,
                    page_size=3
                )
                
                results, total_count = service.search_content(filters)
                print(f"   📊 找到 {total_count} 条结果")
                
                if results:
                    print("   📝 时间分布:")
                    for item in results:
                        print(f"     - {item.publish_time.strftime('%Y-%m-%d')} | {item.title[:30]}...")
                
        except Exception as e:
            print(f"   ❌ 时间筛选失败: {e}")


def main():
    """运行修复验证测试"""
    print("🔧 知乎修复验证测试")
    print("=" * 50)
    
    test_zhihu_timestamp_parsing()
    test_zhihu_search_with_fix()
    test_zhihu_time_range()
    
    print("\n" + "=" * 50)
    print("✅ 知乎修复验证完成")


if __name__ == "__main__":
    main()