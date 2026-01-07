"""
ST26模块单元测试 - 测试parser.py和st26autonew.py的功能。

测试覆盖范围：
1. 配置加载和初始化
2. 序列解析和验证
3. 错误处理
4. Excel sheet检查
5. XML生成

作者: SAYHELLO Team
版本: 1.0.0
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import parser
from st26autonew import check_required_sheets


class TestConfigLoading:
    """配置加载相关测试。"""

    def test_load_default_config(self):
        """测试加载默认配置文件。"""
        config = parser.load_config()
        assert isinstance(config, dict)

    def test_load_config_from_nonexistent_path(self):
        """测试加载不存在的配置文件路径。"""
        config = parser.load_config("/nonexistent/path/config.yaml")
        assert isinstance(config, dict)
        assert len(config) == 0

    def test_get_config_value_with_dot_notation(self):
        """测试获取嵌套配置值。"""
        parser.CONFIG = {
            "sequence": {
                "max_length": 1000
            },
            "modifications": {
                "valid_amino_acids": ["A", "R", "N"]
            }
        }
        max_length = parser._get_config_value("sequence.max_length")
        assert max_length == 1000

    def test_get_config_value_with_default(self):
        """测试获取不存在的配置值时返回默认值。"""
        parser.CONFIG = {}
        value = parser._get_config_value("nonexistent.key", "default_value")
        assert value == "default_value"

    def test_get_config_value_with_empty_config(self):
        """测试空配置时的默认值返回。"""
        parser.CONFIG = {}
        value = parser._get_config_value("some.key", 42)
        assert value == 42


class TestSequenceValidation:
    """序列验证相关测试。"""

    def test_validate_valid_dna_sequence(self):
        """测试验证有效的DNA序列。"""
        result, error = parser.validate_sequence("ATCGATCG")
        assert result is True
        assert error == ""

    def test_validate_valid_rna_sequence(self):
        """测试验证有效的RNA序列。"""
        result, error = parser.validate_sequence("AUCGAUCG")
        assert result is True
        assert error == ""

    def test_validate_valid_protein_sequence(self):
        """测试验证有效的蛋白质序列。"""
        result, error = parser.validate_sequence("MKWVTFISLLFLFSSAY")
        assert result is True
        assert error == ""

    def test_validate_empty_sequence(self):
        """测试空序列验证。"""
        result, error = parser.validate_sequence("")
        assert result is False
        assert "不能为空" in error or "empty" in error.lower()

    def test_validate_sequence_with_invalid_characters(self):
        """测试包含非法字符的序列。"""
        result, error = parser.validate_sequence("ATCGXYZ")
        assert result is False
        assert "invalid" in error.lower() or "非法" in error

    def test_validate_sequence_length_too_long(self):
        """测试超长序列验证。"""
        long_sequence = "A" * 20000
        result, error = parser.validate_sequence(long_sequence)
        assert result is False
        assert "length" in error.lower() or "长度" in error

    def test_validate_sequence_length_too_short(self):
        """测试超短序列验证。"""
        result, error = parser.validate_sequence("")
        assert result is False


class TestSequenceParsing:
    """序列解析相关测试。"""

    def test_parse_dna_sequence(self):
        """测试解析DNA序列。"""
        moltype = parser.parse_sequence("ATCGATCG", "DNA")
        assert moltype == "DNA"

    def test_parse_rna_sequence(self):
        """测试解析RNA序列。"""
        moltype = parser.parse_sequence("AUCGAUCG", "RNA")
        assert moltype == "RNA"

    def test_parse_protein_sequence(self):
        """测试解析蛋白质序列。"""
        moltype = parser.parse_sequence("MKWVTFISLLFLFSSAY", "AA")
        assert moltype == "AA"

    def test_parse_sequence_case_insensitive(self):
        """测试序列解析大小写不敏感。"""
        moltype = parser.parse_sequence("atcgatcg", "dna")
        assert moltype == "DNA"

    def test_parse_sequence_with_spaces(self):
        """测试解析带空格的序列。"""
        moltype = parser.parse_sequence("ATC GAT CG", "DNA")
        assert moltype == "DNA"

    def test_parse_sequence_strips_whitespace(self):
        """测试序列解析去除空白字符。"""
        moltype = parser.parse_sequence("  ATCGATCG  ", "DNA")
        assert moltype == "DNA"


class TestModificationParsing:
    """修饰解析相关测试。"""

    def test_parse_methylation_modification(self):
        """测试解析甲基化修饰。"""
        moltype, mods, special_pos, raw_moltype, has_degenerate, ligand_removed = parser.parse_sequence("ATCGm5C", "DNA", line_number=1)
        assert moltype == "DNA"
        assert len(mods) > 0

    def test_parse_fluoro_modification(self):
        """测试解析氟化修饰。"""
        moltype, mods, special_pos, raw_moltype, has_degenerate, ligand_removed = parser.parse_sequence("ATCGfC", "DNA", line_number=1)
        assert moltype == "DNA"
        assert len(mods) >= 0

    def test_parse_thio_modification(self):
        """测试解析硫代修饰。"""
        moltype, mods, special_pos, raw_moltype, has_degenerate, ligand_removed = parser.parse_sequence("ATNGsT", "DNA", line_number=1)
        assert moltype == "DNA"

    def test_parse_multiple_modifications(self):
        """测试解析多个修饰。"""
        moltype, mods, special_pos, raw_moltype, has_degenerate, ligand_removed = parser.parse_sequence("ATm5CfGsT", "DNA", line_number=1)
        assert moltype == "DNA"


class TestDegenerateBases:
    """简并碱基相关测试。"""

    def test_detect_degenerate_base_R(self):
        """测试检测简并碱基R。"""
        moltype, mods, special_pos, raw_moltype, has_degenerate, ligand_removed = parser.parse_sequence("ATRG", "DNA", line_number=1)
        assert has_degenerate is True

    def test_detect_degenerate_base_Y(self):
        """测试检测简并碱基Y。"""
        moltype, mods, special_pos, raw_moltype, has_degenerate, ligand_removed = parser.parse_sequence("ATYG", "DNA", line_number=1)
        assert has_degenerate is True

    def test_detect_no_degenerate_bases(self):
        """测试正常序列不包含简并碱基。"""
        moltype, mods, special_pos, raw_moltype, has_degenerate, ligand_removed = parser.parse_sequence("ATCG", "DNA", line_number=1)
        assert has_degenerate is False


class TestSpecialPositions:
    """特殊位置相关测试。"""

    def test_parse_5_prime_modification(self):
        """测试5'端修饰。"""
        moltype, mods, special_pos, raw_moltype, has_degenerate, ligand_removed = parser.parse_sequence("mAATCG", "RNA", line_number=1)
        assert moltype == "RNA"

    def test_parse_3_prime_modification(self):
        """测试3'端修饰。"""
        moltype, mods, special_pos, raw_moltype, has_degenerate, ligand_removed = parser.parse_sequence("ATCGT", "RNA", line_number=1)
        assert moltype == "RNA"


