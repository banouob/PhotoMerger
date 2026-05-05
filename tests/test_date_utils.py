"""
日期工具模組測試

測試民國↔西元轉換函式
"""

import pytest

from utils.date_utils import (
    ad_to_roc,
    format_roc_date,
    get_ad_year_from_roc,
    get_roc_year_from_ad,
    roc_to_ad,
    validate_roc_date_format,
)


class TestRocToAd:
    """測試民國轉西元"""

    def test_basic_conversion(self):
        """測試基本轉換"""
        assert roc_to_ad("1121228") == "20231228"

    def test_year_112(self):
        """測試民國 112 年"""
        assert roc_to_ad("1120101") == "20230101"

    def test_year_114(self):
        """測試民國 114 年"""
        assert roc_to_ad("1140217") == "20250217"

    def test_invalid_input(self):
        """測試無效輸入"""
        with pytest.raises(ValueError):
            roc_to_ad("123")
        with pytest.raises(ValueError):
            roc_to_ad("")
        with pytest.raises(ValueError):
            roc_to_ad("ABCDEFG")


class TestAdToRoc:
    """測試西元轉民國"""

    def test_basic_conversion(self):
        """測試基本轉換"""
        assert ad_to_roc("20231228") == "1121228"

    def test_year_2025(self):
        """測試西元 2025 年"""
        assert ad_to_roc("20250217") == "1140217"

    def test_invalid_input(self):
        """測試無效輸入"""
        with pytest.raises(ValueError):
            ad_to_roc("123")
        with pytest.raises(ValueError):
            ad_to_roc("19001228")  # 1900 < 1912


class TestValidateRocDateFormat:
    """測試民國日期格式驗證"""

    def test_valid_format(self):
        """測試有效格式"""
        assert validate_roc_date_format("1121228") is True
        assert validate_roc_date_format("1140101") is True

    def test_invalid_format(self):
        """測試無效格式"""
        assert validate_roc_date_format("") is False
        assert validate_roc_date_format("123") is False
        assert validate_roc_date_format("ABCDEFG") is False


class TestFormatRocDate:
    """測試民國日期格式化"""

    def test_format(self):
        """測試格式化輸出"""
        assert format_roc_date("1121228") == "112年12月28日"
        assert format_roc_date("1150217") == "115年02月17日"


class TestYearConversion:
    """測試年份轉換"""

    def test_ad_year_from_roc(self):
        """民國年→西元年"""
        assert get_ad_year_from_roc(112) == 2023
        assert get_ad_year_from_roc(114) == 2025
        assert get_ad_year_from_roc(1) == 1912

    def test_roc_year_from_ad(self):
        """西元年→民國年"""
        assert get_roc_year_from_ad(2023) == 112
        assert get_roc_year_from_ad(2025) == 114
        assert get_roc_year_from_ad(1912) == 1
