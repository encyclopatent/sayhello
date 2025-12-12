#!/usr/bin/env python3
# 测试parse_sequence函数的错误处理和简并碱基检测功能

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import parse_sequence

def test_error_handling():
    """测试错误处理机制，包括行号信息"""
    print("=== 测试错误处理机制 ===")
    
    # 测试非法字符错误，带有行号
    try:
        parse_sequence("AGCTXYZ", "DNA", line_number=3)
    except ValueError as e:
        print(f"测试1（非法字符）：{e}")
        # 应该输出：第3行序列位置 5 处有非法字符 'X'
    
    # 测试氨基酸非法字符，带有行号
    try:
        parse_sequence("ARNDCEFGHIKLMFPQSXYZ", "AA", line_number=5)
    except ValueError as e:
        print(f"测试2（氨基酸非法字符）：{e}")
        # 应该输出：第5行第17号氨基酸字符'X'非法

def test_degenerate_bases():
    """测试简并碱基检测功能"""
    print("\n=== 测试简并碱基检测 ===")
    
    # 测试包含简并碱基的序列
    test_cases = [
        ("AGCTM", "DNA"),  # M = A/C
        ("AGCTR", "DNA"),  # R = A/G
        ("AGCTW", "DNA"),  # W = A/T
        ("AGCTS", "DNA"),  # S = C/G
        ("AGCTY", "DNA"),  # Y = C/T
        ("AGCTK", "DNA"),  # K = G/T
        ("AGCTAGCT", "DNA"),  # 没有简并碱基
    ]
    
    for seq, moltype in test_cases:
        result = parse_sequence(seq, moltype)
        print(f"序列 '{seq}' ({moltype}):")
        print(f"  解析结果: {result[0]}")
        print(f"  修饰: {result[1]}")
        print(f"  特殊位置: {result[2]}")
        print(f"  原始类型: {result[3]}")
        print(f"  包含简并碱基: {result[4]}")

def test_standard_sequences():
    """测试标准序列解析"""
    print("\n=== 测试标准序列解析 ===")
    
    # 测试RNA序列
    seq_rna = "AGCU"
    result = parse_sequence(seq_rna, "RNA")
    print(f"RNA序列 '{seq_rna}':")
    print(f"  解析结果: {result[0]}")
    print(f"  包含简并碱基: {result[4]}")
    
    # 测试DNA序列
    seq_dna = "AGCT"
    result = parse_sequence(seq_dna, "DNA")
    print(f"DNA序列 '{seq_dna}':")
    print(f"  解析结果: {result[0]}")
    print(f"  包含简并碱基: {result[4]}")
    
    # 测试氨基酸序列
    seq_aa = "ARNDCEFGHIKLMFPQS"
    result = parse_sequence(seq_aa, "AA")
    print(f"氨基酸序列 '{seq_aa}':")
    print(f"  解析结果: {result[0]}")
    print(f"  包含简并碱基: {result[4]}")

if __name__ == "__main__":
    test_error_handling()
    test_degenerate_bases()
    test_standard_sequences()
    print("\n=== 所有测试完成 ===")
