# main.py
import os
import parser
import xml_generator

def convert_excel_to_xml(file_path, output_folder):
    try:
        # 解析Excel数据
        sequences = parser.read_sequences_from_excel(file_path)
        basic_data = parser.read_basic_data_from_excel(file_path)
        
        # 打印序列信息
        parser.print_sequence_info(sequences)
        
        # 获取序列摘要信息
        sequence_summary = parser.get_sequence_summary(sequences)
        
        # 生成XML结构
        xml_root, reminders = xml_generator.generate_xml(sequences, basic_data, output_folder)
        
        # 输出提醒信息
        if reminders:
            print("\n=== 提醒信息 ===")
            for reminder in reminders:
                print(reminder)
            print("================")
        
        # 保存XML文件
        output_file = f"{basic_data['ApplicantFileReference']}.xml"
        output_path = os.path.join(output_folder, output_file)
        
        xml_generator.write_xml_to_file(xml_root, output_path)
        print(f"XML文件已生成: {output_file}")
        
        return output_file, sequence_summary, reminders
    
    except ValueError as ve:
        print(f"数据验证错误: {str(ve)}")
        raise
    except Exception as e:
        print(f"运行时错误: {str(e)}")
        raise

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("用法: python main.py <Excel文件路径> <输出目录>")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 执行转换
    output_file, _ = convert_excel_to_xml(excel_path, output_dir)
