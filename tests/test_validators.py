"""
驗證器模組測試

測試 sanitize_filename、validate_filename、get_safe_filename、validate_date_format
"""

from utils.validators import (
    get_safe_filename,
    sanitize_filename,
    validate_date_format,
    validate_filename,
)


class TestSanitizeFilename:
    """測試 sanitize_filename 函數"""

    def test_removes_illegal_characters(self):
        """測試移除非法字元"""
        assert sanitize_filename("ABC:123") == "ABC-123"
        assert sanitize_filename("AB*CD") == "AB-CD"
        assert sanitize_filename("A/B\\C") == "A-B-C"

    def test_removes_consecutive_hyphens(self):
        """測試移除連續的短橫線"""
        assert sanitize_filename("A---B") == "A-B"

    def test_strips_hyphens(self):
        """測試移除首尾短橫線"""
        assert sanitize_filename("-ABC-") == "ABC"

    def test_empty_input_returns_unnamed(self):
        """測試空輸入返回 'unnamed'"""
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("***") == "unnamed"


class TestValidateFilename:
    """測試 validate_filename 函數"""

    def test_valid_filenames(self):
        """測試合法檔名"""
        assert validate_filename("ABC123") is True
        assert validate_filename("車牌-ABC123") is True

    def test_invalid_filenames(self):
        """測試非法檔名"""
        assert validate_filename("AB:C") is False
        assert validate_filename("AB*C") is False
        assert validate_filename("") is False

    def test_too_long_filename(self):
        """測試過長的檔名"""
        assert validate_filename("A" * 256) is False


class TestGetSafeFilename:
    """測試 get_safe_filename 函數"""

    def test_returns_sanitized_filename(self):
        """測試返回清洗後的檔名"""
        assert get_safe_filename("AB:C*D") == "AB-C-D"

    def test_returns_default_for_invalid(self):
        """測試無效輸入返回默認值"""
        assert get_safe_filename("***", "default") == "unnamed"


class TestValidateDateFormat:
    """測試 validate_date_format 函數"""

    def test_valid_roc_date(self):
        """測試有效的民國日期"""
        assert validate_date_format("1121228") is True
        assert validate_date_format("1140217") is True

    def test_invalid_roc_date_wrong_length(self):
        """測試錯誤長度的民國日期"""
        assert validate_date_format("123") is False
        assert validate_date_format("12345678") is False

    def test_invalid_roc_date_non_digit(self):
        """測試包含非數字的民國日期"""
        assert validate_date_format("112-12-28") is False
        assert validate_date_format("112ABCD") is False

    def test_empty_roc_date(self):
        """測試空的民國日期"""
        assert validate_date_format("") is False

    def test_valid_ad_date(self):
        """測試有效的西元日期"""
        assert validate_date_format("20231228", "ad") is True
        assert validate_date_format("20260217", "ad") is True

    def test_invalid_ad_date_wrong_length(self):
        """測試錯誤長度的西元日期"""
        assert validate_date_format("1121228", "ad") is False
        assert validate_date_format("123456789", "ad") is False

    def test_invalid_ad_date_non_digit(self):
        """測試包含非數字的西元日期"""
        assert validate_date_format("2023-12-28", "ad") is False

    def test_invalid_mode(self):
        """測試無效模式"""
        assert validate_date_format("1121228", "invalid") is False

    def test_default_mode_is_roc(self):
        """測試默認模式為 roc"""
        assert validate_date_format("1121228") is True
        assert validate_date_format("1121228", "roc") is True
