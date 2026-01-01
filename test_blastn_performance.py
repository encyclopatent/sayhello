#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BLASTN性能测试脚本
用于分析siRNA序列匹配工具的性能瓶颈
"""

import time
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sirna_analysis import find_max_continuous, blastn_verify, check_sirna_match

def test_sliding_window_performance():
    """测试滑动窗口算法性能"""
    print("=== 滑动窗口算法性能测试 ===")
    
    # 生成测试数据
    query_seq = "GTGCTGCTGCTGCTGCTGCT"
    target_seq = "A" * 1000 + "GTGCTGCTGCTGCTGCTGCT" + "T" * 1000
    
    # 测试单次调用
    start_time = time.time()
    start, end = find_max_continuous(query_seq, target_seq)
    elapsed = time.time() - start_time
    
    print(f"滑动窗口单次调用耗时: {elapsed:.6f}秒")
    print(f"匹配结果: {start}-{end} ({end-start}bp)")
    
    # 测试批量调用
    print("\n批量测试100次滑动窗口算法:")
    start_time = time.time()
    for i in range(100):
        find_max_continuous(query_seq, target_seq)
    total_time = time.time() - start_time
    avg_time = total_time / 100
    
    print(f"总耗时: {total_time:.6f}秒")
    print(f"平均每次耗时: {avg_time:.6f}秒")
    
    return avg_time

def test_blastn_performance():
    """测试BLASTN调用性能"""
    print("\n=== BLASTN调用性能测试 ===")
    
    # 生成测试数据
    query_seq = "GTGCTGCTGCTGCTGCTGCT"
    target_seq = "A" * 1000 + "GTGCTGCTGCTGCTGCTGCT" + "T" * 1000
    
    # 测试单次BLASTN调用
    try:
        start_time = time.time()
        blast_results = blastn_verify(query_seq, target_seq)
        elapsed = time.time() - start_time
        
        print(f"BLASTN单次调用耗时: {elapsed:.6f}秒")
        if blast_results:
            print(f"BLASTN结果: {len(blast_results)}个匹配")
            print(f"最佳匹配: {blast_results[0]['subject_start']}-{blast_results[0]['subject_end']} ({blast_results[0]['length']}bp)")
        else:
            print("BLASTN未找到匹配")
    except Exception as e:
        print(f"BLASTN调用失败: {e}")
        return None
    
    # 测试缓存效果（第二次调用应该更快）
    print("\n测试BLASTN缓存效果:")
    try:
        start_time = time.time()
        blast_results = blastn_verify(query_seq, target_seq)
        cached_elapsed = time.time() - start_time
        
        print(f"缓存后BLASTN调用耗时: {cached_elapsed:.6f}秒")
        if cached_elapsed < elapsed:
            print(f"缓存提升: {elapsed/cached_elapsed:.2f}倍")
    except Exception as e:
        print(f"缓存测试失败: {e}")
    
    # 测试批量调用（混合有缓存和无缓存的情况）
    print("\n批量测试100次BLASTN调用:")
    start_time = time.time()
    success_count = 0
    fail_count = 0
    timeout_count = 0
    
    for i in range(100):
        # 使用不同的查询序列模拟不同场景
        if i % 5 == 0:
            # 50%的请求使用相同序列（触发缓存）
            test_query = query_seq
        else:
            # 50%的请求使用略有不同的序列（不触发缓存）
            test_query = query_seq[:-1] + ('A' if query_seq[-1] != 'A' else 'T')
        
        try:
            blastn_verify(test_query, target_seq)
            success_count += 1
        except subprocess.TimeoutExpired:
            timeout_count += 1
        except Exception as e:
            fail_count += 1
    
    total_time = time.time() - start_time
    avg_time = total_time / 100
    
    print(f"总耗时: {total_time:.6f}秒")
    print(f"平均每次耗时: {avg_time:.6f}秒")
    print(f"成功: {success_count}, 超时: {timeout_count}, 失败: {fail_count}")
    
    return avg_time

def test_combined_performance():
    """测试完整的check_sirna_match函数性能"""
    print("\n=== 完整匹配函数性能测试 ===")
    
    # 生成测试数据
    query_seq = "GTGCTGCTGCTGCTGCTGCT"
    target_seq = "A" * 1000 + "GTGCTGCTGCTGCTGCTGCT" + "T" * 1000
    
    # 测试不使用BLASTN的情况
    print("\n1. 不使用BLASTN验证:")
    start_time = time.time()
    for i in range(100):
        check_sirna_match(query_seq, target_seq, use_blastn=False)
    total_time_no_blastn = time.time() - start_time
    avg_time_no_blastn = total_time_no_blastn / 100
    
    print(f"总耗时: {total_time_no_blastn:.6f}秒")
    print(f"平均每次耗时: {avg_time_no_blastn:.6f}秒")
    
    # 测试使用BLASTN的情况
    print("\n2. 使用BLASTN验证:")
    start_time = time.time()
    success_count = 0
    fail_count = 0
    
    for i in range(100):
        try:
            result = check_sirna_match(query_seq, target_seq, use_blastn=True)
            success_count += 1
        except Exception as e:
            print(f"失败: {e}")
            fail_count += 1
    
    total_time_with_blastn = time.time() - start_time
    avg_time_with_blastn = total_time_with_blastn / 100
    
    print(f"总耗时: {total_time_with_blastn:.6f}秒")
    print(f"平均每次耗时: {avg_time_with_blastn:.6f}秒")
    print(f"成功: {success_count}, 失败: {fail_count}")
    
    # 计算性能差异
    if avg_time_no_blastn > 0:
        print(f"\nBLASTN验证导致性能下降: {avg_time_with_blastn/avg_time_no_blastn:.2f}倍")
    
    return avg_time_no_blastn, avg_time_with_blastn

def main():
    """主测试函数"""
    print("siRNA序列匹配工具性能测试")
    print("=" * 50)
    
    # 测试滑动窗口算法
    sliding_window_time = test_sliding_window_performance()
    
    # 测试BLASTN性能
    blastn_time = test_blastn_performance()
    
    # 测试完整函数性能
    no_blastn_time, with_blastn_time = test_combined_performance()
    
    print("\n" + "=" * 50)
    print("性能测试总结:")
    print(f"滑动窗口算法平均耗时: {sliding_window_time:.6f}秒")
    if blastn_time:
        print(f"BLASTN调用平均耗时: {blastn_time:.6f}秒")
    print(f"无BLASTN验证平均耗时: {no_blastn_time:.6f}秒")
    print(f"有BLASTN验证平均耗时: {with_blastn_time:.6f}秒")
    
    if no_blastn_time > 0:
        print(f"BLASTN验证开销比例: {((with_blastn_time - no_blastn_time)/with_blastn_time)*100:.1f}%")

if __name__ == "__main__":
    main()