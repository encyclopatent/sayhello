"""xml_generator.py 模块的单元测试"""
import pytest
from xml_generator import get_base_type, ABBREV_TO_FULLNAME


class TestGetBaseType:
    """测试碱基类型识别"""

    def test_adenosine(self):
        """测试腺苷识别"""
        assert get_base_type("adenosine") == 'a'
        assert get_base_type("Adenosine") == 'a'
        assert get_base_type("ADENOSINE") == 'a'

    def test_uridine(self):
        """测试尿苷识别"""
        assert get_base_type("uridine") == 'u'
        assert get_base_type("Uridine") == 'u'

    def test_cytidine(self):
        """测试胞苷识别"""
        assert get_base_type("cytidine") == 'c'
        assert get_base_type("Cytidine") == 'c'

    def test_guanosine(self):
        """测试鸟苷识别"""
        assert get_base_type("guanosine") == 'g'
        assert get_base_type("Guanosine") == 'g'

    def test_unknown_base(self):
        """测试未知碱基"""
        assert get_base_type("unknown") is None
        assert get_base_type("random") is None

    def test_adenine(self):
        """测试腺嘌呤识别"""
        assert get_base_type("adenine") == 'a'

    def test_uracil(self):
        """测试尿嘧啶识别"""
        assert get_base_type("uracil") == 'u'


class TestAbbrevToFullname:
    """测试缩写到全名映射"""

    def test_cm_mapping(self):
        """测试 cm 映射"""
        assert 'cm' in ABBREV_TO_FULLNAME
        assert ABBREV_TO_FULLNAME['cm'] == '2\'-O-methylcytidine'

    def test_common_modifications(self):
        """测试常见修饰"""
        assert 'm' not in ABBREV_TO_FULLNAME  # 单字母修饰不在此映射中
        assert 'cm' in ABBREV_TO_FULLNAME
        assert 'tm' in ABBREV_TO_FULLNAME
        assert 'p' in ABBREV_TO_FULLNAME

    def test_all_entries_have_base_types(self):
        """测试所有条目都能识别碱基类型"""
        abbrev_count = len(ABBREV_TO_FULLNAME)
        identifiable_count = 0

        for abbrev, fullname in ABBREV_TO_FULLNAME.items():
            base = get_base_type(fullname)
            if base in ['a', 'u', 'c', 'g']:
                identifiable_count += 1

        # 至少 80% 的修饰应该能识别碱基类型
        assert identifiable_count / abbrev_count > 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
