#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试新格式序列解析结果，以便了解为什么无法导入WIPO工具
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import convert_new_format_to_old, parse_sequence, get_sequence_summary

def test_new_format_parsing():
    """测试新格式序列解析"""
    print("=== 测试新格式序列解析结果 ===")
    
    # 使用用户提供的新格式序列示例
    new_format_sequence = "(VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)"
    
    print(f"\n1. 原始新格式序列：")
    print(new_format_sequence)
    
    # 转换为旧格式
    old_format_sequence = convert_new_format_to_old(new_format_sequence)
    print(f"\n2. 转换后的旧格式序列：")
    print(old_format_sequence)
    
    # 解析序列
    try:
        naked_sequence, modifications, special_positions, raw_moltype, has_degenerate_bases, _ = parse_sequence(new_format_sequence, "RNA")
        
        print(f"\n3. 解析结果：")
        print(f"   裸序列（去除修饰和配体）：{naked_sequence}")
        print(f"   原始分子类型：{raw_moltype}")
        print(f"   是否包含简并碱基：{has_degenerate_bases}")
        
        print(f"\n4. 修饰信息：")
        for pos, mod, base in modifications:
            print(f"   位置 {pos}：修饰 {mod}，碱基 {base}")
        
        print(f"\n5. 特殊位置：")
        if special_positions:
            for pos in special_positions:
                print(f"   位置 {pos}")
        else:
            print("   无特殊位置")
        
        # 获取序列摘要
        sequence_summary = get_sequence_summary([(
            new_format_sequence,
            "RNA",
            "synthetic construct",
            None, [], [], [], None
        )])
        
        print(f"\n6. 序列摘要：")
        print(f"   总序列数：{sequence_summary['total_count']}")
        print(f"   DNA序列数：{sequence_summary['type_counts']['DNA']}")
        print(f"   RNA序列数：{sequence_summary['type_counts']['RNA']}")
        print(f"   氨基酸序列数：{sequence_summary['type_counts']['AA']}")
        print(f"   是否包含简并碱基：{sequence_summary['has_degenerate_bases']}")
        print(f"   是否包含被忽略的配体：{sequence_summary['has_ligand_ignored']}")
        
        print(f"\n7. 序列详情：")
        for detail in sequence_summary['details']:
            for key, value in detail.items():
                print(f"   {key}: {value}")
        
    except Exception as e:
        print(f"\n解析过程中出现错误：{str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_new_format_parsing()
