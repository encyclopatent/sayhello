#!/usr/bin/env python3
# test_xml_generation.py
# 测试XML生成的正确性，特别是修饰碱基的mod_base值

from parser import convert_new_format_to_old, parse_sequence
from xml_generator import generate_xml, write_xml_to_file
import xml.etree.ElementTree as ET

# 创建测试用的基本数据
basic_data = {
    'ApplicantFileReference': 'TEST_REF',
    'ApplicantName': '测试申请人',
    'ApplicantNameLatin': 'Test Applicant',
    'InventorName': '测试发明人',
    'InventorNameLatin': 'Test Inventor',
    'InventionTitle': '测试发明',
    'earliestpriorityIPOfficeCode': 'CN',
    'ApplicationNumberText': 'CN202312345678.9',
    'earliestpriorityFilingDate': '2023-01-01'
}

# 测试用的新格式序列
test_sequence = "(VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)"

# 创建测试序列数据
sequences = [(test_sequence, "RNA", "synthetic construct", "other RNA", [], [], [], None)]

# 生成XML
root = generate_xml(sequences, basic_data, ".")

# 验证XML中的修饰碱基类型
print("验证XML中的修饰碱基类型：")
for feature in root.findall(".//INSDFeature"):
    feature_key = feature.findtext("INSDFeature_key")
    if feature_key == "modified_base":
        location = feature.findtext("INSDFeature_location")
        mod_base = feature.findtext(".//INSDQualifier[INSDQualifier_name='mod_base']/INSDQualifier_value")
        print(f"位置 {location}: mod_base = {mod_base}")
        
        # 检查是否有使用OTHER类型
        if mod_base == "OTHER":
            print(f"  ❌ 错误：位置 {location} 使用了OTHER类型")
        # 检查修饰符是否在前，碱基在后
        elif len(mod_base) >= 2 and mod_base[0] in ['m', 'f', 'e', 'p']:
            print(f"  ✅ 正确：位置 {location} 使用了正确的修饰类型 {mod_base}")
        else:
            print(f"  ❌ 错误：位置 {location} 的修饰类型格式不正确 {mod_base}")

# 将XML写入文件进行手动验证
xml_file = "./test_output.xml"
write_xml_to_file(root, xml_file)
print(f"\nXML文件已生成：{xml_file}")
