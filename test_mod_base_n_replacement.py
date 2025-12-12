import os
import sys
import pandas as pd
from xml.etree.ElementTree import ElementTree

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xml_generator import generate_xml, write_xml_to_file

def test_mod_base_n_replacement():
    """测试mod_base处理和N碱基替换功能"""
    print("=== 测试mod_base处理和N碱基替换功能 ===")
    
    # 测试数据 - 元组列表，每个元组包含8个元素
    sequences = [
        # 测试1: DNA序列，PREDEFINED_MODS中的cmnm5u应该替换N为t
        ('N', 'DNA', 'synthetic construct', 'other DNA', ['cmnm5u'], [], [], None),
        # 测试2: RNA序列，PREDEFINED_MODS中的cmnm5u应该替换N为t（ST26标准）
        ('N', 'RNA', 'synthetic construct', 'other RNA', ['cmnm5u'], [], [], None),
        # 测试3: DNA序列，PREDEFINED_MODS中的ac4c应该替换N为c
        ('N', 'DNA', 'synthetic construct', 'other DNA', ['ac4c'], [], [], None),
        # 测试4: RNA序列，PREDEFINED_MODS中的gm应该替换N为g
        ('N', 'RNA', 'synthetic construct', 'other RNA', ['gm'], [], [], None),
        # 测试5: DNA序列，freetext包含adenosine，应该替换N为a
        ('N', 'DNA', 'synthetic construct', 'other DNA', ['modified adenosine'], [], [], None),
        # 测试6: mod_base为other的情况，应该添加note注释
        ('N', 'DNA', 'synthetic construct', 'other DNA', ['custom modification'], [], [], None)
    ]
    
    # 基本数据 - 包含所有必填字段
    basic_data = {
        'ApplicantFileReference': 'TEST_MOD_BASE_N',
        'ApplicantName': '测试用户',
        'ApplicantNameLatin': 'Test User',
        'InventorName': '测试发明人',
        'InventorNameLatin': 'Test Inventor',
        'InventionTitle': '测试发明'
    }
    
    # 生成XML
    output_folder = '.'
    root = generate_xml(sequences, basic_data, output_folder)
    xml_file = os.path.join(output_folder, 'TEST_MOD_BASE_N.xml')
    write_xml_to_file(root, xml_file)
    
    # 读取生成的XML文件
    xml_file = os.path.join(output_folder, 'TEST_MOD_BASE_N.xml')
    tree = ElementTree()
    tree.parse(xml_file)
    
    # 测试结果验证
    for i, seq_data in enumerate(sequences):
        sequence, raw_moltype, organism, qual_moltype, freetexts, ring_infos, hybrid_segments, _ = seq_data
        freetext = freetexts[0]
        print(f"\n测试{i+1}: {sequence} ({raw_moltype}, {freetext})")
        
        # 获取序列元素
        sequence_data = tree.findall('.//SequenceData')[i]
        insd_seq = sequence_data.find('INSDSeq')
        
        # 检查替换后的序列
        seq = insd_seq.find('INSDSeq_sequence').text
        print(f"  替换后的序列: {seq}")
        
        # 检查mod_base和note
        modified_base = insd_seq.find('.//INSDFeature_key[.="modified_base"]/..')
        if modified_base:
            mod_base = modified_base.find('.//INSDQualifier_name[.="mod_base"]/../INSDQualifier_value').text
            note = modified_base.find('.//INSDQualifier_name[.="note"]/../INSDQualifier_value')
            note_text = note.text if note is not None else '无'
            print(f"  mod_base: {mod_base}")
            print(f"  note: {note_text}")
            
            # 验证mod_base非other时没有note
            if mod_base != 'OTHER' and note_text != '无':
                print("  ❌ 错误: mod_base非OTHER时不应有note注释")
            elif mod_base == 'OTHER' and note_text == '无':
                print("  ❌ 错误: mod_base为OTHER时应有note注释")
            else:
                print("  ✅ mod_base和note处理正确")
        
        # 验证N碱基替换结果
        expected = None
        freetext = freetext.lower()
        moltype = raw_moltype
        
        if freetext == 'cmnm5u':
            expected = 't'  # 无论DNA还是RNA，都使用't'以符合ST26标准
        elif freetext == 'ac4c':
            expected = 'c'
        elif freetext == 'gm':
            expected = 'g'
        elif 'adenosine' in freetext:
            expected = 'a'
        elif freetext == 'custom modification':
            expected = 'n'  # 自定义修饰无法识别碱基类型
        
        if expected and seq.lower() != expected:
            print(f"  ❌ 错误: N碱基替换结果不正确，期望{expected}，实际{seq}")
        elif expected:
            print(f"  ✅ N碱基替换结果正确")
    
    # 清理测试文件
    if os.path.exists(xml_file):
        os.remove(xml_file)
    
    print("\n=== 测试完成 ===")

if __name__ == '__main__':
    test_mod_base_n_replacement()