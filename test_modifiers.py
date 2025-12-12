# 测试修饰模式中的碱基大小写处理
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from parser import parse_sequence

def test_modifier_base_case():
    print("=== 测试修饰模式中的碱基大小写处理 ===")
    
    # 测试带修饰的简并碱基（修饰应记录小写）
    print("\n1. 带修饰的简并碱基（Mf）:")
    seq, mods, _, _, has_degen = parse_sequence('AGCTMf', 'DNA')
    print(f"   序列: {seq}")
    print(f"   修饰: {mods}")
    print(f"   简并碱基: {has_degen}")
    assert mods[0][2] == 'm', f"修饰应记录小写碱基 'm'，实际记录了 '{mods[0][2]}'"
    
    # 测试带修饰的普通大写碱基（修饰应记录小写）
    print("\n2. 带修饰的普通大写碱基（Am）:")
    seq, mods, _, _, has_degen = parse_sequence('AmGCT', 'DNA')
    print(f"   序列: {seq}")
    print(f"   修饰: {mods}")
    print(f"   简并碱基: {has_degen}")
    assert mods[0][2] == 'a', f"修饰应记录小写碱基 'a'，实际记录了 '{mods[0][2]}'"
    
    # 测试带修饰的普通小写碱基（修饰应记录小写）
    print("\n3. 带修饰的普通小写碱基（am）:")
    seq, mods, _, _, has_degen = parse_sequence('amGCT', 'DNA')
    print(f"   序列: {seq}")
    print(f"   修饰: {mods}")
    print(f"   简并碱基: {has_degen}")
    assert mods[0][2] == 'a', f"修饰应记录小写碱基 'a'，实际记录了 '{mods[0][2]}'"
    
    # 测试s修饰符（修饰应记录小写）
    print("\n4. 带s修饰符的碱基（Ags）:")
    seq, mods, _, _, has_degen = parse_sequence('AGsCT', 'DNA')
    print(f"   序列: {seq}")
    print(f"   修饰: {mods}")
    print(f"   简并碱基: {has_degen}")
    assert mods[0][2] == 'g', f"修饰应记录小写碱基 'g'，实际记录了 '{mods[0][2]}'"
    
    print("\n=== 所有修饰测试通过 ===")

if __name__ == "__main__":
    test_modifier_base_case()