# test_lowercase_m.py
from parser import parse_sequence, get_sequence_summary

# 测试序列：包含小写m（修饰）和大写M（简并碱基）
test_seq1 = "CmsUfsAmCmUmCfNCmAmGmCmAmGmAfCmAfCfUmGmGmGmsAmsUf"
test_seq2 = "AesCesGesUesGTMAsAesUesAesAe"
test_seq3 = "aGCtMf"

def test_sequence_parsing():
    print("=== 测试序列解析（检查小写m是否被误识别为简并碱基）===")
    
    # 测试序列1：只有小写m/f/s，无简并碱基
    print("\n测试序列1：CmsUfsAmCmUmCfNCmAmGmCmAmGmAfCmAfCfUmGmGmGmsAmsUf")
    try:
        result = parse_sequence(test_seq1, "RNA", line_number=1)
        print(f"  裸序列: {result[0]}")
        print(f"  修饰数: {len(result[1])}")
        print(f"  包含简并碱基: {result[4]}")
        if not result[4]:
            print("  ✅ 正确：未检测到简并碱基")
        else:
            print("  ❌ 错误：不应检测到简并碱基")
    except Exception as e:
        print(f"  错误: {e}")
    
    # 测试序列2：包含大写M（简并碱基）和小写e/s
    print("\n测试序列2：AesCesGesUesGTMAsAesUesAesAe")
    try:
        result = parse_sequence(test_seq2, "RNA", line_number=2)
        print(f"  裸序列: {result[0]}")
        print(f"  修饰数: {len(result[1])}")
        print(f"  包含简并碱基: {result[4]}")
        if result[4]:
            print("  ✅ 正确：检测到简并碱基（大写M）")
        else:
            print("  ❌ 错误：应检测到简并碱基（大写M）")
    except Exception as e:
        print(f"  错误: {e}")
    
    # 测试序列3：包含大写M（简并碱基）和小写f
    print("\n测试序列3：aGCtMf")
    try:
        result = parse_sequence(test_seq3, "DNA", line_number=3)
        print(f"  裸序列: {result[0]}")
        print(f"  修饰数: {len(result[1])}")
        print(f"  包含简并碱基: {result[4]}")
        if result[4]:
            print("  ✅ 正确：检测到简并碱基（大写M）")
        else:
            print("  ❌ 错误：应检测到简并碱基（大写M）")
    except Exception as e:
        print(f"  错误: {e}")

# 测试序列摘要生成
def test_sequence_summary():
    print("\n=== 测试序列摘要生成 ===")
    
    # 模拟从Excel读取的序列数据
    sequences = [
        (test_seq1, "RNA", "synthetic construct", "synthetic", [], [], [], None),
        (test_seq2, "RNA", "synthetic construct", "synthetic", [], [], [], None),
        (test_seq3, "DNA", "synthetic construct", "synthetic", [], [], [], None)
    ]
    
    try:
        summary = get_sequence_summary(sequences)
        print(f"总序列数: {summary['total_count']}")
        print(f"类型分布: {summary['type_counts']}")
        print(f"包含简并碱基: {summary['has_degenerate_bases']}")
        
        print("\n各序列详细信息:")
        for detail in summary['details']:
            print(f"  序号: {detail['id']}, 类型: {detail['type']}, 长度: {detail['length']}, 包含简并碱基: {detail['has_degenerate_bases']}")
            
        # 验证结果
        if not summary['details'][0]['has_degenerate_bases'] and \
           summary['details'][1]['has_degenerate_bases'] and \
           summary['details'][2]['has_degenerate_bases']:
            print("\n✅ 正确：序列1无简并碱基，序列2和3有简并碱基")
        else:
            print("\n❌ 错误：序列摘要生成不符合预期")
            
    except Exception as e:
        print(f"  错误: {e}")

if __name__ == "__main__":
    test_sequence_parsing()
    test_sequence_summary()
    print("\n=== 测试完成 ===")
