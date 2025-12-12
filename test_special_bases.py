import pandas as pd
import os
import sys

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入parser模块
from parser import read_sequences_from_excel, get_sequence_summary

# 创建测试数据（包含特殊碱基和注释）
data = {
    '序列': ['CNGTA', 'ACXTY', 'MVRHLTPXEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLGAFSDGLAHLDNLKGTFATLSELHCDKLHVDPENFRLLGNVLVCVLAHHFGKEFTPPVQAAYQKVVAGVANALAHKYH'],
    '分子类型': ['DNA', 'RNA', 'AA'],
    '来源': ['synthetic construct', 'synthetic construct', 'Homo sapiens'],
    'freetext1': ['N1注释', 'X1注释', 'X1注释'],
    'freetext2': ['', '', 'X2注释']
}

# 创建DataFrame
df = pd.DataFrame(data)

# 创建Excel文件
file_path = os.path.join('static', 'uploads', 'test_special_bases.xlsx')

# 确保目录存在
os.makedirs(os.path.dirname(file_path), exist_ok=True)

with pd.ExcelWriter(file_path) as writer:
    # 创建basicdata工作表
    basic_data = pd.DataFrame({
        'Field': ['ApplicantFileReference', 'ApplicationNumberText', 'earliestpriorityFilingDate', 'ApplicantName', 'ApplicantNameLatin', 'InventorName', 'InventorNameLatin', 'InventionTitle'],
        'Value': ['TEST001', '20251234567890', '2025-01-01', '测试公司', 'Test Company', '测试人员', 'Test Person', '测试发明']
    })
    basic_data.to_excel(writer, sheet_name='basicdata', index=False)
    
    # 创建seqdata工作表
    df.to_excel(writer, sheet_name='seqdata', index=False)

print(f"测试文件已创建：{file_path}")

# 测试解析功能
print("\n=== 测试序列解析功能 ===")
sequences = read_sequences_from_excel(file_path)
print(f"读取到 {len(sequences)} 条序列")

# 测试序列摘要功能
print("\n=== 测试序列摘要功能 ===")
summary = get_sequence_summary(sequences)
print(f"总序列数: {summary['total_count']}")
print(f"类型统计: {summary['type_counts']}")

# 验证每条序列的摘要信息
print("\n=== 序列详细信息验证 ===")
for seq in summary['details']:
    print(f"\n序列 {seq['id']}:")
    print(f"  类型: {seq['type']}")
    print(f"  来源: {seq['organism']}")
    print(f"  原始长度: {seq['length']}")
    print(f"  裸序列长度: {seq['naked_length']}")
    print(f"  修饰碱基个数: {seq['modification_count']}")
    print(f"  是否有简并碱基: {seq['has_degenerate_bases']}")
    print(f"  修饰和特殊说明: {seq['modification_special_notes']}")

print("\n=== 测试完成 ===")
