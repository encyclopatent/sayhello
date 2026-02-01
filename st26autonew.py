"""
ST26 Excel to XML Converter - Main Module.

This module provides the main entry point for converting Excel files
to ST26 compliant XML format. Handles CLI interface and orchestrates
the conversion pipeline.
"""

import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    pd = None

import parser
import xml_generator


def check_required_sheets(file_path: str) -> Tuple[bool, bool, Optional[str]]:
    """
    检查Excel文件是否包含必需的基础sheet。

    Args:
        file_path: Excel文件路径

    Returns:
        Tuple包含:
        - has_basicdata: 是否包含basicdata sheet
        - has_seqdata: 是否包含seqdata sheet
        - error_msg: 错误信息（如果有）
    """
    logger.info(f"Checking required sheets in file: {file_path}")

    if not os.path.exists(file_path):
        error_msg = f"文件不存在: {file_path}"
        logger.error(error_msg)
        return False, False, error_msg

    if pd is None:
        error_msg = "pandas库未安装，无法读取Excel文件"
        logger.error(error_msg)
        return False, False, error_msg

    try:
        xl = pd.ExcelFile(file_path, engine='openpyxl')
        sheet_names = xl.sheet_names
        logger.debug(f"Found sheets: {sheet_names}")

        has_basicdata = 'basicdata' in sheet_names
        has_seqdata = 'seqdata' in sheet_names

        if not has_basicdata or not has_seqdata:
            missing = []
            if not has_basicdata:
                missing.append('basicdata')
            if not has_seqdata:
                missing.append('seqdata')
            error_msg = f"缺少必需的sheet: {', '.join(missing)}"
            logger.warning(error_msg)
            return has_basicdata, has_seqdata, error_msg

        logger.info("All required sheets found")
        return has_basicdata, has_seqdata, None

    except FileNotFoundError:
        error_msg = "文件不存在或无法访问"
        logger.error(f"File not found: {file_path}")
        return False, False, error_msg
    except PermissionError:
        error_msg = "没有权限读取文件，请检查文件权限"
        logger.error(f"Permission denied: {file_path}")
        return False, False, error_msg
    except ValueError as e:
        error_msg = f"Excel文件格式错误: {str(e)}"
        logger.error(f"Invalid Excel format: {e}")
        return False, False, error_msg
    except Exception as e:
        error_msg = f"读取Excel文件时发生未知错误: {str(e)}"
        logger.error(f"Unexpected error reading Excel: {e}", exc_info=True)
        return False, False, error_msg


