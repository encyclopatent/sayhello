import pandas as pd
import os
import sys

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入parser模块
from parser import read_sequences_from_excel, get_sequence_summary

# 创建测试数据
data = {
    '序列': ['CmsUfsAmCmUmCfCmAmGmCmAmGmAfCmAfCfUmGmGmGmsAmsUf', 'ACGTMRWSYKVDHB', 'MVRHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLGAFSDGLAHLDNLKGTFATLSELHCDKLHVDPENFRLLGNVLVCVLAHHFGKEFTPPVQAAYQKVVAGVANALAHKYH', 'MKVLVLGLSAAAALVYFSVTVALVKAKGNKAGKGGKAVTGTMIGGKVKDKAKDGLKVLGLVVDP'],
    '分子类型': ['RNA', 'DNA', 'AA', 'AA'],
    '来源': ['synthetic construct', 'synthetic construct', 'Homo sapiens', 'Escherichia coli'],
    '环信息': ['', '', 'region: 1..10 note: alpha helix; region: 20..30 note: beta sheet', 'region: 5..15 note: gamma turn; region: 25..35 note: loop']
}

# 创建DataFrame
df = pd.DataFrame(data)

# 创建Excel文件
file_path = os.path.join('static', 'uploads', 'test_naked_length.xlsx')

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

# 验证特定字段是否正确生成
print("\n=== 特定字段验证 ===")

# 验证RNA序列（第一条）
rna_seq = summary['details'][0]
if rna_seq['type'] == 'RNA':
    print("RNA序列验证:")
    print(f"  预期裸序列长度: 23, 实际: {rna_seq['naked_length']}")
    print(f"  预期修饰碱基个数: 26, 实际: {rna_seq['modification_count']}")
    print(f"  修饰和特殊说明包含'm': {'修饰: m×' in rna_seq['modification_special_notes']}")
    print(f"  修饰和特殊说明包含's': {'修饰: s×' in rna_seq['modification_special_notes']}")
    print(f"  修饰和特殊说明包含'f': {'修饰: f×' in rna_seq['modification_special_notes']}")

# 验证DNA简并碱基序列（第二条）
dna_seq = summary['details'][1]
if dna_seq['type'] == 'DNA':
    print("\nDNA简并碱基序列验证:")
    print(f"  预期裸序列长度: 13, 实际: {dna_seq['naked_length']}")
    print(f"  预期是否有简并碱基: True, 实际: {dna_seq['has_degenerate_bases']}")
    print(f"  修饰和特殊说明包含简并碱基: {'简并碱基:' in dna_seq['modification_special_notes']}")
    
    # 验证简并碱基统计是否正确
    degenerate_bases = ['M', 'R', 'W', 'S', 'Y', 'K', 'V', 'D', 'H', 'B']
    expected_counts = {base: 1 for base in degenerate_bases}
    for base in degenerate_bases:
        expected_str = f"{base}×1"
        if expected_str in dna_seq['modification_special_notes']:
            print(f"    ✓ 包含 {base}×1")
        else:
            print(f"    ✗ 不包含 {base}×1")

# 验证AA序列（第三条）
aa_seq = summary['details'][2]
if aa_seq['type'] == 'AA':
    print("\nAA序列验证:")
    print(f"  预期裸序列长度: {len(aa_seq['modification_special_notes']) > 0}, 实际: {aa_seq['naked_length']}")
    print(f"  修饰和特殊说明: {aa_seq['modification_special_notes']}")
    print(f"  预期是否有简并碱基: True, 实际: {aa_seq['has_degenerate_bases']}")
    print(f"  修饰和特殊说明包含简并碱基: {'简并碱基:' in aa_seq['modification_special_notes']}")

print("\n=== 测试完成 ===")
