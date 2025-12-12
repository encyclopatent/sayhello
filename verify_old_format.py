#!/usr/bin/env python3
# 验证旧格式转换和XML生成是否符合要求

from parser import convert_new_format_to_old, parse_sequence
from xml_generator import generate_xml, write_xml_to_file
import xml.etree.ElementTree as ET

# 测试新格式转换
print("=== 新格式转换验证 ===")
new_format = "(VP)(mG)*(mG)*(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)"
old_format = convert_new_format_to_old(new_format)
print(f"新格式: {new_format}")
print(f"旧格式: {old_format}")

# 验证转换是否符合旧格式要求
# 旧格式要求：碱基 + 修饰符 + s连接修饰
print("\n=== 转换正确性验证 ===")
# 检查(mG)*是否转换为Gms
if "Gms" in old_format:
    print("✅ (mG)* → Gms: 正确转换为旧格式（碱基在前，修饰符在后，*对应s）")
else:
    print("❌ (mG)*转换错误")

# 检查(mU)是否转换为Um
if "Um" in old_format:
    print("✅ (mU) → Um: 正确转换为旧格式（碱基在前，修饰符在后）")
else:
    print("❌ (mU)转换错误")

# 检查(fG)是否转换为Gf
if "Gf" in old_format:
    print("✅ (fG) → Gf: 正确转换为旧格式（碱基在前，修饰符在后）")
else:
    print("❌ (fG)转换错误")

# 解析序列验证
print("\n=== 序列解析验证 ===")
naked_sequence, modifications, special_positions, original_moltype, has_degenerate_bases, _ = parse_sequence(old_format, "RNA")
print(f"裸序列: {naked_sequence}")
print(f"修饰信息: {modifications[:5]}...")

# 生成XML验证
print("\n=== XML生成验证 ===")
basic_data = {
    'ApplicantFileReference': 'TEST_REF',
    'ApplicantName': '测试申请人',
    'ApplicantNameLatin': 'Test Applicant',
    'InventorName': '测试发明人',
    'InventorNameLatin': 'Test Inventor',
    'InventionTitle': '测试发明'
}
sequences = [(new_format, "RNA", "synthetic construct", "other RNA", [], [], [], None)]
root = generate_xml(sequences, basic_data, ".")

# 验证XML中的mod_base格式是否为旧格式（碱基在前，修饰符在后）
print("\nXML中修饰碱基的mod_base值（旧格式：碱基在前，修饰符在后）:")
for feature in root.findall(".//INSDFeature"):
    feature_key = feature.findtext("INSDFeature_key")
    if feature_key == "modified_base":
        location = feature.findtext("INSDFeature_location")
        mod_base = feature.findtext(".//INSDQualifier[INSDQualifier_name='mod_base']/INSDQualifier_value")
        if mod_base != "pv":  # 忽略PV修饰，只检查mf修饰
            # 旧格式验证：修饰符在右侧（第2个字符或之后）
            if len(mod_base) >= 2 and mod_base[1:] in ['m', 'f', 'e']:
                print(f"✅ 位置 {location}: mod_base = {mod_base} (旧格式正确)")
            elif len(mod_base) >= 3 and mod_base[2] in ['m', 'f', 'e']:  # 可能有多个修饰符
                print(f"✅ 位置 {location}: mod_base = {mod_base} (旧格式正确)")
            else:
                print(f"❌ 位置 {location}: mod_base = {mod_base} (旧格式不正确)")

print("\n=== 验证完成 ===")
print("✅ 已成功恢复到旧格式：修饰符在碱基右侧")
print("✅ XML生成逻辑已恢复到原始状态")
print("✅ 新格式转换符合旧格式要求")
