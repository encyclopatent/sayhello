#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
直接测试L96提醒和默认值提醒功能，不通过Excel文件
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import parse_sequence
from xml_generator import generate_xml

def test_l96_reminder():
    """测试L96配体移除提醒功能"""
    print("=== 测试L96配体移除提醒功能 ===")
    
    # 测试用例：旧格式L96
    old_format_seq = "AmGmCmUmAmGL96"
    print(f"输入序列: {old_format_seq}")
    naked_sequence, modifications, special_positions, raw_moltype, has_degenerate_bases, ligand_removed = parse_sequence(old_format_seq, "RNA")
    print(f"解析结果: {naked_sequence}")
    print(f"是否移除L96: {ligand_removed}")
    print()
    
    # 测试用例：新格式L96
    new_format_seq = "(mG)(mG)(mU)(mU)(fG)(mG)(L96)"
    print(f"输入序列: {new_format_seq}")
    naked_sequence, modifications, special_positions, raw_moltype, has_degenerate_bases, ligand_removed = parse_sequence(new_format_seq, "RNA")
    print(f"解析结果: {naked_sequence}")
    print(f"是否移除L96: {ligand_removed}")
    print()

def test_default_reminder():
    """测试默认值设置提醒功能"""
    print("=== 测试默认值设置提醒功能 ===")
    
    # 创建测试序列数据
    sequences = [
        ("AmGmCmUmAmGL96", None, None, None, [], [], [], None),  # 全部使用默认值
        ("AmGmCmUmAmG", "RNA", "Homo sapiens", "other RNA", [], [], [], None),  # 全部指定值
    ]
    
    # 创建基本数据
    basic_data = {
        "ApplicantFileReference": "TEST-2023-001",
        "earliestpriorityIPOfficeCode": "CN",
        "ApplicationNumberText": "CN20230000001",
        "earliestpriorityFilingDate": "2023-01-01",
        "ApplicantName": "测试申请人",
        "ApplicantNameLatin": "Test Applicant",
        "InventorName": "测试发明人",
        "InventorNameLatin": "Test Inventor",
        "InventionTitle": "测试发明"
    }
    
    # 生成XML并获取提醒
    xml_root, reminders = generate_xml(sequences, basic_data, ".")
    
    # 输出提醒信息
    if reminders:
        print("生成的提醒信息:")
        for reminder in reminders:
            print(f"  {reminder}")
    else:
        print("没有生成提醒信息")

if __name__ == "__main__":
    test_l96_reminder()
    test_default_reminder()