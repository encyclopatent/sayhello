#!/usr/bin/env python3
"""
测试新格式序列的转换和解析
用于验证新格式是否被正确识别和转换为旧格式
并检查生成的XML是否符合WIPO工具要求
"""

import sys
import os
from parser import convert_new_format_to_old, parse_sequence, get_sequence_summary
from xml_generator import generate_xml

def test_new_format_detection():
    """测试新格式检测功能"""
    print("=== 测试新格式检测 ===")
    
    test_cases = [
        # 有效的新格式序列
        "(VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)",
        "(Pv)(mG)*(mG)",
        "(pv)(mG)",
        "(VP)(mG)",
        "(VP)(mG)(mU)",
        "(VP)(mG)*(mU)*(mC)",
        
        # 无效的新格式序列（不转换）
        "VPmG*s*mG*s*mUmU",  # 旧格式
        "(VPmG)",  # 括号内包含多个元素但没有*修饰符
        "VP(mG)*",  # 开头不是括号
        "(VP)(mG)*abc",  # 包含其他字符
        "(VP)(mG)",  # 有效的新格式
    ]
    
    for seq in test_cases:
        result = convert_new_format_to_old(seq)
        is_new_format = result != seq
        print(f"原始序列: {seq}")
        print(f"转换结果: {result}")
        print(f"是否为新格式: {is_new_format}")
        print()

def test_new_format_conversion():
    """测试新格式转换为旧格式的准确性"""
    print("=== 测试新格式转换准确性 ===")
    
    test_cases = [
        ("(VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)", 
         "VPmGsmGsmUmUfGmGfAmUfUfUfUmUfCmUmUmGmCmUmAmUmGL96"),
        ("(Pv)(mG)*(mG)", "PvmGsmGs"),
        ("(pv)(mG)", "pvmG"),
        ("(VP)(mG)(mU)", "VPmGmU"),
        ("(VP)(mG)*(mU)*(mC)", "VPmGsmUsCmC"),
        ("(VP)(mG)(fU)*(mC)(L96)", "VPmGfUsCmCL96"),
    ]
    
    for input_seq, expected in test_cases:
        result = convert_new_format_to_old(input_seq)
        print(f"输入序列: {input_seq}")
        print(f"转换结果: {result}")
        print(f"预期结果: {expected}")
        print(f"转换正确: {result == expected}")
        print()

def test_sequence_parsing():
    """测试新格式序列的解析"""
    print("=== 测试新格式序列解析 ===")
    
    test_seq = "(VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)"
    print(f"原始新格式序列: {test_seq}")
    
    # 第一步：转换为旧格式
    old_format_seq = convert_new_format_to_old(test_seq)
    print(f"转换后旧格式: {old_format_seq}")
    
    # 第二步：解析序列
    naked_sequence, modifications, special_positions, raw_moltype, has_degenerate_bases, _ = parse_sequence(test_seq, "RNA")
    
    print(f"裸序列: {naked_sequence}")
    print(f"修饰信息: {modifications}")
    print(f"特殊位置: {special_positions}")
    print(f"分子类型: {raw_moltype}")
    print(f"是否有简并碱基: {has_degenerate_bases}")
    print()
    
    # 检查PV修饰是否被正确统一
    pv_mods = [mod for pos, mod, base in modifications if mod == 'pv']
    print(f"PV修饰数量: {len(pv_mods)}")
    if pv_mods:
        print("PV修饰被正确统一为'pv'格式")
    
    # 检查L96配体是否被正确处理
    ligand_mods = [mod for pos, mod, base in modifications if mod == 'ligand_ignored']
    print(f"配体忽略标记数量: {len(ligand_mods)}")
    if ligand_mods:
        print("L96配体被正确忽略并标记")
    
    print()

