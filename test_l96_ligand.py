#!/usr/bin/env python3
# 测试DNA/RNA序列结尾L96或-L96配体的处理

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import parse_sequence

def test_l96_ligand_handling():
    """测试DNA/RNA序列结尾L96或-L96配体的处理"""
    print("=== 测试DNA/RNA序列结尾L96或-L96配体处理 ===")
    
    # 测试用例列表
    test_cases = [
        # (序列, 分子类型, 预期结果描述)
        ("AGCT-L96", "DNA", "DNA序列结尾带-L96"),
        ("AGCTL96", "DNA", "DNA序列结尾带L96"),
        ("AGCU-L96", "RNA", "RNA序列结尾带-L96"),
        ("AGCUL96", "RNA", "RNA序列结尾带L96"),
        ("AGCT", "DNA", "正常DNA序列（不带L96）"),
        ("AGCU", "RNA", "正常RNA序列（不带L96）"),
        ("AGCTL96XYZ", "DNA", "DNA序列中间带L96（不应该被忽略）"),
        ("AGCT-l96", "DNA", "DNA序列结尾带小写-l96"),
        ("AGCTL96", "AA", "氨基酸序列带L96（不应该被处理）"),
    ]
    
    for seq, moltype, description in test_cases:
        print(f"\n--- {description} ---")
        print(f"输入序列: {seq}")
        print(f"分子类型: {moltype}")
        
        try:
            naked_sequence, modifications, special_positions, original_moltype, has_degenerate, ligand_removed = parse_sequence(seq, moltype)
            
            print(f"解析结果: {naked_sequence}")
            print(f"修饰信息: {modifications}")
            
            # 检查是否有配体忽略提醒
            if ligand_removed:
                print("✅ 配体已被忽略")
            else:
                print("❌ 未检测到配体")
                
        except Exception as e:
            print(f"❌ 解析失败: {e}")

if __name__ == "__main__":
    test_l96_ligand_handling()