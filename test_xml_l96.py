#!/usr/bin/env python3
# 测试L96处理功能是否正常

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import parse_sequence
from parser import get_sequence_summary

def test_l96_handling():
    """测试L96处理功能：过滤L96但保留提醒信息"""
    print("=== 测试L96处理功能 ===")
    
    # 测试用例：带L96的RNA序列
    seq_with_l96 = "AmGmCmAmGmAfCmAfCfUmGmGmGmsAmsUfL96"
    moltype = "RNA"
    
    try:
        print(f"\n1. 测试序列解析（过滤L96）:")
        print(f"   输入序列: {seq_with_l96}")
        
        # 测试parse_sequence函数
        naked_sequence, modifications, special_positions, original_moltype, has_degenerate, ligand_removed = parse_sequence(seq_with_l96, moltype)
        
        print(f"   解析后的裸序列: {naked_sequence}")
        print(f"   修饰信息: {modifications}")
        print(f"   配体是否被移除: {ligand_removed}")
        
        # 检查L96是否被正确过滤
        if "L96" not in naked_sequence and ligand_removed:
            print("   ✅ L96已被正确过滤")
        else:
            print("   ❌ L96过滤失败")
        
        # 测试get_sequence_summary函数是否保留提醒信息
        print(f"\n2. 测试序列摘要（保留L96提醒）:")
        # 创建测试序列数据
        test_sequence = [
            (seq_with_l96, moltype, "synthetic construct", "other RNA", [], [], [], True)
        ]
        
        summary = get_sequence_summary(test_sequence)
        print(f"   序列摘要: {summary}")
        
        # 检查摘要中是否包含L96提醒
        if summary['details'][0]['modification_special_notes'] and "L96" in summary['details'][0]['modification_special_notes']:
            print("   ✅ L96提醒信息已保留")
        else:
            print("   ❌ L96提醒信息丢失")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    test_l96_handling()
