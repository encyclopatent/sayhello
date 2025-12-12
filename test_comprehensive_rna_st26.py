#!/usr/bin/env python3
# test_comprehensive_rna_st26.py
# 综合测试RNA序列处理，验证L96处理、U/T替换和N碱基替换功能

import os
import xml.etree.ElementTree as ET
from xml_generator import generate_xml, write_xml_to_file
from parser import parse_sequence

def test_comprehensive_rna_st26():
    """综合测试RNA序列处理，验证L96处理、U/T替换和N碱基替换功能"""
    print("=== 综合测试RNA序列处理（ST26标准） ===")
    
    # 测试1: 包含L96配体的RNA序列
    test_seq_with_l96 = "AmGmCmUmAmGmAfCmAfCfUmGmGmGmsAmsUfL96"
    print(f"\n测试1: 包含L96配体的RNA序列")
    print(f"测试序列: {test_seq_with_l96}")
    
    # 解析序列
    naked_sequence, modifications, special_positions, original_moltype, has_degenerate_bases, ligand_removed = parse_sequence(test_seq_with_l96, "RNA")
    print(f"  解析后的裸序列: {naked_sequence}")
    print(f"  L96配体是否被移除: {ligand_removed}")
    
    # 验证所有u都已替换为t
    if 'u' not in naked_sequence and 'U' not in naked_sequence:
        print("  ✅ ST26标准验证: RNA序列中的u已全部替换为t")
    else:
        print("  ❌ ST26标准验证: RNA序列中仍包含u")
    
    # 测试2: 包含N和多种修饰的RNA序列
    print(f"\n测试2: 包含N和多种修饰的RNA序列")
    
    # 创建测试数据
    sequences = [
        ('N', 'RNA', 'synthetic construct', 'other RNA', ['cmnm5u'], [], [], None),
        ('N', 'RNA', 'synthetic construct', 'other RNA', ['mam5u'], [], [], None),
        ('N', 'RNA', 'synthetic construct', 'other RNA', ['mcm5s2u'], [], [], None),
        ('AGCUAGCNAGCU', 'RNA', 'synthetic construct', 'other RNA', ['cmnm5u'], [], [], None),
        ('AGCUAGCNAGCUNAGCU', 'RNA', 'synthetic construct', 'other RNA', ['cmnm5u', 'mam5u'], [], [], None)
    ]
    
    basic_data = {
        'ApplicantFileReference': 'TEST_COMPREHENSIVE_RNA_ST26',
        'earliestpriorityIPOfficeCode': 'CN',
        'ApplicationNumberText': 'CN202312345678.9',
        'earliestpriorityFilingDate': '2023-01-01',
        'ApplicantName': '测试申请人',
        'ApplicantNameLatin': 'Test User',
        'InventorName': '测试发明人',
        'InventorNameLatin': 'Test Inventor',
        'InventionTitle': '测试发明'
    }
    
    # 生成XML
    output_folder = '.'
    root = generate_xml(sequences, basic_data, output_folder)
    xml_file = os.path.join(output_folder, 'TEST_COMPREHENSIVE_RNA_ST26.xml')
    write_xml_to_file(root, xml_file)
    
    # 验证生成的XML
    tree = ET.parse(xml_file)
    sequence_data_list = tree.findall('.//SequenceData')
    
    for i, sequence_data in enumerate(sequence_data_list):
        seq_id = sequence_data.get('sequenceIDNumber')
        insd_seq = sequence_data.find('INSDSeq')
        seq = insd_seq.find('INSDSeq_sequence').text
        moltype = insd_seq.find('INSDSeq_moltype').text
        
        print(f"\n  序列{seq_id} ({moltype}):")
        print(f"    原始序列: {sequences[i][0]}")
        print(f"    生成的XML序列: {seq}")
        
        # 验证所有u都已替换为t
        if 'u' not in seq and 'U' not in seq:
            print("    ✅ ST26标准验证: RNA序列中的u已全部替换为t")
        else:
            print("    ❌ ST26标准验证: RNA序列中仍包含u")
        
        # 验证N碱基替换
        if sequences[i][0].upper() == 'N' and seq.lower() in ['t', 'a', 'c', 'g']:
            print("    ✅ N碱基替换验证: N已被正确替换为对应的碱基")
        elif 'N' in sequences[i][0] and 'n' not in seq.lower():
            print("    ✅ N碱基替换验证: N已被正确替换为对应的碱基")
    
    # 清理测试文件
    if os.path.exists(xml_file):
        os.remove(xml_file)
    
    # 测试3: 新格式RNA序列
    print(f"\n测试3: 新格式RNA序列")
    test_new_format_seq = "(mG)(mG)(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)"
    print(f"测试序列: {test_new_format_seq}")
    
    # 解析序列
    naked_sequence, modifications, special_positions, original_moltype, has_degenerate_bases, ligand_removed = parse_sequence(test_new_format_seq, "RNA")
    print(f"  解析后的裸序列: {naked_sequence}")
    print(f"  L96配体是否被移除: {ligand_removed}")
    
    # 验证所有u都已替换为t
    if 'u' not in naked_sequence and 'U' not in naked_sequence:
        print("  ✅ ST26标准验证: RNA序列中的u已全部替换为t")
    else:
        print("  ❌ ST26标准验证: RNA序列中仍包含u")
    
    print("\n=== 综合测试完成 ===")

if __name__ == '__main__':
    test_comprehensive_rna_st26()
