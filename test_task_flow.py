#!/usr/bin/env python3
"""
测试异步任务结果传递流程
"""
import sys
import os
import json
import tempfile
import pandas as pd
from types import SimpleNamespace

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入需要的模块
from st26autonew import convert_excel_to_xml
from parser import get_sequence_summary

# 创建测试数据
test_data = {
    'Sequence': ['ACGTACGT', 'AUGAUGAUG', 'ABCDEFG'],
    'MolType': ['DNA', 'RNA', 'AA'],
    'Organism': ['Homo sapiens', 'Mus musculus', 'Escherichia coli']
}

def test_sequence_summary_generation():
    """测试sequence_summary的生成和转换"""
    print("Testing sequence_summary generation...")
    
    # 创建模拟的序列数据
    from parser import get_sequence_summary
    
    # 模拟sequences数据结构
    sequences = []
    for i, (seq, moltype, organism) in enumerate(zip(test_data['Sequence'], test_data['MolType'], test_data['Organism']), 1):
        # 创建模拟的序列元组
        sequences.append((
            seq,  # 序列
            moltype,  # 原始分子类型
            organism,  # 来源
            None,  # 限定分子类型
            [],  # freetext值
            [],  # 环信息
            [],  # 杂合区段
            None,  # check_ref
            None,  # parsed_seq_data
            i  # 行号
        ))
    
    try:
        # 调用get_sequence_summary函数
        sequence_summary = get_sequence_summary(sequences)
        
        # 打印原始sequence_summary
        print("\nOriginal sequence_summary:")
        print(json.dumps(sequence_summary, indent=2, ensure_ascii=False))
        
        # 测试转换为对象
        def dict_to_object(d):
            if isinstance(d, dict):
                obj = SimpleNamespace()
                for key, value in d.items():
                    setattr(obj, key, dict_to_object(value))
                return obj
            elif isinstance(d, list):
                return [dict_to_object(item) for item in d]
            else:
                return d
        
        sequence_summary_obj = dict_to_object(sequence_summary)
        
        # 测试对象访问
        print("\nTesting object access:")
        print(f"Total count: {sequence_summary_obj.total_count}")
        print(f"DNA count: {sequence_summary_obj.type_counts.DNA}")
        print(f"RNA count: {sequence_summary_obj.type_counts.RNA}")
        print(f"AA count: {sequence_summary_obj.type_counts.AA}")
        
        # 测试序列详情访问
        print("\nSequence details:")
        for seq in sequence_summary_obj.details:
            print(f"  ID: {seq.id}, Type: {seq.type}, Organism: {seq.organism}, Length: {seq.naked_length}")
            print(f"  Notes: {seq.modification_special_notes}")
        
        # 测试前端模板访问
        print("\nTesting template access patterns:")
        # 模拟Jinja2模板访问
        print(f"Template access sequence_summary.total_count: {sequence_summary_obj.total_count}")
        print(f"Template access sequence_summary.type_counts.DNA: {sequence_summary_obj.type_counts.DNA}")
        print(f"Template access sequence_summary.details[0].id: {sequence_summary_obj.details[0].id}")
        print(f"Template access sequence_summary.details[0].type: {sequence_summary_obj.details[0].type}")
        print(f"Template access sequence_summary.details[0].naked_length: {sequence_summary_obj.details[0].naked_length}")
        
        print("\n✓ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        os.remove(test_file_path)
        # 清理生成的XML文件
        if 'xml_file' in locals() and os.path.exists(os.path.join(output_folder, xml_file)):
            os.remove(os.path.join(output_folder, xml_file))

if __name__ == "__main__":
    success = test_sequence_summary_generation()
    sys.exit(0 if success else 1)