def convert_excel_to_xml(
    file_path: str,
    output_folder: str,
    expert_settings: Optional[Dict[str, str]] = None
) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    将Excel文件转换为ST26 XML格式。

    Args:
        file_path: Excel文件路径
        output_folder: 输出目录路径
        expert_settings: 专家模式设置，包含：
            - 'mEn': m修饰符的英文名称（用于XML注释，可包含{base}占位符）
            - 'fEn': f修饰符的英文名称（用于XML注释，可包含{base}占位符）
            - 'eEn': e修饰符的英文名称（用于XML注释，可包含{base}占位符）
            - 'sEn': s修饰符的英文名称（用于XML注释）
            - 'pvEn': pv修饰符的英文名称（用于XML注释）

    Returns:
        Tuple包含:
        - output_file: 输出文件名
        - sequence_summary: 序列摘要信息
        - reminders: 提醒信息列表

    Raises:
        ValueError: 文件缺少必需的sheet或数据格式错误
        FileNotFoundError: 输入文件不存在
        RuntimeError: 转换过程发生错误
    """
    logger.info(f"Starting conversion: {file_path} -> {output_folder}")

    has_basicdata, has_seqdata, error_msg = check_required_sheets(file_path)

    if not has_basicdata or not has_seqdata:
        if error_msg:
            raise ValueError(error_msg)
        raise ValueError("Excel文件缺少必需的sheet。请使用模版上传数据！")

    try:
        logger.info("Reading sequences from Excel")
        sequences = parser.read_sequences_from_excel(file_path)
        logger.info(f"Read {len(sequences)} sequences")

        logger.info("Reading basic data from Excel")
        basic_data = parser.read_basic_data_from_excel(file_path)

    except ValueError as ve:
        error_message = str(ve)
        logger.error(f"Parser error: {error_message}")

        if "not found" in error_message.lower():
            raise ValueError("请使用模版上传数据！Excel文件中缺少必需的sheet（basicdata或seqdata）。")
        elif "sheet" in error_message.lower() or "not found" in error_message:
            raise ValueError("请使用模版上传数据！Excel文件中缺少必需的sheet。")
        else:
            raise ValueError(f"数据解析失败: {error_message}")

    except KeyError as ke:
        error_message = f"缺少必需的数据字段: {str(ke)}"
        logger.error(f"Missing required field: {ke}")
        raise ValueError(error_message)

    except IOError as ioe:
        error_message = f"文件读取错误: {str(ioe)}"
        logger.error(f"IO error during parsing: {ioe}")
        raise RuntimeError(error_message)

    except Exception as e:
        logger.error(f"Unexpected error during parsing: {e}", exc_info=True)
        raise RuntimeError(f"解析数据时发生未知错误: {str(e)}")

    try:
        parser.print_sequence_info(sequences)
        sequence_summary = parser.get_sequence_summary(sequences, expert_settings)

    except Exception as e:
        logger.error(f"Error getting sequence summary: {e}")
        sequence_summary = {}

    try:
        logger.info("Generating XML")
        xml_root, reminders = xml_generator.generate_xml(
            sequences, basic_data, output_folder, expert_settings
        )

        if reminders:
            logger.info(f"Generated {len(reminders)} reminders")
            for reminder in reminders:
                logger.debug(f"Reminder: {reminder}")

    except ValueError as ve:
        error_message = f"XML数据验证失败: {str(ve)}"
        logger.error(f"XML validation error: {ve}")
        raise ValueError(error_message)

    except ET.ParseError as pe:
        error_message = f"XML解析错误: {str(pe)}"
        logger.error(f"XML parse error: {pe}")
        raise RuntimeError(error_message)

    except Exception as e:
        logger.error(f"XML generation failed: {e}", exc_info=True)
        raise RuntimeError(f"生成XML时发生错误: {str(e)}")

    try:
        applicant_ref = basic_data.get('ApplicantFileReference')
        if not applicant_ref:
            raise ValueError("缺少申请人文件引用号")

        output_file = f"{applicant_ref}.xml"
        output_path = os.path.join(output_folder, output_file)

        logger.info(f"Writing XML to {output_path}")
        xml_generator.write_xml_to_file(xml_root, output_path)

        logger.info(f"Successfully generated: {output_file}")
        return output_file, sequence_summary, reminders

    except ValueError as ve:
        error_message = f"输出文件路径验证失败: {str(ve)}"
        logger.error(f"Output path validation error: {ve}")
        raise ValueError(error_message)

    except PermissionError:
        error_message = "没有权限写入输出目录，请检查目录权限"
        logger.error(f"Permission denied for output directory: {output_folder}")
        raise RuntimeError(error_message)

    except IOError as ioe:
        error_message = f"写入XML文件时发生I/O错误: {str(ioe)}"
        logger.error(f"IO error writing XML: {ioe}")
        raise RuntimeError(error_message)

    except Exception as e:
        logger.error(f"Failed to write XML file: {e}", exc_info=True)
        raise RuntimeError(f"写入XML文件时发生未知错误: {str(e)}")


def main() -> int:
    """
    CLI入口函数。

    Returns:
        退出代码（0表示成功，非0表示错误）
    """
    if len(sys.argv) != 3:
        print("用法: python st26autonew.py <Excel文件路径> <输出目录>")
        print("示例: python st26autonew.py input.xlsx output/")
        return 1

    excel_path = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.exists(excel_path):
        print(f"错误: 文件不存在: {excel_path}")
        logger.error(f"Input file not found: {excel_path}")
        return 1

    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Output directory ready: {output_dir}")

        output_file, sequence_summary, reminders = convert_excel_to_xml(excel_path, output_dir)

        print(f"\n转换完成!")
        print(f"输出文件: {output_file}")
        print(f"输出目录: {output_dir}")

        if reminders:
            print(f"\n提醒信息 ({len(reminders)}条):")
            for reminder in reminders:
                print(f"  - {reminder}")

        logger.info("Conversion completed successfully")
        return 0

    except ValueError as ve:
        print(f"数据验证错误: {ve}")
        logger.warning(f"Validation error: {ve}")
        return 1

    except RuntimeError as re:
        print(f"运行时错误: {re}")
        logger.error(f"Runtime error: {re}")
        return 1

    except Exception as e:
        print(f"未知错误: {e}")
        logger.exception("Unexpected error during conversion")
        return 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    sys.exit(main())
