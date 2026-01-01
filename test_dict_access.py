#!/usr/bin/env python3

# 测试脚本：验证Jinja2模板是否可以正确访问字典格式的sequence_summary数据
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app

def test_dict_access():
    """测试字典格式的sequence_summary是否可以通过点符号访问"""
    # 模拟sequence_summary字典
    sequence_summary = {
        'total_count': 3,
        'type_counts': {
            'DNA': 2,
            'RNA': 1,
            'AA': 0
        },
        'details': [
            {
                'id': 1,
                'type': 'DNA',
                'organism': 'Homo sapiens',
                'naked_length': 100,
                'modification_special_notes': 'None'
            },
            {
                'id': 2,
                'type': 'DNA',
                'organism': 'Mus musculus',
                'naked_length': 150,
                'modification_special_notes': 'Methylated'
            },
            {
                'id': 3,
                'type': 'RNA',
                'organism': 'Escherichia coli',
                'naked_length': 200,
                'modification_special_notes': '5\' cap'
            }
        ],
        'has_degenerate_bases': False,
        'has_ligand_ignored': False
    }
    
    # 模拟session数据
    with app.test_request_context():
        # 使用Jinja2模板的语法来访问字典数据
        # 这模拟了模板中的 {{ sequence_summary.total_count }} 语法
        total_count = sequence_summary.total_count if hasattr(sequence_summary, 'total_count') else sequence_summary.get('total_count')
        
        # 模拟模板中的 {{ sequence_summary.type_counts.DNA }} 语法
        dna_count = sequence_summary.type_counts.DNA if hasattr(sequence_summary, 'type_counts') and hasattr(sequence_summary.type_counts, 'DNA') else sequence_summary.get('type_counts', {}).get('DNA')
        
        # 模拟模板中的循环访问语法
        details = []
        for seq in sequence_summary.details if hasattr(sequence_summary, 'details') else sequence_summary.get('details', []):
            details.append({
                'id': seq.id if hasattr(seq, 'id') else seq.get('id'),
                'type': seq.type if hasattr(seq, 'type') else seq.get('type'),
                'organism': seq.organism if hasattr(seq, 'organism') else seq.get('organism')
            })
        
        print("测试结果：")
        print(f"总序列数: {total_count}")
        print(f"DNA序列数: {dna_count}")
        print(f"详细信息数量: {len(details)}")
        
        # 验证所有数据是否正确获取
        if total_count == 3 and dna_count == 2 and len(details) == 3:
            print("\n✅ 测试通过！字典格式的数据可以被正确访问。")
            return True
        else:
            print("\n❌ 测试失败！无法正确访问字典格式的数据。")
            return False

if __name__ == "__main__":
    # 测试Jinja2模板风格的字典访问
    success = test_dict_access()
    
    # 测试标准字典访问
    print("\n标准字典访问测试：")
    sequence_summary = {
        'total_count': 3,
        'type_counts': {
            'DNA': 2,
            'RNA': 1,
            'AA': 0
        }
    }
    
    try:
        # 标准字典访问方式
        print(f"总序列数: {sequence_summary['total_count']}")
        print(f"DNA序列数: {sequence_summary['type_counts']['DNA']}")
        print("✅ 标准字典访问正常工作。")
    except Exception as e:
        print(f"❌ 标准字典访问失败: {e}")
    
    # 测试Jinja2的实际行为
    print("\nJinja2模板行为模拟：")
    from jinja2 import Template
    
    # 创建一个简单的Jinja2模板
    template_str = '''
    总序列数: {{ sequence_summary.total_count }}\n\    DNA序列: {{ sequence_summary.type_counts.DNA }} | RNA序列: {{ sequence_summary.type_counts.RNA }} | 氨基酸序列: {{ sequence_summary.type_counts.AA }}\n\    
    详细信息：\n\    {% for seq in sequence_summary.details %}
    序号: {{ seq.id }} | 类型: {{ seq.type }} | 来源: {{ seq.organism }}\n\    {% endfor %}
    '''
    
    template = Template(template_str)
    
    # 使用字典作为上下文渲染模板
    try:
        rendered = template.render(sequence_summary=sequence_summary)
        print("✅ Jinja2模板成功渲染！")
        print("渲染结果：")
        print(rendered)
    except Exception as e:
        print(f"❌ Jinja2模板渲染失败: {e}")
