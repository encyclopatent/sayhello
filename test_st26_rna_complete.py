#!/usr/bin/env python3
# test_st26_rna_complete.py
# 测试完整的RNA序列处理流程，验证ST26标准的u→t替换

import os
import xml.etree.ElementTree as ET
from xml_generator import generate_xml, write_xml_to_file
from parser import parse_sequence

def test_st26_rna_complete():
    """测试完整的RNA序列处理流程，验证ST26标准的u→t替换"""
    print("=== 测试完整的RNA序列处理流程（ST26标准） ===")
    
    # 测试1: 包含多个u的RNA序列
    test_seq = "AmGmCmUmAmGmAfCmAfCfUmGmGmGmsAmsUf"
    print(f"\n测试序列: {test_seq}")
    
    # 步骤1: 解析序列
    naked_sequence, modifications, special_positions, original_moltype, has_degenerate_bases, ligand_removed = parse_sequence(test_seq, "RNA")
    print(f"  解析后的裸序列: {naked_sequence}")
    
    # 验证所有u都已替换为t
    if 'u' not in naked_sequence and 'U' not in naked_sequence:
        print("  ✅ ST26标准验证: RNA序列中的u已全部替换为t")
    else:
        print("  ❌ ST26标准验证: RNA序列中仍包含u")
    
    # 测试2: 包含N和uridine修饰的RNA序列
    print(f"\n测试序列: N (RNA, cmnm5u)")
    
    # 创建测试数据
    sequences = [
        ('N', 'RNA', 'synthetic construct', 'other RNA', ['cmnm5u'], [], [], None)
    ]
    
    basic_data = {
        'ApplicantFileReference': 'TEST_ST26_RNA',
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
    xml_file = os.path.join(output_folder, 'TEST_ST26_RNA.xml')
    write_xml_to_file(root, xml_file)
    
    # 验证生成的XML
    tree = ET.parse(xml_file)
    sequence_data = tree.find('.//SequenceData')
    insd_seq = sequence_data.find('INSDSeq')
    seq = insd_seq.find('INSDSeq_sequence').text
    
    print(f"  生成的XML序列: {seq}")
    if seq == 't':
        print("  ✅ ST26标准验证: RNA序列中的uridine修饰已替换为t")
    else:
        print("  ❌ ST26标准验证: RNA序列中的uridine修饰未正确替换")
    
    # 清理测试文件
    if os.path.exists(xml_file):
        os.remove(xml_file)
    
    print("\n=== 测试完成 ===")

if __name__ == '__main__':
    test_st26_rna_complete()
