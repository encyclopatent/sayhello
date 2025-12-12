# 测试提醒功能改进
import parser
import xml_generator

# 测试L96配体移除提醒
print("=== 测试L96配体移除提醒 ===")

# 测试旧格式L96
old_format_seq = "AmGmCmUmAmGmAfCmAfCfUmGmGmGmsAmsUfL96"
naked_sequence, modifications, special_positions, raw_moltype, has_degenerate_bases, ligand_removed = parser.parse_sequence(old_format_seq, "RNA")
print(f"旧格式L96 - ligand_removed: {ligand_removed}")

# 测试新格式L96
new_format_seq = "(mG)(mG)(mU)(mU)(fG)(mG)(fA)(mU)(fU)(fU)(fU)(mU)(fC)(mU)(mU)(mG)(mC)(mU)(mA)(mU)(mG)(L96)"
naked_sequence, modifications, special_positions, raw_moltype, has_degenerate_bases, ligand_removed = parser.parse_sequence(new_format_seq, "RNA")
print(f"新格式L96 - ligand_removed: {ligand_removed}")

# 测试默认值设置提醒
print("\n=== 测试默认值设置提醒 ===")

# 创建测试序列数据
sequences = [
    ("AmGmCmUmAmGmAfCmAfCfUmGmGmGmsAmsUfL96", None, None, None, [], [], [], None),  # 全部使用默认值
    ("AmGmCmUmAmGmAfCmAfCfUmGmGmGmsAmsUf", "RNA", "Homo sapiens", "other RNA", [], [], [], None),  # 全部指定值
    ("(mG)(mG)(mU)(mU)(fG)(mG)(L96)", None, "E. coli", None, [], [], [], None),  # 部分默认值
]

# 创建基本数据
basic_data = {
    "ApplicantFileReference": "TEST-2023-001",
    "earliestpriorityIPOfficeCode": "CN",
    "ApplicationNumberText": "CN20230000001",
    "earliestpriorityFilingDate": "2023-01-01",
    "ApplicantName": "测试申请人",
    "ApplicantNameLatin": "Test Applicant",
    "InventorName": "测试发明人",
    "InventorNameLatin": "Test Inventor",
    "InventionTitle": "测试发明"
}

# 生成XML并获取提醒
root, reminders = xml_generator.generate_xml(sequences, basic_data, ".")

# 输出提醒信息
print("提醒列表:")
for reminder in reminders:
    print(f"  {reminder}")

# 验证提醒数量
print(f"\n提醒总数: {len(reminders)}")
print(f"预期至少有3条提醒")

print("\n=== 测试完成 ===")