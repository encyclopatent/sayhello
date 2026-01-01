#!/usr/bin/env python3
"""
测试特定场景：当优先权信息为空时，其他信息仍然生成
"""
import xml.etree.ElementTree as ET
import sys

# 添加当前目录到Python路径
sys.path.append('/Users/zhaoyongjiang/Downloads/SAYHELLO')

from xml_generator import generate_xml

def test_specific_scenario():
    """测试用户提到的具体场景"""
    print("=== 测试用户提到的场景 ===")
    
    # 测试数据：优先权信息为空，但其他信息完整
    basic_data = {
        'ApplicantFileReference': 'TEST123',
        'earliestpriorityIPOfficeCode': '',
        'ApplicationNumberText': '',
        'earliestpriorityFilingDate': '',
        'ApplicantName': '测试有限公司',
        'ApplicantNameLatin': 'TEST Technology Co., Ltd.',
        'InventorName': '莫某某',
        'InventorNameLatin': 'morgen',
        'InventionTitle': '测试分子'
    }
    
    # 测试序列数据
    test_sequences = [
        ("ACGU", "RNA", "synthetic construct", "other RNA", [], [], [], False, None, 1)
    ]
    
    # 生成XML
    root, reminders = generate_xml(test_sequences, basic_data, '.')
    
    # 将XML转换为字符串，便于查看
    xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
    
    # 美化XML输出，便于阅读
    def prettify_xml(xml_string):
        """美化XML字符串"""
        import xml.dom.minidom
        dom = xml.dom.minidom.parseString(xml_string)
        return dom.toprettyxml(indent=" ")
    
    print("\n生成的XML:")
    print(prettify_xml(xml_str))
    
    # 检查关键元素是否存在
    expected_elements = [
        'ApplicantFileReference',
        'ApplicantName',
        'ApplicantNameLatin',
        'InventorName',
        'InventorNameLatin',
        'InventionTitle'
    ]
    
    missing_elements = []
    for element_name in expected_elements:
        if root.find(element_name) is None:
            missing_elements.append(element_name)
    
    # 检查优先权信息是否不存在
    priority_element = root.find('EarliestPriorityApplicationIdentification')
    if priority_element is not None:
        print("❌ 错误：优先权信息应该不存在，但实际存在")
    else:
        print("✅ 正确：优先权信息不存在")
    
    # 检查其他信息是否存在
    if missing_elements:
        print(f"❌ 错误：以下元素应该存在但实际不存在：{missing_elements}")
        return False
    else:
        print(f"✅ 正确：所有预期元素都存在")
        return True

if __name__ == "__main__":
    success = test_specific_scenario()
    sys.exit(0 if success else 1)
