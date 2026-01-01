# test_specific_or_case.py
import xml.etree.ElementTree as ET
import os
from xml_generator import generate_xml, write_xml_to_file

# 测试数据准备
test_sequence = "ATGCnTAA"
test_data = {
    'ApplicantFileReference': 'TEST_OR_CASE',
    'earliestpriorityIPOfficeCode': 'CN',
    'ApplicationNumberText': '2023123456',
    'earliestpriorityFilingDate': '2023-01-01',
    'ApplicantName': 'Test Applicant',
    'ApplicantNameLatin': 'Test Applicant',
    'InventorName': 'Test Inventor',
    'InventorNameLatin': 'Test Inventor',
    'InventionTitle': 'Test Sequence'
}

# 用户提供的freetext示例
test_freetext = "m3c, m4c, N4, N4-dimethylcytosine, or N4-cyclopropylcytosine"

# 构建测试序列数据结构
test_sequences = [
    (test_sequence, 'DNA', 'test organism', 'other DNA', [test_freetext], None, None, None)
]

# 生成XML
xml_root, reminders = generate_xml(test_sequences, test_data, ".")

# 保存XML到文件
xml_file = "test_or_case.xml"
write_xml_to_file(xml_root, xml_file)

# 解析生成的XML以验证结果
tree = ET.parse(xml_file)
root = tree.getroot()

# 找到序列元素
seq_element = root.find('.//INSDSeq_sequence')
print(f"生成的序列: {seq_element.text}")
print(f"序列中的N是否被替换: {'n' in seq_element.text}")

# 找到所有特征
features = root.findall('.//INSDFeature')
print(f"\n总特征数: {len(features)}")

# 查找misc_difference和modified_base特征
misc_features = [f for f in features if f.find('INSDFeature_key').text == 'misc_difference']
modified_features = [f for f in features if f.find('INSDFeature_key').text == 'modified_base']

print(f"misc_difference特征数: {len(misc_features)}")
print(f"modified_base特征数: {len(modified_features)}")

# 检查misc_difference特征的note
if misc_features:
    misc_qualifiers = misc_features[0].find('INSDFeature_quals')
    for qual in misc_qualifiers.findall('INSDQualifier'):
        name = qual.find('INSDQualifier_name').text
        value = qual.find('INSDQualifier_value').text
        if name == 'note':
            print(f"misc_difference的note内容: {value}")
            print(f"note包含完整freetext: {'or' in value}")

# 检查modified_base特征
if modified_features:
    mod_qualifiers = modified_features[0].find('INSDFeature_quals')
    mod_base_value = "None"
    note_value = "None"
    for qual in mod_qualifiers.findall('INSDQualifier'):
        name = qual.find('INSDQualifier_name').text
        value = qual.find('INSDQualifier_value').text
        if name == 'mod_base':
            mod_base_value = value
        elif name == 'note':
            note_value = value
    print(f"\nmodified_base的mod_base值: {mod_base_value}")
    print(f"modified_base的note内容: {note_value}")
    print(f"note包含完整freetext: {'or' in note_value}")

# 清理测试文件
os.remove(xml_file)
print(f"\n测试文件已清理: {xml_file}")