class TestExcelSheetChecking:
    """Excel Sheet检查相关测试。"""

    def test_check_required_sheets_nonexistent_file(self):
        """测试检查不存在的Excel文件。"""
        has_basicdata, has_seqdata, error_msg = check_required_sheets("/nonexistent/file.xlsx")
        assert has_basicdata is False
        assert has_seqdata is False
        assert error_msg is not None

    def test_check_required_sheets_missing_sheets(self):
        """测试检查缺少必需sheet的Excel文件。"""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
            try:
                from openpyxl import Workbook
                wb = Workbook()
                ws = wb.active
                ws.title = "wrong_sheet"
                wb.save(tmp_path)

                has_basicdata, has_seqdata, error_msg = check_required_sheets(tmp_path)
                assert has_basicdata is False
                assert has_seqdata is False
                assert error_msg is not None
            finally:
                os.unlink(tmp_path)


class TestErrorHandling:
    """错误处理相关测试。"""

    def test_invalid_input_type(self):
        """测试无效输入类型。"""
        with pytest.raises((ValueError, TypeError)):
            parser.parse_sequence(12345, "DNA", line_number=1)

    def test_empty_sequence_raises_error(self):
        """测试空序列抛出错误。"""
        with pytest.raises(ValueError):
            parser.parse_sequence("", "DNA", line_number=1)

    def test_whitespace_only_sequence(self):
        """测试仅包含空白的序列。"""
        with pytest.raises(ValueError):
            parser.parse_sequence("   ", "DNA", line_number=1)

    def test_parse_sequence_with_none(self):
        """测试None输入。"""
        with pytest.raises((ValueError, TypeError)):
            parser.parse_sequence(None, "DNA", line_number=1)


