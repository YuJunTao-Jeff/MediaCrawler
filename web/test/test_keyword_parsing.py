"""
关键词解析功能测试
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_keyword_splitting():
    """测试关键词分割逻辑"""
    print("=== 测试关键词分割逻辑 ===")
    
    # 测试用例
    test_cases = [
        "澳鹏科技",  # 单个关键词
        "澳鹏 科技 AI",  # 空格分割
        "appen,澳鹏,田小鹏,爱普恩",  # 逗号分割
        "appen,澳鹏,田小鹏,爱普恩,澳鹏大连,澳鹏无锡,澳鹏科技,澳鹏中国,澳鹏数据,澳鹏重庆",  # 完整的默认关键词
        "澳鹏, 科技, AI",  # 逗号+空格
        "澳鹏,科技 AI,人工智能",  # 混合分割
        "",  # 空字符串
        "   ",  # 只有空格
        "澳鹏,,科技",  # 连续逗号
    ]
    
    print("测试不同的关键词分割逻辑:")
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: '{test_input}'")
        
        # 当前的分割逻辑 (修复后的版本)
        keywords = []
        for part in test_input.replace(',', ' ').split():
            keyword = part.strip()
            if keyword:
                keywords.append(keyword)
        
        print(f"  分割结果: {keywords}")
        print(f"  关键词数量: {len(keywords)}")
        
        # 模拟SQL查询条件
        if keywords:
            like_conditions = [f"title LIKE '%{kw}%' OR content LIKE '%{kw}%'" for kw in keywords]
            sql_condition = " OR ".join([f"({cond})" for cond in like_conditions])
            print(f"  SQL条件: {sql_condition[:100]}...")
        else:
            print("  SQL条件: 无关键词，不添加筛选条件")


def test_search_logic_simulation():
    """模拟搜索逻辑测试"""
    print("\n=== 模拟搜索逻辑测试 ===")
    
    # 模拟数据
    mock_data = [
        {"title": "澳鹏科技发布AI新产品", "content": "澳鹏科技今天发布了最新的人工智能产品"},
        {"title": "appen公司收购案例", "content": "appen公司最近完成了一项重要收购"},
        {"title": "田小鹏谈AI发展", "content": "澳鹏创始人田小鹏分享了对AI行业的看法"},
        {"title": "爱普恩数据服务", "content": "爱普恩提供专业的数据标注服务"},
        {"title": "无关内容", "content": "这是一条与澳鹏无关的内容"},
        {"title": "澳鹏大连分公司", "content": "澳鹏在大连设立了新的分公司"},
        {"title": "腾讯AI研究", "content": "腾讯发布了新的AI研究成果"},
    ]
    
    # 测试关键词
    test_keywords = "appen,澳鹏,田小鹏,爱普恩,澳鹏大连"
    
    print(f"测试关键词: '{test_keywords}'")
    print(f"模拟数据量: {len(mock_data)}")
    
    # 分割关键词
    keywords = []
    for part in test_keywords.replace(',', ' ').split():
        keyword = part.strip()
        if keyword:
            keywords.append(keyword)
    
    print(f"分割后的关键词: {keywords}")
    
    # 模拟搜索
    matching_results = []
    for item in mock_data:
        matched = False
        matched_keywords = []
        
        for keyword in keywords:
            if keyword in item['title'] or keyword in item['content']:
                matched = True
                matched_keywords.append(keyword)
        
        if matched:
            matching_results.append({
                'item': item,
                'matched_keywords': matched_keywords
            })
    
    print(f"\n搜索结果: {len(matching_results)} 条匹配")
    for i, result in enumerate(matching_results, 1):
        item = result['item']
        matched_kw = result['matched_keywords']
        print(f"{i}. 标题: {item['title']}")
        print(f"   匹配关键词: {matched_kw}")
        print(f"   内容: {item['content'][:50]}...")
        print("---")


def test_default_keywords_coverage():
    """测试默认关键词覆盖度"""
    print("\n=== 测试默认关键词覆盖度 ===")
    
    default_keywords = "appen,澳鹏,田小鹏,爱普恩,澳鹏大连,澳鹏无锡,澳鹏科技,澳鹏中国,澳鹏数据,澳鹏重庆"
    
    # 分割关键词
    keywords = []
    for part in default_keywords.replace(',', ' ').split():
        keyword = part.strip()
        if keyword:
            keywords.append(keyword)
    
    print(f"默认关键词列表 ({len(keywords)} 个):")
    for i, kw in enumerate(keywords, 1):
        print(f"  {i:2d}. '{kw}'")
    
    # 分析关键词特点
    print(f"\n关键词分析:")
    print(f"  英文关键词: {[kw for kw in keywords if any(c.isalpha() and ord(c) < 128 for c in kw)]}")
    print(f"  中文关键词: {[kw for kw in keywords if any(ord(c) > 127 for c in kw)]}")
    print(f"  包含'澳鹏': {[kw for kw in keywords if '澳鹏' in kw]}")
    print(f"  地名相关: {[kw for kw in keywords if any(city in kw for city in ['大连', '无锡', '重庆', '中国'])]}")
    
    # 检查重复和包含关系
    duplicates = []
    for i, kw1 in enumerate(keywords):
        for j, kw2 in enumerate(keywords):
            if i != j and kw1 in kw2:
                duplicates.append((kw1, kw2))
    
    if duplicates:
        print(f"\n发现关键词包含关系:")
        for kw1, kw2 in duplicates:
            print(f"  '{kw1}' 包含在 '{kw2}' 中")
    else:
        print(f"\n✅ 关键词之间无包含关系")


def main():
    """运行所有测试"""
    print("🧪 关键词解析功能测试")
    print("=" * 50)
    
    test_keyword_splitting()
    test_search_logic_simulation()
    test_default_keywords_coverage()
    
    print("\n" + "=" * 50)
    print("✅ 关键词解析测试完成")
    print("\n💡 建议:")
    print("  1. 默认关键词应该涵盖澳鹏相关的主要变体")
    print("  2. 关键词分割逻辑应该支持逗号和空格分割")
    print("  3. 搜索时使用OR逻辑，匹配任一关键词即可")
    print("  4. 注意关键词之间的包含关系，避免重复匹配")


if __name__ == "__main__":
    main()