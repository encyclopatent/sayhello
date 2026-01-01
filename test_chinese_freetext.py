#!/usr/bin/env python3
"""
测试中文freetext处理功能
"""
import xml.etree.ElementTree as ET
import sys

# 添加当前目录到Python路径
sys.path.append('/Users/zhaoyongjiang/Downloads/SAYHELLO')

from xml_generator import generate_xml

def test_chinese_freetext():
    """测试中文freetext处理功能"""
    print("=== 测试中文freetext处理功能 ===")
    
    # 测试数据
    basic_data = {
        'ApplicantFileReference': 'TEST_CHINESE',
        'ApplicantName': '测试有限公司',
        'ApplicantNameLatin': 'TEST Technology Co., Ltd.',
        'InventorName': '莫某某',
        'InventorNameLatin': 'morgen',
        'InventionTitle': '测试分子'
    }
    
    # 测试用例1：DNA序列，freetext包含中文
    test_cases = [
        {
            'name': '测试用例1：纯中文freetext',
            'sequence': 'ACGNT',
            'moltype': 'DNA',
            'freetexts': ['任意碱基'],
            'expected_english': 'custom modification',
            'expected_chinese': '任意碱基'
        },
        {
            'name': '测试用例2：中英文混合freetext',
            'sequence': 'ACGNT',
            'moltype': 'DNA',
            'freetexts': ['any base 任意碱基'],
            'expected_english': 'any base',
            'expected_chinese': '任意碱基'
        },
        {
            'name': '测试用例3：纯英文freetext',
            'sequence': 'ACGNT',
            'moltype': 'DNA',
            'freetexts': ['any base'],
            'expected_english': 'any base',
            'expected_chinese': ''
        },
        {
            'name': '测试用例4：包含or的中英文混合freetext',
            'sequence': 'ACGNT',
            'moltype': 'DNA',
            'freetexts': ['A or G 腺嘌呤或鸟嘌呤'],
            'expected_english': 'A or G',
            'expected_chinese': '腺嘌呤或鸟嘌呤'
        },
        {
            'name': '测试用例5：氨基酸序列中文freetext',
            'sequence': 'ACGX',
            'moltype': 'AA',
            'freetexts': ['任意氨基酸'],
            'expected_english': 'custom modification',
            'expected_chinese': '任意氨基酸'
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{i+1}. {test_case['name']}")
        
        # 准备测试数据
        test_sequences = [
            (test_case['sequence'], test_case['moltype'], 'synthetic construct', 
             'other DNA' if test_case['moltype'] == 'DNA' else 'other RNA', 
             test_case['freetexts'], [], [], False, None, 1)
        ]
        
        # 生成XML
        root, reminders = generate_xml(test_sequences, basic_data, '.')
        
        # 检查结果
        found_elements = []
        success = True
        
        # 查找所有包含note限定符的特征
        features_with_note = []
        
        for seq_data in root.findall('SequenceData'):
            for insd_seq in seq_data.findall('INSDSeq'):
                for feature_table in insd_seq.findall('INSDSeq_feature-table'):
                    for feature in feature_table.findall('INSDFeature'):
                        for quals in feature.findall('INSDFeature_quals'):
                            for qual in quals.findall('INSDQualifier'):
                                qual_name = qual.find('INSDQualifier_name')
                                if qual_name and qual_name.text == 'note':
                                    features_with_note.append((feature, qual))
        
        # 检查每个包含note的特征
        for feature, note_qual in features_with_note:
            feature_key = feature.find('INSDFeature_key').text
            location = feature.find('INSDFeature_location').text
            
            # 检查英文值
            insd_value = note_qual.find('INSDQualifier_value')
            if insd_value is None:
                print(f"  ❌ 错误：未找到INSDQualifier_value元素")
                success = False
            else:
                actual_english = insd_value.text
                if actual_english != test_case['expected_english']:
                    print(f"  ❌ 错误：英文值不匹配，预期：{test_case['expected_english']}，实际：{actual_english}")
                    success = False
                else:
                    print(f"  ✅ 英文值正确：{actual_english}")
            
            # 检查非英文值
            non_english_value = note_qual.find('NonEnglishQualifier_value')
            if test_case['expected_chinese']:
                if non_english_value is None:
                    print(f"  ❌ 错误：预期有NonEnglishQualifier_value元素，但未找到")
                    success = False
                else:
                    actual_chinese = non_english_value.text
                    if actual_chinese != test_case['expected_chinese']:
                        print(f"  ❌ 错误：中文值不匹配，预期：{test_case['expected_chinese']}，实际：{actual_chinese}")
                        success = False
                    else:
                        print(f"  ✅ 中文值正确：{actual_chinese}")
            else:
                if non_english_value is not None:
                    print(f"  ❌ 错误：预期没有NonEnglishQualifier_value元素，但找到了：{non_english_value.text}")
                    success = False
                else:
                    print(f"  ✅ 正确：没有NonEnglishQualifier_value元素")
            
            found_elements.append({
                'feature_key': feature_key,
                'location': location,
                'english_value': actual_english,
                'chinese_value': actual_chinese if non_english_value else ''
            })
        
        if not found_elements:
            print(f"  ❌ 错误：未找到包含note的特征元素")
            success = False
        
        results.append((test_case['name'], success))
        
        if success:
            print(f"  ✅ 测试通过")
        else:
            print(f"  ❌ 测试失败")
            
            # 打印生成的XML用于调试
            xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
            print(f"\n生成的XML:")
            print(xml_str)
    
    # 总结
    print("\n=== 测试总结 ===")
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"通过: {passed_count}/{total_count}")
    
    for test_name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")
    
    return passed_count == total_count

def test_specific_example():
    """测试用户提供的特定示例"""
    print("\n=== 测试用户提供的特定示例 ===")
    
    # 测试数据
    basic_data = {
        'ApplicantFileReference': 'TEST_SPECIFIC',
        'ApplicantName': '测试有限公司',
        'ApplicantNameLatin': 'TEST Technology Co., Ltd.',
        'InventorName': '莫某某',
        'InventorNameLatin': 'morgen',
        'InventionTitle': '测试分子'
    }
    
    # 测试序列：第9位是N，会生成modified_base特征
    test_sequences = [
        ('ACGUACGNUACGU', 'RNA', 'synthetic construct', 'other RNA', 
         ['任意碱基'], [], [], False, None, 1)
    ]
    
    # 生成XML
    root, reminders = generate_xml(test_sequences, basic_data, '.')
    
    # 查找位置9的modified_base特征
    found = False
    for seq_data in root.findall('SequenceData'):
        for insd_seq in seq_data.findall('INSDSeq'):
            for feature_table in insd_seq.findall('INSDSeq_feature-table'):
                for feature in feature_table.findall('INSDFeature'):
                    feature_key = feature.find('INSDFeature_key').text
                    location = feature.find('INSDFeature_location').text
                    
                    if feature_key == 'modified_base' and location == '9':
                        found = True
                        print("  ✅ 找到位置9的modified_base特征")
                        
                        # 检查mod_base值
                        mod_base = None
                        note_qual = None
                        
                        for quals in feature.findall('INSDFeature_quals'):
                            for qual in quals.findall('INSDQualifier'):
                                qual_name = qual.find('INSDQualifier_name')
                                if qual_name:
                                    if qual_name.text == 'mod_base':
                                        mod_base = qual.find('INSDQualifier_value').text
                                    elif qual_name.text == 'note':
                                        note_qual = qual
                        
                        if mod_base == 'OTHER':
                            print(f"  ✅ mod_base值正确：{mod_base}")
                        else:
                            print(f"  ❌ mod_base值错误，预期：OTHER，实际：{mod_base}")
                            return False
                        
                        if note_qual:
                            # 检查note值
                            note_value = note_qual.find('INSDQualifier_value').text
                            non_english_value = note_qual.find('NonEnglishQualifier_value')
                            
                            if note_value == 'custom modification':
                                print(f"  ✅ note值正确：{note_value}")
                            else:
                                print(f"  ❌ note值错误，预期：custom modification，实际：{note_value}")
                                return False
                            
                            if non_english_value and non_english_value.text == '任意碱基':
                                print(f"  ✅ NonEnglishQualifier_value值正确：{non_english_value.text}")
                            else:
                                print(f"  ❌ NonEnglishQualifier_value值错误或未找到")
                                return False
                        else:
                            print("  ❌ 未找到note限定符")
                            return False
                        
                        break
    
    if not found:
        print("  ❌ 未找到位置9的modified_base特征")
        return False
    
    print("  ✅ 测试通过")
    return True

if __name__ == "__main__":
    # 运行测试用例
    test1_passed = test_chinese_freetext()
    test2_passed = test_specific_example()
    
    # 总体结果
    print("\n=== 总体测试结果 ===")
    if test1_passed and test2_passed:
        print("✅ 所有测试通过！")
        sys.exit(0)
    else:
        print("❌ 部分测试失败！")
        sys.exit(1)
