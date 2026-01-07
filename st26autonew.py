# main.py
import os
import pandas as pd
import parser
import xml_generator

def check_required_sheets(file_path):
    """检查Excel文件是否包含必需的基础sheet
    
    Returns:
        tuple: (has_basicdata, has_seqdata)
    """
    try:
        xl = pd.ExcelFile(file_path, engine='openpyxl')
        sheet_names = xl.sheet_names
        has_basicdata = 'basicdata' in sheet_names
        has_seqdata = 'seqdata' in sheet_names
        return has_basicdata, has_seqdata
    except Exception as e:
        print(f"读取Excel文件时出错: {e}")
        return False, False

def convert_excel_to_xml(file_path, output_folder):
    try:
        has_basicdata, has_seqdata = check_required_sheets(file_path)
        
        if not has_basicdata or not has_seqdata:
            missing_sheets = []
            if not has_basicdata:
                missing_sheets.append('basicdata')
            if not has_seqdata:
                missing_sheets.append('seqdata')
            
            error_msg = f"Excel文件缺少必需的sheet：{', '.join(missing_sheets)}。请使用模版上传数据！"
            print(f"数据验证错误: {error_msg}")
            raise ValueError(error_msg)
        
        try:
            sequences = parser.read_sequences_from_excel(file_path)
            basic_data = parser.read_basic_data_from_excel(file_path)
        except ValueError as ve:
            if "not found" in str(ve):
                error_msg = "请使用模版上传数据！Excel文件中缺少必需的sheet（basicdata或seqdata）。"
                print(f"数据验证错误: {error_msg}")
                raise ValueError(error_msg)
            else:
                raise
        
        parser.print_sequence_info(sequences)
        sequence_summary = parser.get_sequence_summary(sequences)
        
        xml_root, reminders = xml_generator.generate_xml(sequences, basic_data, output_folder)
        
        if reminders:
            print("\n=== 提醒信息 ===")
            for reminder in reminders:
                print(reminder)
            print("================")
        
        output_file = f"{basic_data['ApplicantFileReference']}.xml"
        output_path = os.path.join(output_folder, output_file)
        
        xml_generator.write_xml_to_file(xml_root, output_path)
        print(f"XML文件已生成: {output_file}")
        
        return output_file, sequence_summary, reminders
    
    except ValueError as ve:
        error_msg = str(ve)
        if "请使用模版" in error_msg:
            raise ValueError(error_msg)
        else:
            raise ValueError("请使用模版上传数据！Excel文件中缺少必需的sheet（basicdata或seqdata）。")
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg:
            raise ValueError("请使用模版上传数据！Excel文件中缺少必需的sheet（basicdata或seqdata）。")
        else:
            raise ValueError(error_msg)

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
