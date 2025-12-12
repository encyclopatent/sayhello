import pandas as pd
import os

# 创建基础数据表格
basic_data = pd.DataFrame({
    'Field': ['ApplicantFileReference', 'earliestpriorityIPOfficeCode', 'ApplicationNumberText', 
              'earliestpriorityFilingDate', 'ApplicantName', 'ApplicantNameLatin', 
              'InventorName', 'InventorNameLatin', 'InventionTitle'],
    'Value': ['TEST001', 'CN', '20241111111111', '2024-05-09', '测试公司', 'Test Company', 
              '测试发明人', 'Test Inventor', '测试核酸分子']
})

# 创建序列数据表格，包含一个带有非法字符的序列
sequence_data = pd.DataFrame({
    '序列': ['AGCU#GUAC', 'AAAAA', 'ATCG'],  # 第一个序列包含非法字符 '#'
    '分子类型': ['RNA', 'AA', 'DNA'],
    '来源': ['synthetic construct', 'synthetic construct', 'synthetic construct']
})

# 创建Excel文件
with pd.ExcelWriter('test_file_with_error.xlsx', engine='openpyxl') as writer:
    basic_data.to_excel(writer, sheet_name='basicdata', index=False)
    sequence_data.to_excel(writer, sheet_name='seqdata', index=False)

print("测试文件已生成: test_file_with_error.xlsx")
