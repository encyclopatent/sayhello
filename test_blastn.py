#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试网络BLAST功能
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sirna_analysis import blastn_search_ncbi


def test_blastn_search():
    """测试NCBI BLAST网络检索功能"""
    print("测试NCBI BLAST网络检索功能...")
    
    # 使用一个简单的测试序列
    test_sequence = "AGCTTGCATGCCTGCAGGTCGACTCTAGAGGATCCCCGGGTACCGAGCTCGAATTCGTAATCATGGTCATAGCTGTTTCCTGTGTGAAAATTGTTATCCGCTCACAATTCCACACAACATACGAGCCGGAAGCATAAAGTGTAAAGCCTGGGGTGCCTAATGAGTGAGCTAACTCACATTAGCAACATAGTACATATGATTATCTGCGCGCTGTACTGTAACACCCATGTACATTCACATCCATATGTATATTCACATGTCATACGCGTAACGTAACATATGATTATCTGCGCGCTGTACTGTAACACCCATGTACATTCACATCCATATGTATATTCACATGTCATACGCGTAACGTAACATATGATTATCTGCGCGCTGTACTGTAACACCCATGTACATTCACATCCATATGTATATTCACATGTCATACGCGTAACGTAACATATGATTATCTGCGCGCTGTACTGTAACACCCATGTACATTCACATCCATATGTATATTCACATGTCATACGCGTAACGTAACATATGATTATCTGCGCGCTGTACTGTAACACCCATGTACATTCACATCCATATGTATATTCACATGTCATACGCGTAACGTAACATATGATTATCTGCGCGCTGTACTGTAACACCCATGTACATTCACATCCATATGTATATTCACATGTCATACGCGTAACGTAACATATGATTATCTGCGCGCTGTACTGTAACACCCATGTACATTCACATCCATATGTATATTCACATGTCATACGCGTAACGTAAC"
    
    try:
        print(f"正在检索序列...")
        results = blastn_search_ncbi(test_sequence)
        
        print(f"检索完成！找到 {len(results)} 个匹配结果")
        
        if results:
            print("\n前5个匹配结果：")
            for i, result in enumerate(results[:5]):
                print(f"\n结果 {i+1}:")
                print(f"NCBI ID: {result['ncbi_id']}")
                print(f"描述: {result['description']}")
                print(f"匹配长度: {result['match_length']}")
                print(f"一致性: {result['identity']} ({result['identity_percent']:.2f}%)")
                print(f"E值: {result['evalue']:.2e}")
        else:
            print("未找到匹配结果")
            
    except Exception as e:
        print(f"BLAST测试失败: {e}")
        return False
        
    return True


if __name__ == "__main__":
    success = test_blastn_search()
    if success:
        print("\n✅ BLAST功能测试成功！")
        sys.exit(0)
    else:
        print("\n❌ BLAST功能测试失败！")
        sys.exit(1)
