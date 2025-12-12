#!/usr/bin/env python3
# 测试XML生成程序是否使用裸序列长度

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import parse_sequence
from xml_generator import generate_xml

# 测试序列：带修饰符的序列
# 原始序列：AmGfU (长度5)
# 裸序列：AGT (长度3) - 注意U会被替换为T

test_sequence = "AmGfU"
moltype = "RNA"

# 解析序列获取裸序列
naked_sequence, modifications, special_positions, original_moltype, _, _ = parse_sequence(test_sequence, moltype)
print(f"测试序列: {test_sequence}")
print(f"原始序列长度: {len(test_sequence)}")
print(f"裸序列: {naked_sequence}")
print(f"裸序列长度: {len(naked_sequence)}")
print(f"修饰符数量: {len(modifications)}")
print(f"修饰符: {modifications}")

# 准备生成XML所需的数据
basic_data = {
    'ApplicantFileReference': 'TEST001',
    'ApplicantName': '测试申请人',
    'ApplicantNameLatin': 'Test Applicant',
    'InventorName': '测试发明人',
    'InventorNameLatin': 'Test Inventor',
    'InventionTitle': '测试发明',
}

sequences = [(test_sequence, moltype, 'synthetic construct', 'other RNA', [], [], [], None)]

# 生成XML
root = generate_xml(sequences, basic_data, '.')

# 查找并打印XML中的序列长度信息
import xml.etree.ElementTree as ET
for sequence_data in root.findall('SequenceData'):
    insd_seq = sequence_data.find('INSDSeq')
    seq_length = insd_seq.find('INSDSeq_length').text
    seq_moltype = insd_seq.find('INSDSeq_moltype').text
    seq_sequence = insd_seq.find('INSDSeq_sequence').text
    
    print(f"\nXML中的序列信息:")
    print(f"序列长度: {seq_length} (应为裸序列长度: {len(naked_sequence)})")
    print(f"分子类型: {seq_moltype}")
    print(f"序列内容: {seq_sequence}")
    
    # 检查source特征的位置
    feature_table = insd_seq.find('INSDSeq_feature-table')
    source_feature = feature_table.find(".//INSDFeature[INSDFeature_key='source']")
    source_location = source_feature.find('INSDFeature_location').text
    print(f"Source特征位置: {source_location} (应为1..{len(naked_sequence)})")

# 验证修复是否成功
if seq_length == str(len(naked_sequence)):
    print("\n✅ 修复成功！XML中使用的是裸序列长度。")
else:
    print("\n❌ 修复失败！XML中仍然使用的是原始序列长度。")
