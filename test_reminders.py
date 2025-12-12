# 测试提醒功能
import xml_generator
import parser

# 测试数据：包含简并碱基和L96配体的序列
test_sequences = [
    ("AGCTMRW", None, None, None, [], [], [], None),  # 包含简并碱基的序列
    ("AGCTL96", None, None, None, [], [], [], None),  # 包含L96配体的序列
    ("AGCT", None, None, None, [], [], [], None)       # 普通序列
]

# 测试基本数据
test_basic_data = {
    'ApplicantFileReference': 'test',
    'earliestpriorityIPOfficeCode': 'CN',
    'ApplicationNumberText': '202312345678.9',
    'earliestpriorityFilingDate': '2023-01-01',
    'ApplicantName': '测试申请人',
    'ApplicantNameLatin': 'Test Applicant',
    'InventorName': '测试发明人',
    'InventorNameLatin': 'Test Inventor',
    'InventionTitle': '测试发明'
}

# 生成XML并获取提醒
xml_root, reminders = xml_generator.generate_xml(test_sequences, test_basic_data, ".")

# 输出提醒信息
print("生成的提醒信息：")
for reminder in reminders:
    print(f"  {reminder}")

# 验证提醒数量是否符合预期
print(f"\n总提醒数量：{len(reminders)}")

# 验证是否包含简并碱基和L96配体的提醒
has_degenerate_reminder = any("简并碱基" in r for r in reminders)
has_l96_reminder = any("L96配体" in r for r in reminders)
has_default_reminders = len(reminders) > 2  # 应该有一些默认值提醒

print(f"\n验证结果：")
print(f"包含简并碱基提醒：{'✓' if has_degenerate_reminder else '✗'}")
print(f"包含L96配体提醒：{'✓' if has_l96_reminder else '✗'}")
print(f"包含默认值提醒：{'✓' if has_default_reminders else '✗'}")

# 检查是否每个提醒都包含行号
has_line_numbers = all("第" in r and "行" in r for r in reminders)
print(f"所有提醒都包含行号：{'✓' if has_line_numbers else '✗'}")
