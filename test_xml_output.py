#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试新格式序列的XML输出，以便了解为什么无法导入WIPO工具
"""

import sys
import os
import xml.etree.ElementTree as ET
import pandas as pd

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import convert_new_format_to_old, parse_sequence, get_sequence_summary

def generate_xml(sequences):
    """生成与WIPO工具兼容的XML结构"""
    root = ET.Element("Seq-List")
    
    for seq_idx, seq_data in enumerate(sequences):
        sequence, raw_moltype, organism, qual_moltype, freetext_values, _, _, _ = seq_data
        
        # 解析序列
        naked_sequence, modifications, special_positions, _, _, _ = parse_sequence(sequence, raw_moltype)
        moltype = str(raw_moltype).upper() if pd.notnull(raw_moltype) else "RNA"
        
        # 创建Seq元素
        seq_elem = ET.SubElement(root, "Seq")
        
        # 添加分子类型
        mol_elem = ET.SubElement(seq_elem, "Mol-Data")
        ET.SubElement(mol_elem, "Molecule-Type").text = moltype
        
        # 添加来源
        org_elem = ET.SubElement(seq_elem, "Org")
        ET.SubElement(org_elem, "Org-Name", type="scientific").text = organism
        
        # 添加序列内容
        seq_data_elem = ET.SubElement(seq_elem, "Seq-Data")
        ET.SubElement(seq_data_elem, "Seq-str").text = naked_sequence
        
        # 添加修饰信息
        if modifications:
            mods_elem = ET.SubElement(seq_elem, "Modifications")
            for pos, mod, base in modifications:
                if mod != "ligand_ignored":  # 忽略配体修饰
                    mod_elem = ET.SubElement(mods_elem, "Mod")
                    ET.SubElement(mod_elem, "Mod-Pos").text = str(pos)
                    ET.SubElement(mod_elem, "Mod-Type").text = mod
                    ET.SubElement(mod_elem, "Mod-Base").text = base
    
    # 格式化XML
    import xml.dom.minidom as minidom
    rough_string = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def test_wipo_import_issue():
    """测试新格式序列解析结果，特别是XML输出"""
    print("=== 新格式序列WIPO导入问题排查 ===")
    
    # 使用用户提供的新格式序列示例
    new_format_sequence = "(VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)"
    
    print(f"\n1. 原始新格式序列：")
    print(new_format_sequence)
    
    # 转换为旧格式
    old_format_sequence = convert_new_format_to_old(new_format_sequence)
    print(f"\n2. 转换后的旧格式序列：")
    print(old_format_sequence)
    
    # 解析序列
    try:
        naked_sequence, modifications, special_positions, raw_moltype, has_degenerate_bases, _ = parse_sequence(new_format_sequence, "RNA")
        
        print(f"\n3. 解析结果：")
        print(f"   裸序列：{naked_sequence}")
        print(f"   分子类型：{raw_moltype}")
        print(f"   裸序列长度：{len(naked_sequence)}")
        print(f"   修饰数量：{len(modifications)}")
        print(f"   特殊位置数量：{len(special_positions)}")
        print(f"   是否包含简并碱基：{has_degenerate_bases}")
        
        print(f"\n4. 修饰详情：")
        for pos, mod, base in modifications:
            print(f"   - 位置：{pos}, 修饰：{mod}, 碱基：{base}")
        
        # 获取序列摘要
        sequences = [(new_format_sequence, "RNA", "synthetic construct", None, [], [], [], None)]
        sequence_summary = get_sequence_summary(sequences)
        
        print(f"\n5. 序列摘要：")
        print(f"   总序列数：{sequence_summary['total_count']}")
        print(f"   RNA序列数：{sequence_summary['type_counts']['RNA']}")
        print(f"   修饰和特殊说明：{sequence_summary['details'][0]['modification_special_notes']}")
        
        # 生成XML输出
        print(f"\n6. 生成的XML结构：")
        import pandas as pd  # 导入缺失的pandas
        xml_output = generate_xml(sequences)
        print(xml_output)
        
        # 保存XML到文件以便进一步检查
        with open("wipo_test_output.xml", "w", encoding="utf-8") as f:
            f.write(xml_output)
        print(f"\n7. XML已保存到：wipo_test_output.xml")
        
        # 检查可能的问题
        print(f"\n8. 可能的WIPO导入问题：")
        
        # 检查RNA序列中的U是否被转换为T
        if 'RNA' in raw_moltype and 'T' in naked_sequence:
            print("   - RNA序列中的U被转换为T，这可能不被WIPO工具接受")
        
        # 检查修饰位置格式
        for pos, mod, base in modifications:
            if '^' in str(pos):
                print(f"   - 连接修饰's'使用位置格式{pos}，WIPO可能需要不同的表示方式")
        
        # 检查修饰符格式
        for pos, mod, base in modifications:
            if mod == 'pv' and base == 'other':
                print("   - PV修饰使用'other'作为碱基，WIPO可能需要特定碱基")
        
        print(f"\n9. 转换后的序列长度分析：")
        print(f"   - 原始新格式长度：{len(new_format_sequence)}")
        print(f"   - 转换后旧格式长度：{len(old_format_sequence)}")
        print(f"   - 裸序列长度：{len(naked_sequence)}")
        
    except Exception as e:
        print(f"\n解析过程中出现错误：{str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_wipo_import_issue()
