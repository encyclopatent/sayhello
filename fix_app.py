#!/usr/bin/env python3
"""修复 app.py 中的 bug 和编码问题"""

# 读取原文件
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 修复1: 删除重复导入和未使用的导入
fixed_lines = []
for i, line in enumerate(lines):
    line_num = i + 1
    
    # 删除第5行: from types import SimpleNamespace
    if line_num == 5 and 'from types import SimpleNamespace' in line:
        print(f"删除第{line_num}行: {line.strip()}")
        continue
    
    # 删除第108行: from flask import request
    if line_num == 108 and line.strip() == 'from flask import request':
        print(f"删除第{line_num}行: {line.strip()}")
        continue
    
    fixed_lines.append(line)

# 修复2: 修复字符串替换问题
fixed_content = ''.join(fixed_lines)

# 修复 alignment_analyze() 中的 replace 问题
import re
fixed_content = re.sub(
    r"target_sequence = request\.form\.get\('target_sequence', ''\)\.strip\(\)\.upper\(\)\.replace\('\\s\+', ''\)",
    "target_sequence = re.sub(r'\\s+', '', request.form.get('target_sequence', '').strip().upper())",
    fixed_content
)
fixed_content = re.sub(
    r"query_sequence = request\.form\.get\('query_sequence', ''\)\.strip\(\)\.upper\(\)\.replace\('\\s\+', ''\)",
    "query_sequence = re.sub(r'\\s+', '', request.form.get('query_sequence', '').strip().upper())",
    fixed_content
)

# 修复3: 修复 send_file 参数 - attachment_filename -> download_name
fixed_content = re.sub(
    r'attachment_filename=filename',
    r'download_name=filename',
    fixed_content
)

# 修复4: 修复 blast_status() 返回状态码
# 删除 "}), 500"
fixed_content = re.sub(
    r"'blast_results': None\s*\}\s*\),\s*500",
    "'blast_results': None\n            })",
    fixed_content
)

# 写回文件
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("\n✅ 修复完成！")
print("\n主要修复：")
print("1. ✅ 删除重复导入: from flask import request")
print("2. ✅ 删除未使用导入: from types import SimpleNamespace")
print("3. ✅ 修复字符串替换: .replace('\\\\s+', '') -> re.sub(r'\\\\s+', '', ...)")
print("4. ✅ 修复send_file参数: attachment_filename -> download_name")
print("5. ✅ 修复blast_status返回状态码")
