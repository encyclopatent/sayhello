import os
import tempfile
import shutil
from werkzeug.utils import secure_filename
import pandas as pd
from st26autonew import convert_excel_to_xml

# 创建测试数据
seq_data = {
    '序列': ['AUGACGUUAGC', 'MVRHLTPXEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRFFESFGDLSTPDAVMGNPKVKAHGKKVLGAFSDGLAHLDNLKGTFATLSELHCDKLHVDPENFRLLGNVLVCVLAHHFGKEFTPPVQAAYQKVVAGVANALAHKYH'],
    '分子类型': ['RNA', 'AA'],
    '来源': ['synthetic construct', 'Homo sapiens'],
    'freetext1': ['RNA序列注释', '蛋白质序列注释']
}

basic_data = {
    'Field': ['ApplicantFileReference', 'earliestpriorityFilingDate', 'ApplicantName', 'ApplicantNameLatin', 'InventorName', 'InventorNameLatin', 'InventionTitle'],
    'Value': ['TEST123', '2024-05-01', '测试有限公司', 'TEST Technology Co., Ltd.', '莫某某', 'morgen', '测试分子']
}

seq_df = pd.DataFrame(seq_data)
basic_df = pd.DataFrame(basic_data)

# 创建临时目录
temp_dir = tempfile.mkdtemp()
output_dir = tempfile.mkdtemp()

try:
    # 创建测试Excel文件
    test_file_path = os.path.join(temp_dir, 'test_download.xlsx')
    with pd.ExcelWriter(test_file_path, engine='xlsxwriter') as writer:
        seq_df.to_excel(writer, sheet_name='seqdata', index=False)
        basic_df.to_excel(writer, sheet_name='basicdata', index=False)
    
    print(f"创建测试Excel文件: {test_file_path}")
    print(f"文件大小: {os.path.getsize(test_file_path)} 字节")
    
    # 转换Excel到XML
    xml_filename, sequence_summary, reminders = convert_excel_to_xml(test_file_path, output_dir)
    xml_file_path = os.path.join(output_dir, xml_filename)
    
    print(f"\n生成XML文件: {xml_file_path}")
    print(f"文件大小: {os.path.getsize(xml_file_path)} 字节")
    print(f"\n序列摘要: {sequence_summary}")
    print(f"\n提醒信息: {reminders}")
    
    # 模拟下载后的清理过程
    print(f"\n模拟下载后的清理过程:")
    
    # 1. 读取XML文件内容（模拟下载）
    import io
    buffer = io.BytesIO()
    with open(xml_file_path, 'rb') as f:
        buffer.write(f.read())
    buffer.seek(0)
    
    # 2. 删除生成的XML文件
    if os.path.exists(xml_file_path):
        os.remove(xml_file_path)
        print(f"已删除生成的XML文件: {xml_file_path}")
    
    # 3. 删除上传的Excel文件
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print(f"已删除上传的Excel文件: {test_file_path}")
    
    # 验证文件是否被删除
    print(f"\n验证清理结果:")
    print(f"XML文件是否存在: {os.path.exists(xml_file_path)}")
    print(f"Excel文件是否存在: {os.path.exists(test_file_path)}")
    
    print(f"\n测试完成！")
    
except Exception as e:
    print(f"测试出错: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    # 清理临时目录
    shutil.rmtree(temp_dir)
    shutil.rmtree(output_dir)
    print(f"\n已清理临时目录")
