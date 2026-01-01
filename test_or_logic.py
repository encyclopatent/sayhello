#!/usr/bin/env python3
# 测试包含"or"的freetext注释处理逻辑

import xml.etree.ElementTree as ET
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xml_generator import generate_xml

def test_or_logic():
    # 测试数据1: 简单的"a or b"格式
    test_data1 = {
        'ApplicantFileReference': 'TEST001',
        'ApplicationNumber': 'PCT/CN2023/100001',
        'ApplicationDate': '2023-01-01',
        'ApplicantName': '测试申请人',
        'ApplicantNameLatin': 'Test Applicant',
        'InventorName': '测试发明人',
        'InventorNameLatin': 'Test Inventor',
        'InventionTitle': '测试发明',
        'PriorityApplicationNumber': '',
        'PriorityDate': ''
    }
    
    # 测试序列1: DNA序列，包含"a or b"格式的注释
    test_sequence1 = [
        ('ATGCNTAA', 'DNA', 'synthetic construct', 'other DNA', ['a or b'], [], [], None)
    ]
    
    # 测试数据2: 复杂的"cmnm5s2u, mam5u, mcm5s2u, or p"格式
    test_data2 = {
        'ApplicantFileReference': 'TEST002',
        'ApplicationNumber': 'PCT/CN2023/100002',
        'ApplicationDate': '2023-01-01',
        'ApplicantName': '测试申请人',
        'ApplicantNameLatin': 'Test Applicant',
        'InventorName': '测试发明人',
        'InventorNameLatin': 'Test Inventor',
        'InventionTitle': '测试发明',
        'PriorityApplicationNumber': '',
        'PriorityDate': ''
    }
    
    # 测试序列2: RNA序列，包含复杂的"or"格式注释
    test_sequence2 = [
        ('AUGCNUAA', 'RNA', 'synthetic construct', 'other RNA', ['cmnm5s2u, mam5u, mcm5s2u, or p'], [], [], None)
    ]
    
    print("=== 测试1: 简单的'a or b'格式 ===")
    root1, reminders1 = generate_xml(test_sequence1, test_data1, ".")
    
    # 打印序列内容
    seq_element1 = root1.find('.//SequenceData/INSDSeq/INSDSeq_sequence')
    print(f"处理后的序列: {seq_element1.text}")
    
    # 检查是否添加了两个特征
    features1 = root1.findall('.//SequenceData/INSDSeq/INSDSeq_feature-table/INSDFeature')
    print(f"总特征数: {len(features1)}")
    
    for i, feature in enumerate(features1):
        feature_key = feature.find('INSDFeature_key').text
        print(f"特征{i+1}类型: {feature_key}")
        if feature_key in ['misc_difference', 'modified_base']:
            location = feature.find('INSDFeature_location').text
            
            # 简单方式查找mod_base和note
            mod_base_value = "None"
            note_value = "None"
            qualifiers = feature.find('INSDFeature_quals')
            if qualifiers:
                for qual in qualifiers.findall('INSDQualifier'):
                    name = qual.find('INSDQualifier_name')
                    value = qual.find('INSDQualifier_value')
                    if name is not None and value is not None:
                        if name.text == "mod_base":
                            mod_base_value = value.text
                        elif name.text == "note":
                            note_value = value.text
            
            print(f"  位置: {location}, mod_base: {mod_base_value}, note: {note_value}")
    
    print("\n=== 测试2: 复杂的'cmnm5s2u, mam5u, mcm5s2u, or p'格式 ===")
    root2, reminders2 = generate_xml(test_sequence2, test_data2, ".")
    
    # 打印序列内容
    seq_element2 = root2.find('.//SequenceData/INSDSeq/INSDSeq_sequence')
    print(f"处理后的序列: {seq_element2.text}")
    
    # 检查是否添加了两个特征
    features2 = root2.findall('.//SequenceData/INSDSeq/INSDSeq_feature-table/INSDFeature')
    print(f"总特征数: {len(features2)}")
    
    for i, feature in enumerate(features2):
        feature_key = feature.find('INSDFeature_key').text
        print(f"特征{i+1}类型: {feature_key}")
        if feature_key in ['misc_difference', 'modified_base']:
            location = feature.find('INSDFeature_location').text
            
            # 简单方式查找mod_base和note
            mod_base_value = "None"
            note_value = "None"
            qualifiers = feature.find('INSDFeature_quals')
            if qualifiers:
                for qual in qualifiers.findall('INSDQualifier'):
                    name = qual.find('INSDQualifier_name')
                    value = qual.find('INSDQualifier_value')
                    if name is not None and value is not None:
                        if name.text == "mod_base":
                            mod_base_value = value.text
                        elif name.text == "note":
                            note_value = value.text
            
            print(f"  位置: {location}, mod_base: {mod_base_value}, note: {note_value}")
    
    # 检查N是否被替换
    print("\n=== 检查N替换情况 ===")
    print(f"测试1序列中的N是否被替换: {'n' not in seq_element1.text}")
    print(f"测试2序列中的N是否被替换: {'n' not in seq_element2.text}")

if __name__ == "__main__":
    test_or_logic()
