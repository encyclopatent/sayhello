import os
import time
import st26autonew

# 设置测试文件和输出目录
test_file = "static/uploads/template.xlsx"
output_dir = "outputs"

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

print(f"开始测试转换性能，文件: {test_file}")
start_time = time.time()

# 执行转换
try:
    output_file, sequence_summary, reminders = st26autonew.convert_excel_to_xml(test_file, output_dir)
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"转换完成，生成文件: {output_file}")
    print(f"转换耗时: {duration:.2f} 秒")
    
    # 打印序列摘要信息
    print("\n序列摘要:")
    for key, value in sequence_summary.items():
        print(f"{key}: {value}")
        
    # 打印提醒信息
    if reminders:
        print("\n提醒信息:")
        for reminder in reminders:
            print(f"- {reminder}")
            
except Exception as e:
    end_time = time.time()
    duration = end_time - start_time
    print(f"转换失败，错误: {e}")
    print(f"耗时: {duration:.2f} 秒")
