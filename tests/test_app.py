"""app.py 模块的单元测试"""
import pytest
import os
from app import allowed_file, ALLOWED_EXTENSIONS


class TestFileValidation:
    """测试文件验证功能"""

    def test_allowed_xlsx_file(self):
        """测试允许的 xlsx 文件"""
        assert allowed_file("test.xlsx") is True

    def test_allowed_xls_file(self):
        """测试允许的 xls 文件"""
        assert allowed_file("test.xls") is True

    def test_uppercase_extension(self):
        """测试大写扩展名"""
        assert allowed_file("test.XLSX") is True

    def test_mixed_case_extension(self):
        """测试混合大小写扩展名"""
        assert allowed_file("test.Xlsx") is True

    def test_disallowed_extension(self):
        """测试不允许的扩展名"""
        assert allowed_file("test.pdf") is False
        assert allowed_file("test.txt") is False
        assert allowed_file("test.doc") is False

    def test_no_extension(self):
        """测试无扩展名"""
        assert allowed_file("test") is False
        assert allowed_file("test.") is False

    def test_multiple_dots(self):
        """测试多个点"""
        assert allowed_file("test.file.xlsx") is True

    def test_allowed_extensions_constant(self):
        """测试 ALLOWED_EXTENSIONS 常量"""
        assert 'xlsx' in ALLOWED_EXTENSIONS
        assert 'xls' in ALLOWED_EXTENSIONS
        assert len(ALLOWED_EXTENSIONS) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
