#!/usr/bin/env python3
"""
测试脚本：验证XML生成时是否正确处理空值字段
"""
import xml.etree.ElementTree as ET
import os
import sys

# 添加当前目录到Python路径
sys.path.append('/Users/zhaoyongjiang/Downloads/SAYHELLO')

from xml_generator import generate_xml

def test_empty_fields():
    """测试空值字段是否正确处理"""
    # 测试数据1：所有字段都为空
    basic_data_empty = {
        'ApplicantFileReference': 'TEST001',
        'earliestpriorityIPOfficeCode': '',
        'ApplicationNumberText': '',
        'earliestpriorityFilingDate': '',
        'ApplicantName': '',
        'ApplicantNameLatin': '',
        'InventorName': 'Test Inventor',
        'InventorNameLatin': 'Test Inventor',
        'InventionTitle': 'Test Invention'
    }
    
    # 测试数据2：只有ApplicantName为空
    basic_data_applicant_empty = {
        'ApplicantFileReference': 'TEST002',
        'earliestpriorityIPOfficeCode': 'CN',
        'ApplicationNumberText': '202312345678.9',
        'earliestpriorityFilingDate': '2023-01-01',
        'ApplicantName': '',
        'ApplicantNameLatin': '',
        'InventorName': 'Test Inventor',
        'InventorNameLatin': 'Test Inventor',
        'InventionTitle': 'Test Invention'
    }
    
    # 测试数据3：只有ApplicationNumberText和earliestpriorityFilingDate为空
    basic_data_priority_empty = {
        'ApplicantFileReference': 'TEST003',
        'earliestpriorityIPOfficeCode': 'CN',
        'ApplicationNumberText': '',
        'earliestpriorityFilingDate': '',
        'ApplicantName': 'Test Applicant',
        'ApplicantNameLatin': 'Test Applicant',
        'InventorName': 'Test Inventor',
        'InventorNameLatin': 'Test Inventor',
        'InventionTitle': 'Test Invention'
    }
    
    # 测试数据4：所有字段都有值
    basic_data_full = {
        'ApplicantFileReference': 'TEST004',
        'earliestpriorityIPOfficeCode': 'CN',
        'ApplicationNumberText': '202312345678.9',
        'earliestpriorityFilingDate': '2023-01-01',
        'ApplicantName': 'Test Applicant',
        'ApplicantNameLatin': 'Test Applicant',
        'InventorName': 'Test Inventor',
        'InventorNameLatin': 'Test Inventor',
        'InventionTitle': 'Test Invention'
    }
    
    # 测试序列数据
    test_sequences = [
        ("ACGU", "RNA", "synthetic construct", "other RNA", [], [], [], False, None, 1)
    ]
    
    test_cases = [
        ("所有字段为空", basic_data_empty, {
            'EarliestPriorityApplicationIdentification': False,
            'ApplicationNumberText': False,
            'FilingDate': False,
            'ApplicantName': False
        }),
        ("ApplicantName为空", basic_data_applicant_empty, {
            'EarliestPriorityApplicationIdentification': True,
            'ApplicationNumberText': True,
            'FilingDate': True,
            'ApplicantName': False
        }),
        ("ApplicationNumberText和earliestpriorityFilingDate为空", basic_data_priority_empty, {
            'EarliestPriorityApplicationIdentification': True,
            'ApplicationNumberText': False,
            'FilingDate': False,
            'ApplicantName': True
        }),
        ("所有字段都有值", basic_data_full, {
            'EarliestPriorityApplicationIdentification': True,
            'ApplicationNumberText': True,
            'FilingDate': True,
            'ApplicantName': True
        })
    ]
    
    results = []
    
    for test_name, basic_data, expected in test_cases:
        print(f"\n=== 测试用例：{test_name} ===")
        
        # 生成XML
        root, reminders = generate_xml(test_sequences, basic_data, '.')
        
        # 检查结果
        test_results = {
            'EarliestPriorityApplicationIdentification': False,
            'ApplicationNumberText': False,
            'FilingDate': False,
            'ApplicantName': False
        }
        
        # 检查EarliestPriorityApplicationIdentification元素是否存在
        earliest_priority = root.find('EarliestPriorityApplicationIdentification')
        if earliest_priority is not None:
            test_results['EarliestPriorityApplicationIdentification'] = True
            
            # 检查子元素
            if earliest_priority.find('ApplicationNumberText') is not None:
                test_results['ApplicationNumberText'] = True
            if earliest_priority.find('FilingDate') is not None:
                test_results['FilingDate'] = True
        
        # 检查ApplicantName元素是否存在
        if root.find('ApplicantName') is not None:
            test_results['ApplicantName'] = True
        
        # 输出结果
        print(f"预期结果: {expected}")
        print(f"实际结果: {test_results}")
        
        # 验证结果
        passed = all(expected[key] == test_results[key] for key in expected)
        results.append((test_name, passed, expected, test_results))
        
        if passed:
            print("✅ 测试通过")
        else:
            print("❌ 测试失败")
            
            # 生成详细的XML输出用于调试
            xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
            print("\n生成的XML:")
            print(xml_str)
    
    # 总结
    print("\n=== 测试总结 ===")
    passed_count = sum(1 for _, passed, _, _ in results if passed)
    total_count = len(results)
    
    print(f"通过: {passed_count}/{total_count}")
    
    for test_name, passed, expected, actual in results:
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")
    
    return passed_count == total_count

if __name__ == "__main__":
    success = test_empty_fields()
    sys.exit(0 if success else 1)
