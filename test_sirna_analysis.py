import sys
import os
from Bio.Seq import Seq

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sirna_analysis import check_sirna_match

def test_sirna_trimming():
    """测试对非siRNA序列两端截短2个碱基后重新匹配的功能"""
    print("开始测试siRNA序列两端截短重新匹配功能...")
    print("=" * 50)
    
    # 测试用例1: 原始序列不匹配，但截短后匹配（正义链）
    print("\n测试用例1: 原始序列不匹配，但截短后匹配正义链")
    # 设计一个更短的靶序列，确保截短后的序列能够完全匹配
    target_seq = "ATCGTACGTACGTACGTACGTA"
    # 靶序列的第2-20位是: TCGTACGTACGTACGTACG (19bp)
    # 原始序列: 两端各2个碱基与靶序列不匹配，中间19个碱基完全匹配
    query_seq = "XX" + "TCGTACGTACGTACGTACG" + "YY"  # 原始序列: XX + 匹配部分 + YY，总长度23bp
    
    print(f"靶序列: {target_seq}")
    print(f"查询序列: {query_seq}")
    print(f"查询序列长度: {len(query_seq)}")
    print(f"截短后序列: {query_seq[2:-2]}")
    print(f"截短后序列长度: {len(query_seq[2:-2])}")
    
    # 调用check_sirna_match函数
    strand, pos = check_sirna_match(query_seq, target_seq, max_mismatch=1)
    
    print(f"结果链类型: {strand}")
    print(f"结果位置: {pos}")
    
    if strand == "正义链" and "[存在突出端]" in pos:
        print("✅ 测试通过: 正确截短并标注为正义链且存在突出端")
    else:
        print("❌ 测试失败")
    
    # 测试用例2: 原始序列不匹配，但截短后匹配（反义链）
    print("\n测试用例2: 原始序列不匹配，但截短后匹配反义链")
    # 重新设计：确保截短后的查询序列本身不匹配靶序列，只有其反向互补才匹配
    target_seq = "ATCGATCGATCGATCGATC"  # 18bp的靶序列，正向链
    
    # 截短后的查询序列应该是靶序列的反向互补
    rc_seq = str(Seq(target_seq).reverse_complement())  # 靶序列的反向互补
    query_seq = "XX" + rc_seq + "YY"  # 总长度22bp，两端各2个不匹配碱基
    
    # 验证设计：
    # 1. 截短后的查询序列本身不应匹配靶序列
    print(f"靶序列: {target_seq}")
    print(f"截短后查询序列: {rc_seq}")
    print(f"截短后查询序列是否匹配靶序列: {'是' if rc_seq in target_seq else '否'}")
    
    # 2. 截短后查询序列的反向互补应该匹配靶序列
    rc_complement = str(Seq(rc_seq).reverse_complement())
    print(f"截短后查询序列的反向互补: {rc_complement}")
    print(f"反向互补是否匹配靶序列: {'是' if rc_complement == target_seq else '否'}")
    
    # 3. 确保原始查询序列不直接匹配
    print(f"原始查询序列: {query_seq}")
    print(f"原始查询序列是否匹配靶序列: {'是' if query_seq in target_seq else '否'}")
    print(f"原始查询序列的反向互补是否匹配靶序列: {'是' if str(Seq(query_seq).reverse_complement()) in target_seq else '否'}")
    
    print(f"靶序列: {target_seq}")
    print(f"查询序列: {query_seq}")
    print(f"查询序列长度: {len(query_seq)}")
    print(f"截短后序列: {query_seq[2:-2]}")
    print(f"截短后序列长度: {len(query_seq[2:-2])}")
    
    # 调用check_sirna_match函数
    strand, pos = check_sirna_match(query_seq, target_seq, max_mismatch=1)
    
    print(f"\n结果链类型: {strand}")
    print(f"结果位置: {pos}")
    
    if strand == "反义链" and "[存在突出端]" in pos:
        print("✅ 测试通过: 正确截短并标注为反义链且存在突出端")
    else:
        print("❌ 测试失败")
    
    # 测试用例3: 原始序列已经匹配，不应该被截短
    print("\n测试用例3: 原始序列已经匹配，不应该被截短")
    target_seq = "AAATCGTACGTACGTACGTACGTACGTAAAA"
    query_seq = "TCGTACGTACGTACGTACG"  # 正好匹配靶序列中间部分
    
    print(f"靶序列: {target_seq}")
    print(f"查询序列: {query_seq}")
    print(f"查询序列长度: {len(query_seq)}")
    
    # 调用check_sirna_match函数
    strand, pos = check_sirna_match(query_seq, target_seq, max_mismatch=1)
    
    print(f"结果链类型: {strand}")
    print(f"结果位置: {pos}")
    
    if strand == "正义链" and "[存在突出端]" not in pos:
        print("✅ 测试通过: 原始序列匹配，未被截短")
    else:
        print("❌ 测试失败")
    
    # 测试用例4: 原始序列不匹配，截短后也不匹配
    print("\n测试用例4: 原始序列不匹配，截短后也不匹配")
    target_seq = "AAATCGTACGTACGTACGTACGTACGTAAAA"
    query_seq = "TTTT" + "ZZZZZZZZZZZZZZZZZZZ" + "GGGG"  # 中间部分完全不匹配
    
    print(f"靶序列: {target_seq}")
    print(f"查询序列: {query_seq}")
    print(f"查询序列长度: {len(query_seq)}")
    
    # 调用check_sirna_match函数
    strand, pos = check_sirna_match(query_seq, target_seq, max_mismatch=1)
    
    print(f"结果链类型: {strand}")
    print(f"结果位置: {pos}")
    
    if strand == "非siRNA" and pos == "N/A":
        print("✅ 测试通过: 截短后仍不匹配，返回非siRNA")
    else:
        print("❌ 测试失败")
    
    # 测试用例5: 序列长度不足22bp，不应被截短
    print("\n测试用例5: 序列长度不足22bp，不应被截短")
    target_seq = "AAATCGTACGTACGTACGTACGTACGTAAAA"
    # 设计一个长度正好为21bp的查询序列，确保它不匹配靶序列
    # 使用一个与靶序列完全不匹配的序列
    query_seq = "ATCGATCGATCGATCGATCGX"  # 21bp，最后一个碱基与靶序列不匹配
    
    print(f"靶序列: {target_seq}")
    print(f"查询序列: {query_seq}")
    print(f"查询序列长度: {len(query_seq)}")
    
    # 调用check_sirna_match函数
    strand, pos = check_sirna_match(query_seq, target_seq, max_mismatch=1)
    
    print(f"结果链类型: {strand}")
    print(f"结果位置: {pos}")
    
    if strand == "非siRNA" and pos == "N/A" and "[存在突出端]" not in pos:
        print("✅ 测试通过: 序列长度不足22bp，未被截短")
    else:
        print("❌ 测试失败")
    
    print("\n" + "=" * 50)
    print("所有测试用例执行完毕！")

if __name__ == "__main__":
    test_sirna_trimming()
