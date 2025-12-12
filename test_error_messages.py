#!/usr/bin/env python3
# 测试修改后的错误信息

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import parse_sequence

# 测试情况1: 非法修饰符（小写字母x）
print("=== 测试1: 非法修饰符（小写字母x）===")
try:
    parse_sequence("AxG", "RNA")
except ValueError as e:
    print(f"错误信息: {e}")

# 测试情况2: 非法碱基字符（字母Z）
print("\n=== 测试2: 非法碱基字符（字母Z）===")
try:
    parse_sequence("AGZ", "RNA")
except ValueError as e:
    print(f"错误信息: {e}")

# 测试情况3: 非法氨基酸字符（感叹号!）
print("\n=== 测试3: 非法氨基酸字符（感叹号!）===")
try:
    parse_sequence("AA!", "AA")
except ValueError as e:
    print(f"错误信息: {e}")

# 测试情况4: 合法序列
print("\n=== 测试4: 合法序列（带修饰符）===")
try:
    naked_seq, mods, special, moltype, _, _ = parse_sequence("AmGfU", "RNA")
    print(f"成功解析！裸序列: {naked_seq}")
    print(f"修饰符: {mods}")
except ValueError as e:
    print(f"错误信息: {e}")

# 测试情况5: 带行号的非法修饰符
print("\n=== 测试5: 带行号的非法修饰符===")
try:
    parse_sequence("AxG", "RNA", line_number=5)
except ValueError as e:
    print(f"错误信息: {e}")

# 测试情况6: 带行号的非法氨基酸
print("\n=== 测试6: 带行号的非法氨基酸===")
try:
    parse_sequence("AA!", "AA", line_number=10)
except ValueError as e:
    print(f"错误信息: {e}")
