import sys
import os
from Bio.Seq import Seq

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sirna_analysis import find_best_match

def test_fasta_match_with_extension():
    """测试突出端标记是否会影响与fasta结果的匹配"""
    print("开始测试突出端标记对fasta匹配的影响...")
    print("=" * 50)
    
    # 测试用例1: 带有突出端标记的查询位置
    print("\n测试用例1: 带有突出端标记的查询位置")
    query_pos = "5-24 (19bp) [存在突出端]"
    
    # 创建fasta文献结果
    literature_results = [
        {
            '文献序列ID': 'FASTA_001',
            '序列内容': 'ATCGTACGTACGTACGTACG',
            '匹配位置': '5-24 (19bp)',
            '匹配长度': 19
        },
        {
            '文献序列ID': 'FASTA_002',
            '序列内容': 'CGTACGTACGTACGTACGTA',
            '匹配位置': '6-25 (19bp)',
            '匹配长度': 19
        }
    ]
    
    print(f"查询位置: {query_pos}")
    print("文献结果:")
    for result in literature_results:
        print(f"  {result['文献序列ID']}: {result['匹配位置']}")
    
    # 调用find_best_match函数
    best_match = find_best_match(query_pos, literature_results)
    
    if best_match:
        print(f"找到最佳匹配: {best_match['文献序列ID']} (位置: {best_match['匹配位置']})")
        print("✅ 测试通过: 突出端标记不影响匹配")
    else:
        print("❌ 测试失败: 未找到匹配")
    
    # 测试用例2: 不带突出端标记的查询位置（作为对照）
    print("\n测试用例2: 不带突出端标记的查询位置")
    query_pos_no_ext = "5-24 (19bp)"
    
    best_match_no_ext = find_best_match(query_pos_no_ext, literature_results)
    
    if best_match_no_ext:
        print(f"找到最佳匹配: {best_match_no_ext['文献序列ID']} (位置: {best_match_no_ext['匹配位置']})")
        print("✅ 测试通过: 无突出端标记的匹配正常")
    else:
        print("❌ 测试失败: 未找到匹配")
    
    # 测试用例3: 验证两种情况是否找到相同的匹配
    print("\n测试用例3: 比较带/不带突出端标记的匹配结果")
    if best_match and best_match_no_ext:
        if best_match['文献序列ID'] == best_match_no_ext['文献序列ID']:
            print("✅ 测试通过: 带/不带突出端标记找到相同的匹配")
        else:
            print("❌ 测试失败: 带/不带突出端标记找到不同的匹配")
    else:
        print("❌ 测试失败: 至少有一个情况未找到匹配")
    
    # 测试用例4: 文献结果带有突出端标记
    print("\n测试用例4: 文献结果带有突出端标记")
    literature_results_with_ext = [
        {
            '文献序列ID': 'FASTA_003',
            '序列内容': 'ATCGTACGTACGTACGTACG',
            '匹配位置': '5-24 (19bp) [存在突出端]',
            '匹配长度': 19
        }
    ]
    
    query_pos2 = "5-24 (19bp)"
    best_match3 = find_best_match(query_pos2, literature_results_with_ext)
    
    if best_match3:
        print(f"找到最佳匹配: {best_match3['文献序列ID']} (位置: {best_match3['匹配位置']})")
        print("✅ 测试通过: 文献结果带突出端标记不影响匹配")
    else:
        print("❌ 测试失败: 未找到匹配")
    
    print("\n" + "=" * 50)
    print("所有测试用例执行完毕！")

if __name__ == "__main__":
    test_fasta_match_with_extension()
