#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试L96配体忽略提醒是否正确显示在修饰和特殊说明中
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import get_sequence_summary

def test_l96_reminder():
    """测试L96配体忽略提醒功能"""
    print("=== 测试L96配体忽略提醒功能 ===")
    
    # 测试用例1：RNA序列结尾带L96
    test_cases = [
        (
            "(VP)(mG)*(mG)*(mU)(mU)(L96)",
            "RNA",
            "synthetic construct",
            None, [], [], [], None
        ),
        (
            "ATCG-L96",
            "DNA",
            "synthetic construct",
            None, [], [], [], None
        ),
        (
            "(VP)(mG)*(mR)*(mU)(L96)",
            "RNA",
            "synthetic construct",
            None, [], [], [], None
        )
    ]
    
    results = get_sequence_summary(test_cases)
    
    for i, result in enumerate(results['details'], 1):
        test_name = test_cases[i-1][0]
        print(f"\n测试 {i}: {test_name}")
        print(f"序列类型: {result['type']}")
        print(f"修饰和特殊说明: {result['modification_special_notes']}")
        
        # 验证L96是否在提醒中
        if "L96" in result['modification_special_notes']:
            print("✓ L96配体忽略提醒已正确显示")
        else:
            print("✗ L96配体忽略提醒未显示")
        
        # 验证简并碱基提醒（如果有）
        if test_name == "RNA序列包含L96和简并碱基":
            if "简并碱基" in result['modification_special_notes']:
                print("✓ 简并碱基提醒已正确显示")
            else:
                print("✗ 简并碱基提醒未显示")

if __name__ == "__main__":
    test_l96_reminder()
