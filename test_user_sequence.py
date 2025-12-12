# 测试用户提供的序列示例
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from parser import parse_sequence

def test_user_sequences():
    print("=== 测试用户提供的序列示例 ===")
    
    # 测试第一个序列：CmsUfsAmCmUmCfNCmAmGmCmAmGmAfCmAfCfUmGmGmGmsAmsUf
    # 所有m/f/s都是修饰
    print("\n1. 测试序列: CmsUfsAmCmUmCfNCmAmGmCmAmGmAfCmAfCfUmGmGmGmsAmsUf")
    seq, mods, special_pos, _, has_degen, _ = parse_sequence('CmsUfsAmCmUmCfNCmAmGmCmAmGmAfCmAfCfUmGmGmGmsAmsUf', 'RNA')
    print(f"   处理后序列: {seq}")
    print(f"   序列长度: {len(seq)}")
    print(f"   修饰列表: {mods}")
    print(f"   修饰数量: {len(mods)}")
    print(f"   特殊位置: {special_pos}")
    print(f"   包含简并碱基: {has_degen}")
    
    # 测试第二个序列：AesCesGesUesGTMAsAesUesAesAe
    # 只有大写M是简并碱基，其他e都是修饰
    print("\n2. 测试序列: AesCesGesUesGTMAsAesUesAesAe")
    seq, mods, special_pos, _, has_degen, _ = parse_sequence('AesCesGesUesGTMAsAesUesAesAe', 'DNA')
    print(f"   处理后序列: {seq}")
    print(f"   序列长度: {len(seq)}")
    print(f"   修饰列表: {mods}")
    print(f"   修饰数量: {len(mods)}")
    print(f"   特殊位置: {special_pos}")
    print(f"   包含简并碱基: {has_degen}")
    
    # 测试第三个序列：验证大小写保持
    print("\n3. 测试序列: aGCtMf")
    seq, mods, special_pos, _, has_degen, _ = parse_sequence('aGCtMf', 'DNA')
    print(f"   处理后序列: {seq}")
    print(f"   修饰列表: {mods}")
    print(f"   包含简并碱基: {has_degen}")
    
    # 验证简并碱基检测是否正确
    assert has_degen, "序列中包含大写M，应该检测到简并碱基"
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_user_sequences()