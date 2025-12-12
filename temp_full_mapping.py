import pandas as pd
import os

# 模版文件路径
template_path = os.path.join('static', 'templates', 'template.xlsx')

# 读取Excel文件
df = pd.read_excel(template_path, sheet_name='标准字符表')

# 创建缩写到全名的映射字典
abbrev_to_fullname = dict(zip(df['Abbreviation'], df['Definition.1']))

print("完整的缩写到全名映射:")
for k, v in abbrev_to_fullname.items():
    print(f"{k} -> {v}")

# 测试几个PREDEFINED_MODS中的字符
print("\n测试PREDEFINED_MODS中的字符:")
test_mods = ['cmnm5u', 'ac4c', 'gm', 'i', 'm1a']
for mod in test_mods:
    if mod in abbrev_to_fullname:
        print(f"{mod} -> {abbrev_to_fullname[mod]}")
    else:
        print(f"{mod} 不在映射中")

# 实现碱基类型识别函数
def get_base_type(fullname):
    """根据修饰碱基的全名识别对应的碱基类型"""
    fullname_lower = fullname.lower()
    if 'adenosine' in fullname_lower or 'adenine' in fullname_lower:
        return 'a'
    elif 'uridine' in fullname_lower or 'uracil' in fullname_lower:
        return 'u'
    elif 'cytidine' in fullname_lower or 'cytosine' in fullname_lower:
        return 'c'
    elif 'guanosine' in fullname_lower or 'guanine' in fullname_lower:
        return 'g'
    else:
        return None

# 测试碱基类型识别
print("\n测试碱基类型识别:")
for k, v in list(abbrev_to_fullname.items())[:10]:
    base_type = get_base_type(v)
    print(f"{k} -> {v} -> 碱基类型: {base_type}")