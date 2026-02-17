"""
檔名驗證和清洗工具

提供檔名清洗功能,確保檔名符合 Windows/Unix 文件系統要求
支援民國 (ROC) 及西元 (AD) 日期格式驗證
"""

import re
from typing import Optional


def sanitize_filename(filename: str) -> str:
    r"""
    清洗檔名,移除或替換非法字元

    將以下非法字元替換為短橫線 (-):
    / \ : * ? " < > |

    Args:
        filename: 原始檔名

    Returns:
        清洗後的檔名

    Examples:
        >>> sanitize_filename("車牌:ABC*123")
        '車牌-ABC-123'
        >>> sanitize_filename("AB<C>D?E")
        'AB-C-D-E'
    """
    # 定義非法字元模式
    illegal_chars = r'[/\\:*?"<>|]'

    # 替換非法字元為短橫線
    sanitized = re.sub(illegal_chars, '-', filename)

    # 移除連續的短橫線
    sanitized = re.sub(r'-+', '-', sanitized)

    # 移除首尾的短橫線
    sanitized = sanitized.strip('-')

    # 確保檔名不為空
    if not sanitized:
        sanitized = "unnamed"

    return sanitized


def validate_filename(filename: str) -> bool:
    """
    驗證檔名是否合法

    檢查檔名是否:
    1. 不為空
    2. 不包含非法字元
    3. 長度在合理範圍內 (1-255 字元)

    Args:
        filename: 待驗證的檔名

    Returns:
        True 如果檔名合法,否則 False

    Examples:
        >>> validate_filename("ABC123")
        True
        >>> validate_filename("AB:C*D")
        False
        >>> validate_filename("")
        False
    """
    if not filename:
        return False

    # 檢查長度
    if len(filename) > 255:
        return False

    # 檢查是否包含非法字元
    illegal_chars = r'[/\\:*?"<>|]'
    if re.search(illegal_chars, filename):
        return False

    return True


def get_safe_filename(filename: str, default: str = "unnamed") -> str:
    """
    獲取安全的檔名

    如果輸入的檔名非法,則返回清洗後的版本;
    如果清洗後仍然為空,則返回默認值

    Args:
        filename: 原始檔名
        default: 默認檔名 (如果清洗後為空)

    Returns:
        安全的檔名

    Examples:
        >>> get_safe_filename("車牌:ABC*123")
        '車牌-ABC-123'
        >>> get_safe_filename("***", "default")
        'default'
    """
    sanitized = sanitize_filename(filename)
    return sanitized if sanitized else default


def validate_date_format(date_str: str, mode: str = "roc") -> bool:
    """
    驗證日期字串格式

    支援兩種模式:
    - "roc": 民國日期 7 位數字 (YYYMMDD)，例如 "1121228"
    - "ad":  西元日期 8 位數字 (YYYYMMDD)，例如 "20231228"

    Args:
        date_str: 待驗證的日期字串
        mode: 驗證模式，"roc" (預設) 或 "ad"

    Returns:
        True 如果格式正確, 否則 False

    Examples:
        >>> validate_date_format("1121228")
        True
        >>> validate_date_format("1121228", "roc")
        True
        >>> validate_date_format("20231228", "ad")
        True
        >>> validate_date_format("112-12-28")
        False
        >>> validate_date_format("")
        False
    """
    if not date_str:
        return False

    if mode == "roc":
        # 民國格式: 7 位數字 (YYYMMDD)
        if len(date_str) != 7:
            return False
        return date_str.isdigit()
    elif mode == "ad":
        # 西元格式: 8 位數字 (YYYYMMDD)
        if len(date_str) != 8:
            return False
        return date_str.isdigit()
    else:
        return False
