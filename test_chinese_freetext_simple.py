#!/usr/bin/env python3
"""
简单测试中文freetext处理功能
"""
import sys

# 添加当前目录到Python路径
sys.path.append('/Users/zhaoyongjiang/Downloads/SAYHELLO')

from xml_generator import generate_xml

def test_chinese_freetext_simple():
    """简单测试中文freetext处理功能"""
    print("=== 简单测试中文freetext处理功能 ===")
    
    # 测试数据
    basic_data = {
        'ApplicantFileReference': 'TEST_CHINESE',
        'ApplicantName': '测试有限公司',
        'ApplicantNameLatin': 'TEST Technology Co., Ltd.',
        'InventorName': '莫某某',
        'InventorNameLatin': 'morgen',
        'InventionTitle': '测试分子'
    }
    
    # 测试用例
    test_sequences = [
        ('ACGNT', 'DNA', 'synthetic construct', 'other DNA', 
         ['any base 任意碱基'], [], [], False, None, 1)
    ]
    
    # 生成XML
    root, reminders = generate_xml(test_sequences, basic_data, '.')
    
    # 将XML转换为字符串
    import xml.etree.ElementTree as ET
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    
    print("\n生成的XML:")
    print(xml_str)
    
    # 验证XML中是否包含预期的元素和值
    expected_elements = [
        '<INSDQualifier_name>note</INSDQualifier_name>',
        '<INSDQualifier_value>any base</INSDQualifier_value>',
        '<NonEnglishQualifier_value>任意碱基</NonEnglishQualifier_value>'
    ]
    
    print("\n验证结果:")
    all_passed = True
    for expected in expected_elements:
        if expected in xml_str:
            print(f"  ✅ 包含预期元素: {expected}")
        else:
            print(f"  ❌ 未找到预期元素: {expected}")
            all_passed = False
    
    if all_passed:
        print("\n✅ 所有验证通过！功能已正确实现。")
        return True
    else:
        print("\n❌ 部分验证失败！")
        return False

def test_user_example():
    """测试用户提供的示例"""
    print("\n=== 测试用户提供的示例 ===")
    
    # 测试数据
    basic_data = {
        'ApplicantFileReference': 'TEST_EXAMPLE',
        'ApplicantName': '测试有限公司',
        'ApplicantNameLatin': 'TEST Technology Co., Ltd.',
        'InventorName': '莫某某',
        'InventorNameLatin': 'morgen',
        'InventionTitle': '测试分子'
    }
    
    # 测试序列：包含一个N，会生成modified_base特征
    test_sequences = [
        ('ACGUACGNUACGU', 'RNA', 'synthetic construct', 'other RNA', 
         ['any base 任意碱基'], [], [], False, None, 1)
    ]
    
    # 生成XML
    root, reminders = generate_xml(test_sequences, basic_data, '.')
    
    # 将XML转换为字符串
    import xml.etree.ElementTree as ET
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    
    print("\n生成的XML:")
    print(xml_str)
    
    # 验证XML中是否包含预期的结构
    expected_structure = [
        '<INSDFeature_key>modified_base</INSDFeature_key>',
        '<INSDFeature_location>8</INSDFeature_location>',  # 注意：索引从1开始，N在第8位
        '<INSDQualifier_value>OTHER</INSDQualifier_value>',
        '<INSDQualifier_name>note</INSDQualifier_name>',
        '<INSDQualifier_value>any base</INSDQualifier_value>',
        '<NonEnglishQualifier_value>任意碱基</NonEnglishQualifier_value>'
    ]
    
    print("\n验证结果:")
    all_passed = True
    for expected in expected_structure:
        if expected in xml_str:
            print(f"  ✅ 包含预期结构: {expected}")
        else:
            print(f"  ❌ 未找到预期结构: {expected}")
            all_passed = False
    
    if all_passed:
        print("\n✅ 所有验证通过！功能已正确实现。")
        return True
    else:
        print("\n❌ 部分验证失败！")
        return False

if __name__ == "__main__":
    # 运行简单测试
    test1_passed = test_chinese_freetext_simple()
    test2_passed = test_user_example()
    
    # 总体结果
    print("\n=== 总体测试结果 ===")
    if test1_passed and test2_passed:
        print("✅ 所有测试通过！中文freetext处理功能已正确实现。")
        sys.exit(0)
    else:
        print("❌ 部分测试失败！")
        sys.exit(1)
