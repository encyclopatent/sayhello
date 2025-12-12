import pandas as pd
import os

# 模版文件路径
template_path = os.path.join('static', 'templates', 'template.xlsx')

# 读取Excel文件
try:
    # 读取"标准字符表"sheet
    df = pd.read_excel(template_path, sheet_name='标准字符表')
    
    # 显示前几行数据，了解数据结构
    print("数据前几行:")
    print(df.head())
    
    # 显示列名
    print("\n列名:")
    print(df.columns)
    
    # 如果列名是中文，尝试获取Abbreviation和Base-Definition列
    # 可能的列名包括：'Abbreviation', '缩写', 'Base-Definition', '碱基定义'
    for col in df.columns:
        print(f"\n列 '{col}' 的前5个值:")
        print(df[col].head())
        
    # 尝试创建缩写到全名的映射字典
    # 假设列名是'Abbreviation'和'Base-Definition'
    if 'Abbreviation' in df.columns and 'Base-Definition' in df.columns:
        abbrev_to_fullname = dict(zip(df['Abbreviation'], df['Base-Definition']))
        print("\n缩写到全名的映射:")
        for k, v in list(abbrev_to_fullname.items())[:10]:
            print(f"{k} -> {v}")
    
except Exception as e:
    print(f"读取Excel文件时出错: {e}")
    # 尝试列出所有sheet
    xl = pd.ExcelFile(template_path)
    print("\nExcel文件中的所有sheet:")
    print(xl.sheet_names)