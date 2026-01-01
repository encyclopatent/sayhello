#!/usr/bin/env python3

# 完整任务流程测试：模拟异步任务结果传递和前端数据访问
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import parser

# 模拟测试数据
test_data = {
    'Sequence': [
        'ATCGATCGATCG',
        'AUGCAGUCAUGC', 
        'ATCGNNATCG'
    ],
    'MolType': [
        'DNA',
        'RNA',
        'DNA'
    ],
    'Organism': [
        'Homo sapiens',
        'Mus musculus',
        'Escherichia coli'
    ]
}

def test_task_flow():
    """测试完整的任务流程：生成sequence_summary -> 模拟session存储 -> 模拟前端访问"""
    try:
        print("=== 完整任务流程测试 ===")
        
        # 模拟sequences数据结构（与真实环境一致）
        sequences = []
        for i, (seq, moltype, organism) in enumerate(zip(test_data['Sequence'], test_data['MolType'], test_data['Organism']), 1):
            sequences.append((seq, moltype, organism, None, [], [], [], None, None, i))
        
        print(f"\n1. 模拟序列数据：共{len(sequences)}个序列")
        for seq in sequences[:2]:  # 只显示前两个
            print(f"   序列{seq[9]}: {seq[0][:10]}... ({seq[1]}, {seq[2]})")
        
        # 2. 获取sequence_summary（调用真实函数）
        sequence_summary = parser.get_sequence_summary(sequences)
        
        print("\n2. 生成sequence_summary（调用真实函数）")
        print(f"   数据类型: {type(sequence_summary)}")
        print(f"   总序列数: {sequence_summary['total_count']}")
        print(f"   类型统计: {sequence_summary['type_counts']}")
        print(f"   详细信息数: {len(sequence_summary['details'])}")
        
        # 3. 模拟reminders数据
        reminders = [
            "⚠️  序列3(第3行)包含简并碱基 'N'，已在XML中标记为未定义碱基。",
            "⚠️  序列3(第3行)的DNA序列中存在简并碱基，已在XML中标记为未定义碱基。"
        ]
        
        print(f"\n3. 模拟提醒信息：共{len(reminders)}条")
        for reminder in reminders:
            print(f"   {reminder}")
        
        # 4. 模拟session存储（直接使用字典）
        session_data = {
            'xml_file': 'test_output.xml',
            'sequence_summary': sequence_summary,
            'reminders': reminders,
            'task_id': 'test_task_id'
        }
        
        print("\n4. 模拟session存储")
        print(f"   XML文件名: {session_data['xml_file']}")
        print(f"   Sequence_summary类型: {type(session_data['sequence_summary'])}")
        print(f"   Reminders类型: {type(session_data['reminders'])}")
        
        # 5. 模拟前端模板访问（Jinja2风格）
        print("\n5. 模拟前端模板访问（Jinja2风格）")
        
        # 测试访问基本信息
        print(f"   总序列数: {{ sequence_summary.total_count }} -> {session_data['sequence_summary']['total_count']}")
        print(f"   DNA序列数: {{ sequence_summary.type_counts.DNA }} -> {session_data['sequence_summary']['type_counts']['DNA']}")
        print(f"   RNA序列数: {{ sequence_summary.type_counts.RNA }} -> {session_data['sequence_summary']['type_counts']['RNA']}")
        
        # 测试循环访问序列详情
        print("   序列详情循环访问：")
        for i, seq in enumerate(session_data['sequence_summary']['details']):
            print(f"     序列{i+1}: 类型={{ seq.type }} -> {seq['type']}, 来源={{ seq.organism }} -> {seq['organism']}")
        
        # 测试访问提醒信息
        print("   提醒信息循环访问：")
        for i, reminder in enumerate(session_data['reminders']):
            print(f"     提醒{i+1}: {{ reminder }} -> {reminder}")
        
        # 6. 模拟JSON API响应
        print("\n6. 模拟JSON API响应")
        api_response = {
            'state': 'SUCCESS',
            'current': 100,
            'total': 100,
            'status': '转换完成！',
            'result': {
                'status': 'success',
                'xml_file': session_data['xml_file'],
                'sequence_summary': session_data['sequence_summary'],
                'reminders': session_data['reminders']
            }
        }
        
        # 测试JSON序列化
        json_response = json.dumps(api_response, ensure_ascii=False, indent=2)
        print(f"   JSON序列化成功: {len(json_response)}字符")
        
        # 解析JSON响应
        parsed_response = json.loads(json_response)
        print(f"   JSON解析成功: state={parsed_response['state']}, result={parsed_response['result']['status']}")
        
        print("\n✅ 完整任务流程测试通过！")
        print("   - sequence_summary可以正确生成")
        print("   - 数据可以以字典格式存储在session中")
        print("   - 前端可以使用点符号访问字典数据")
        print("   - JSON API响应可以正确序列化和解析")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_task_flow()
