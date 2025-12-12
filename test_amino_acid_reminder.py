#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试氨基酸序列中的特殊氨基酸提醒
"""

import sys
import os
import pandas as pd

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入parser模块
from parser import read_sequences_from_excel, get_sequence_summary

# 创建测试数据（只包含氨基酸序列和X残基）
data = {
    '序列': ['MVRHLTPXEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLGAFSDGLAHLDNLKGTFATLSELHCDKLHVDPENFRLLGNVLVCVLAHHFGKEFTPPVQAAYQKVVAGVANALAHKYH'],
    '分子类型': ['AA'],
    '来源': ['Homo sapiens'],
    'freetext1': ['X1注释']
}

# 创建DataFrame
df = pd.DataFrame(data)

# 创建临时Excel文件
import tempfile

with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
    tmp_filename = tmp.name
    writer = pd.ExcelWriter(tmp_filename, engine='xlsxwriter')
    
    # 创建基础数据sheet
    basic_data = {
        'Field': ['Title', 'Creator', 'Contact'],
        'Value': ['Test', 'Test User', 'test@example.com']
    }
    basic_df = pd.DataFrame(basic_data)
    basic_df.to_excel(writer, sheet_name='basicdata', index=False)
    
    # 创建序列数据sheet
    df.to_excel(writer, sheet_name='seqdata', index=False)
    writer.close()

print(f"临时Excel文件已创建: {tmp_filename}")

# 测试读取序列数据
print("\n=== 读取序列数据 ===")
try:
    sequences = read_sequences_from_excel(tmp_filename)
    print(f"成功读取 {len(sequences)} 条序列")
    
    # 测试生成序列摘要
    print("\n=== 生成序列摘要 ===")
    sequence_summary = get_sequence_summary(sequences)
    print(sequence_summary)
    
    # 检查是否包含正确的提醒
    print("\n=== 检查提醒内容 ===")
    if isinstance(sequence_summary, list):
        for item in sequence_summary:
            if isinstance(item, dict) and 'modifications' in item:
                modifications = item['modifications']
                print(f"修饰信息: {modifications}")
                
                # 检查是否包含"特殊氨基酸"而不是"特殊碱基"
                has_special_amino_acid = any('特殊氨基酸' in mod for mod in modifications)
                has_special_base = any('特殊碱基' in mod for mod in modifications)
                
                if has_special_amino_acid:
                    print("✅ 氨基酸序列使用了正确的'特殊氨基酸'提醒")
                elif has_special_base:
                    print("❌ 氨基酸序列错误地使用了'特殊碱基'提醒")
                
                # 检查RNA序列是否仍然使用"特殊碱基"
                if 'AA' in item.get('moltype', ''):
                    print("氨基酸序列检查完成")
                elif 'RNA' in item.get('moltype', '') or 'DNA' in item.get('moltype', ''):
                    if has_special_base:
                        print("✅ 核酸序列正确使用了'特殊碱基'提醒")

finally:
    # 删除临时文件
    if os.path.exists(tmp_filename):
        os.remove(tmp_filename)
        print(f"\n临时文件已删除: {tmp_filename}")
