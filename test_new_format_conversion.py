#!/usr/bin/env python3
# test_new_format_conversion.py
# 测试新格式序列转换逻辑

from parser import convert_new_format_to_old, parse_sequence
from xml_generator import generate_xml

def test_new_format_conversion():
    """测试新格式序列转换为旧格式"""
    
    # 测试用例1: 基本新格式序列
    new_format_seq1 = "(VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)"
    print("测试用例1: 基本新格式序列")
    print(f"原始序列: {new_format_seq1}")
    
    # 转换为旧格式
    old_format_seq1 = convert_new_format_to_old(new_format_seq1)
    print(f"转换后旧格式: {old_format_seq1}")
    
    # 解析序列
    try:
        naked_seq, mods, special_pos, _, _, _ = parse_sequence(old_format_seq1, "RNA")
        print(f"裸序列: {naked_seq}")
        print(f"修饰信息: {mods}")
        print("✓ 解析成功")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    print("-" * 50)
    
    # 测试用例2: 带连字符的PV修饰
    new_format_seq2 = "(Pv-)(mG)*(mG)"
    print("测试用例2: 带连字符的PV修饰")
    print(f"原始序列: {new_format_seq2}")
    
    old_format_seq2 = convert_new_format_to_old(new_format_seq2)
    print(f"转换后旧格式: {old_format_seq2}")
    
    try:
        naked_seq, mods, special_pos, _, _, _ = parse_sequence(old_format_seq2, "RNA")
        print(f"裸序列: {naked_seq}")
        print(f"修饰信息: {mods}")
        print("✓ 解析成功")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    print("-" * 50)
    
    # 测试用例3: VP修饰在中间
    new_format_seq3 = "(mG)*(VP)*(mG)"
    print("测试用例3: VP修饰在中间")
    print(f"原始序列: {new_format_seq3}")
    
    old_format_seq3 = convert_new_format_to_old(new_format_seq3)
    print(f"转换后旧格式: {old_format_seq3}")
    
    try:
        naked_seq, mods, special_pos, _, _, _ = parse_sequence(old_format_seq3, "RNA")
        print(f"裸序列: {naked_seq}")
        print(f"修饰信息: {mods}")
        print("✓ 解析成功")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    print("-" * 50)
    
    # 测试用例4: 不带*修饰符
    new_format_seq4 = "(VP)(mG)(mG)(mU)"
    print("测试用例4: 不带*修饰符")
    print(f"原始序列: {new_format_seq4}")
    
    old_format_seq4 = convert_new_format_to_old(new_format_seq4)
    print(f"转换后旧格式: {old_format_seq4}")
    
    try:
        naked_seq, mods, special_pos, _, _, _ = parse_sequence(old_format_seq4, "RNA")
        print(f"裸序列: {naked_seq}")
        print(f"修饰信息: {mods}")
        print("✓ 解析成功")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    print("-" * 50)
    
    # 测试用例5: 不是新格式的序列
    new_format_seq5 = "VPmGs*mG"
    print("测试用例5: 不是新格式的序列")
    print(f"原始序列: {new_format_seq5}")
    
    old_format_seq5 = convert_new_format_to_old(new_format_seq5)
    print(f"转换后旧格式: {old_format_seq5}")
    
    try:
        naked_seq, mods, special_pos, _, _, _ = parse_sequence(old_format_seq5, "RNA")
        print(f"裸序列: {naked_seq}")
        print(f"修饰信息: {mods}")
        print("✓ 解析成功")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    print("-" * 50)

if __name__ == "__main__":
    test_new_format_conversion()
