# test_user_sequences.py
from parser import parse_sequence

# 用户提供的测试序列
test_seq1 = "CmsUfsAmCmUmCfNCmAmGmCmAmGmAfCmAfCfUmGmGmGmsAmsUf"
test_seq2 = "AesCesGesUesGTMAsAesUesAesAe"
test_seq3 = "aGCtMf"

def test_sequence(seq, expected_moltype="RNA"):
    print(f"\n测试序列: {seq}")
    print(f"期望分子类型: {expected_moltype}")
    try:
        result = parse_sequence(seq, expected_moltype)
        print(f"解析结果:")
        print(f"  裸序列: {result[0]}")
        print(f"  修饰数: {len(result[1])}")
        print(f"  修饰详情: {result[1]}")
        print(f"  特殊位置: {result[2]}")
        print(f"  分子类型: {result[3]}")
        print(f"  包含简并碱基: {result[4]}")
        return True
    except Exception as e:
        print(f"  错误: {e}")
        return False

# 运行测试
print("=== 运行用户序列测试 ===")
test_sequence(test_seq1, "RNA")
test_sequence(test_seq2, "RNA")
test_sequence(test_seq3, "DNA")
print("\n=== 测试完成 ===")