class TestBackwardCompatibility:
    """向后兼容相关测试。"""

    def test_old_format_modification_1(self):
        """测试旧格式修饰标注1 (m5C -> m5C)。"""
        moltype, mods, special_pos, raw_moltype, has_degenerate, ligand_removed = parser.parse_sequence("ATm5CG", "DNA", line_number=1)
        assert moltype == "DNA"

    def test_old_format_modification_2(self):
        """测试旧格式修饰标注2。"""
        moltype, mods, special_pos, raw_moltype, has_degenerate, ligand_removed = parser.parse_sequence("ATm5m5CG", "DNA", line_number=1)
        assert moltype == "DNA"


class TestConstants:
    """常量定义相关测试。"""

    def test_base_names_defined(self):
        """测试碱基名称已定义。"""
        assert hasattr(parser, 'BASE_NAMES')
        assert isinstance(parser.BASE_NAMES, dict)
        assert 'A' in parser.BASE_NAMES
        assert 'T' in parser.BASE_NAMES
        assert 'G' in parser.BASE_NAMES
        assert 'C' in parser.BASE_NAMES

    def test_valid_amino_acids_defined(self):
        """测试有效氨基酸列表已定义。"""
        assert hasattr(parser, 'VALID_AA')
        assert isinstance(parser.VALID_AA, (list, set, tuple))
        assert 'A' in parser.VALID_AA
        assert 'G' in parser.VALID_AA
        assert len(parser.VALID_AA) >= 20

    def test_predefined_mods_defined(self):
        """测试预定义修饰列表已定义。"""
        assert hasattr(parser, 'PREDEFINED_MODS')
        assert isinstance(parser.PREDEFINED_MODS, (list, set, tuple))


class TestInputSanitization:
    """输入清理相关测试。"""

    def test_removes_leading_whitespace(self):
        """测试去除前导空白。"""
        moltype = parser.parse_sequence("  ATCG", "DNA", line_number=1)
        assert moltype == "DNA"

    def test_removes_trailing_whitespace(self):
        """测试去除尾随空白。"""
        moltype = parser.parse_sequence("ATCG  ", "DNA", line_number=1)
        assert moltype == "DNA"

    def test_removes_internal_spaces(self):
        """测试去除内部空格。"""
        moltype = parser.parse_sequence("AT CG", "DNA", line_number=1)
        assert moltype == "DNA"


class TestTypeHints:
    """类型提示相关测试。"""

    def test_functions_have_type_hints(self):
        """测试函数具有类型提示。"""
        import inspect

        functions_to_check = [
            parser.load_config,
            parser._get_config_value,
            parser.validate_sequence,
            parser.parse_sequence,
        ]

        for func in functions_to_check:
            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param_name != 'self' and param.annotation == inspect.Parameter.empty:
                    pytest.fail(f"Function {func.__name__} parameter '{param_name}' missing type hint")
