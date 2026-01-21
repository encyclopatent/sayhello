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
    """将Excel文件转换为XML文件

    Args:
        file_path: Excel文件路径
        output_folder: XML输出文件夹路径（已废弃，保留以兼容）

    Returns:
        tuple: (xml文件名, 序列摘要, 提醒列表)

    Raises:
        ValueError: 当转换过程中出现错误时
    """
    # 输入验证
    if not isinstance(file_path, str):
        raise ValueError("file_path必须是字符串类型")

    if not isinstance(output_folder, str):
        raise ValueError("output_folder必须是字符串类型")
    
    if not os.path.exists(file_path):
        raise ValueError(f"文件不存在: {file_path}")
    
    if not os.path.exists(output_folder):
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            raise ValueError(f"无法创建输出文件夹: {str(e)}")
    
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
            error_msg = str(ve)
            print(f"数据验证错误: {error_msg}")
            raise
        except Exception as e:
            error_msg = f"读取Excel数据时发生错误: {str(e)}"
            print(f"数据读取错误: {error_msg}")
            raise ValueError(error_msg)

        # 验证基本数据
        if not basic_data:
            raise ValueError("basicdata工作表中没有有效数据")

        if 'ApplicantFileReference' not in basic_data:
            raise ValueError("basicdata工作表中缺少必需的ApplicantFileReference字段")

        parser.print_sequence_info(sequences)
        sequence_summary = parser.get_sequence_summary(sequences)

        try:
            xml_root, reminders = xml_generator.generate_xml(sequences, basic_data)
        except Exception as e:
            error_msg = f"生成XML时发生错误: {str(e)}"
            print(f"XML生成错误: {error_msg}")
            raise ValueError(error_msg)

        if reminders:
            print("\n=== 提醒信息 ===")
            for reminder in reminders:
                print(reminder)
            print("===============\n")

        output_file = f"{basic_data['ApplicantFileReference']}.xml"
        output_path = os.path.join(output_folder, output_file)
        
        try:
            xml_generator.write_xml_to_file(xml_root, output_path)
        except Exception as e:
            error_msg = f"写入XML文件时发生错误: {str(e)}"
            print(f"XML写入错误: {error_msg}")
            raise ValueError(error_msg)
        
        print(f"XML文件已生成: {output_file}")
        
        return output_file, sequence_summary, reminders
    
    except ValueError as ve:
        # 保留原始错误信息，不做过度包装
        raise
    except Exception as e:
        # 捕获所有其他异常，提供清晰的错误信息
        error_msg = f"转换过程中发生错误: {str(e)}"
        print(f"转换错误: {error_msg}")
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
