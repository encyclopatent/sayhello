"""parser.py 模块的单元测试"""
import pytest
from parser import (
    parse_sequence,
    convert_new_format_to_old,
    get_sequence_summary,
    BASE_NAMES,
    VALID_AA,
    PREDEFINED_MODS
)


class TestConvertNewFormatToOld:
    """测试新格式到旧格式的转换"""

    def test_simple_conversion(self):
        """测试简单转换"""
        seq = "(mG)*(mU)"
        result, ligand = convert_new_format_to_old(seq)
        assert result == "GmU"
        assert ligand is False

    def test_vp_modifier(self):
        """测试 VP 修饰符"""
        seq = "(VP)(mG)*(mU)"
        result, ligand = convert_new_format_to_old(seq)
        assert result.startswith("PV")
        assert ligand is False

    def test_l96_ligand_removal(self):
        """测试 L96 配体移除"""
        seq = "(mG)*(L96)"
        result, ligand = convert_new_format_to_old(seq)
        assert "L96" not in result
        assert ligand is True

    def test_invalid_format(self):
        """测试无效格式返回原序列"""
        seq = "AUGCCGA"  # 不是新格式
        result, ligand = convert_new_format_to_old(seq)
        assert result == seq
        assert ligand is False


class TestParseSequence:
    """测试序列解析"""

    def test_simple_rna_sequence(self):
        """测试简单 RNA 序列"""
        seq = "AUGCCGA"
        naked, mods, special, moltype, has_degenerate, ligand = parse_sequence(
            seq, "RNA", 1
        )
        assert naked == "ATCCGA"  # U -> T
        assert len(mods) == 0
        assert len(special) == 0

    def test_rna_with_modifications(self):
        """测试带修饰的 RNA 序列"""
        seq = "mAmC"
        naked, mods, special, moltype, has_degenerate, ligand = parse_sequence(
            seq, "RNA", 1
        )
        assert naked == "AC"
        assert len(mods) == 2
        assert len(special) == 0

    def test_dna_sequence(self):
        """测试 DNA 序列"""
        seq = "ATCG"
        naked, mods, special, moltype, has_degenerate, ligand = parse_sequence(
            seq, "DNA", 1
        )
        assert naked == "ATCG"
        assert len(mods) == 0

    def test_aa_sequence(self):
        """测试氨基酸序列"""
        seq = "ACDEFGH"
        naked, mods, special, moltype, has_degenerate, ligand = parse_sequence(
            seq, "AA", 1
        )
        assert naked == "ACDEFGH"
        assert len(mods) == 0

    def test_sequence_with_n(self):
        """测试包含 N 的序列"""
        seq = "ANNC"
        naked, mods, special, moltype, has_degenerate, ligand = parse_sequence(
            seq, "RNA", 1
        )
        assert "N" in naked
        assert len(special) == 2

    def test_sequence_with_degenerate_bases(self):
        """测试包含简并碱基的序列"""
        seq = "AMRC"
        naked, mods, special, moltype, has_degenerate, ligand = parse_sequence(
            seq, "RNA", 1
        )
        assert has_degenerate is True
        assert "M" in naked and "R" in naked

    def test_invalid_character(self):
        """测试非法字符"""
        with pytest.raises(ValueError, match="并非系统允许的碱基表示"):
            parse_sequence("AXZ", "RNA", 1)

    def test_invalid_aa_character(self):
        """测试非法氨基酸字符"""
        with pytest.raises(ValueError, match="并非系统允许的氨基酸表示"):
            parse_sequence("AXBZ", "AA", 1)


class TestGetSequenceSummary:
    """测试序列摘要生成"""

    def test_empty_sequences(self):
        """测试空序列列表"""
        summary = get_sequence_summary([])
        assert summary['total_count'] == 0
        assert summary['type_counts']['DNA'] == 0
        assert summary['type_counts']['RNA'] == 0
        assert summary['type_counts']['AA'] == 0

    def test_mixed_sequences(self):
        """测试混合序列类型"""
        sequences = [
            ("ATCG", "DNA", "synthetic construct", "other DNA", [], [], [], None, None, 1),
            ("AUGCCGA", "RNA", "synthetic construct", "other RNA", [], [], [], None, None, 2),
            ("ACDEFGH", "AA", "synthetic construct", "protein", [], [], [], None, None, 3),
        ]
        summary = get_sequence_summary(sequences)
        assert summary['total_count'] == 3
        assert summary['type_counts']['DNA'] == 1
        assert summary['type_counts']['RNA'] == 1
        assert summary['type_counts']['AA'] == 1
        assert len(summary['details']) == 3


class TestConstants:
    """测试常量定义"""

    def test_base_names(self):
        """测试碱基名称常量"""
        assert 'A' in BASE_NAMES
        assert 'en' in BASE_NAMES['A']
        assert 'zh' in BASE_NAMES['A']

    def test_valid_aa(self):
        """测试有效氨基酸"""
        assert 'A' in VALID_AA
        assert 'Z' in VALID_AA
        assert 'X' in VALID_AA
        assert len(VALID_AA) == 25

    def test_predefined_mods(self):
        """测试预定义修饰"""
        assert 'cm' in PREDEFINED_MODS
        assert 'm' not in PREDEFINED_MODS  # 单字母修饰不在列表中


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
