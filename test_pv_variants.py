#!/usr/bin/env python3
# 测试pv修饰的各种变体

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import parse_sequence

# 测试各种pv修饰的变体
pv_variants = [
    'pvG',      # 原始小写
    'PvG',      # 首字母大写
    'PVG',      # 全大写
    'vpG',      # 反转小写
    'VpG',      # 反转首字母大写
    'VPG',      # 反转全大写
    'pv-G',     # 带连字符小写
    'Pv-G',     # 带连字符首字母大写
    'PV-G',     # 带连字符全大写
    'vp-G',     # 带连字符反转小写
    'Vp-G',     # 带连字符反转首字母大写
    'VP-G',     # 带连字符反转全大写
    'pvAmG',    # 复杂序列带修饰符
    'PV-AmG',   # 全大写带连字符和修饰符
]

moltype = 'RNA'

for variant in pv_variants:
    print(f"\n=== 测试: {variant} ===")
    try:
        naked_sequence, modifications, special_positions, original_moltype, has_degenerate, _ = parse_sequence(variant, moltype)
        print(f"成功解析！")
        print(f"裸序列: {naked_sequence}")
        print(f"修饰符: {modifications}")
        print(f"是否包含pv修饰: {'是' if any(mod[1] == 'pv' for mod in modifications) else '否'}")
    except Exception as e:
        print(f"解析失败: {e}")

# 测试不带修饰符的序列（确保不影响正常序列）
print(f"\n=== 测试: 不带修饰符的正常序列 ===")
try:
    naked_sequence, modifications, special_positions, original_moltype, has_degenerate, _ = parse_sequence('AGU', moltype)
    print(f"成功解析！")
    print(f"裸序列: {naked_sequence}")
    print(f"修饰符: {modifications}")
    print(f"是否包含pv修饰: {'是' if any(mod[1] == 'pv' for mod in modifications) else '否'}")
except Exception as e:
    print(f"解析失败: {e}")