def test_xml_generation():
    """测试生成的XML是否符合WIPO工具要求"""
    print("=== 测试XML生成 ===")
    
    # 准备测试数据
    test_seq = "(VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)"
    
    # 模拟序列数据
    sequences = [(test_seq, "RNA", "synthetic construct", "other RNA", [], [], [], None)]
    
    # 模拟基本数据
    basic_data = {
        'ApplicantFileReference': 'TEST123',
        'earliestpriorityIPOfficeCode': 'CN',
        'ApplicationNumberText': 'CN202312345678.9',
        'earliestpriorityFilingDate': '2023-01-01',
        'ApplicantName': '测试申请人',
        'ApplicantNameLatin': 'Test Applicant',
        'InventorName': '测试发明人',
        'InventorNameLatin': 'Test Inventor',
        'InventionTitle': '测试发明',
    }
    
    try:
        # 生成XML
        root = generate_xml(sequences, basic_data, './')
        print("XML生成成功")
        
        # 检查PV修饰的碱基是否正确
        import xml.etree.ElementTree as ET
        
        # 查找所有modified_base特征
        modified_bases = []
        for feature in root.findall('.//INSDFeature'):
            key = feature.find('INSDFeature_key').text
            if key == 'modified_base':
                location = feature.find('INSDFeature_location').text
                for qual in feature.findall('.//INSDQualifier'):
                    qual_name = qual.find('INSDQualifier_name').text
                    qual_value = qual.find('INSDQualifier_value').text
                    if qual_name == 'mod_base':
                        modified_bases.append((location, qual_value))
                    elif qual_name == 'note' and '5prime-vinylphosphonate' in qual_value:
                        print(f"找到PV修饰: 位置{location}, 注释{qual_value}")
        
        print("所有修饰碱基:")
        for location, base in modified_bases:
            print(f"位置{location}: {base}")
            
        # 检查是否有'OTHER'碱基的修饰
        other_bases = [base for location, base in modified_bases if base == 'OTHER']
        print(f"\nOTHER修饰碱基数量: {len(other_bases)}")
        if not other_bases:
            print("✓ 没有OTHER修饰碱基，符合WIPO工具要求")
        else:
            print("✗ 存在OTHER修饰碱基，可能导致WIPO工具报错")
            
    except Exception as e:
        print(f"XML生成失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def test_whole_pipeline():
    """测试完整的处理流程"""
    print("=== 测试完整处理流程 ===")
    
    test_seq = "(VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)"
    print(f"输入序列: {test_seq}")
    
    # 1. 检查是否为新格式并转换
    is_new_format = test_seq.startswith('(') and '(' in test_seq[1:]
    print(f"是否为新格式: {is_new_format}")
    
    old_format = convert_new_format_to_old(test_seq)
    print(f"转换为旧格式: {old_format}")
    
    # 2. 解析序列
    naked_sequence, modifications, special_positions, raw_moltype, has_degenerate_bases, _ = parse_sequence(test_seq, "RNA")
    
    print(f"\n解析结果:")
    print(f"裸序列: {naked_sequence}")
    print(f"裸序列长度: {len(naked_sequence)}")
    print(f"修饰信息数量: {len(modifications)}")
    
    print(f"\n修饰详情:")
    for pos, mod, base in modifications:
        if mod != 'ligand_ignored':
            print(f"位置: {pos}, 修饰: {mod}, 碱基: {base}")
        else:
            print(f"位置: {pos}, 配体被忽略: {base}")
    
    # 3. 生成序列摘要
    sequences = [(test_seq, "RNA", "synthetic construct", "other RNA", [], [], [], None)]
    summary = get_sequence_summary(sequences)
    
    print(f"\n序列摘要:")
    print(f"序列类型: {summary['details'][0]['type']}")
    print(f"是否有简并碱基: {summary['has_degenerate_bases']}")
    print(f"是否有配体被忽略: {summary['has_ligand_ignored']}")
    print(f"修饰和特殊说明: {summary['details'][0]['modification_special_notes']}")
    
    print()

def main():
    """主函数"""
    print("开始新格式序列验证测试...\n")
    
    test_new_format_detection()
    test_new_format_conversion()
    test_sequence_parsing()
    test_xml_generation()
    test_whole_pipeline()
    
    print("所有测试完成！")

if __name__ == "__main__":
    main()
