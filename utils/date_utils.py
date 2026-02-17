"""
ROC (Republic of China/Taiwan) 日期轉換工具

提供民國與西元日期格式之間的轉換功能
民國年 = 西元年 - 1911
"""

from typing import Optional


def roc_to_ad(roc_date_str: str) -> str:
    """
    將民國日期轉換為西元日期

    Args:
        roc_date_str: 民國日期字串 (7位數字, 如 "1121228")

    Returns:
        西元日期字串 (8位數字, 如 "20231228")

    Raises:
        ValueError: 如果輸入格式不正確

    Examples:
        >>> roc_to_ad("1121228")
        '20231228'
        >>> roc_to_ad("1150217")
        '20260217'
    """
    if not roc_date_str or len(roc_date_str) != 7:
        raise ValueError(f"民國日期必須為7位數字，收到: {roc_date_str}")

    if not roc_date_str.isdigit():
        raise ValueError(f"民國日期必須全為數字，收到: {roc_date_str}")

    # 解析民國年、月、日
    roc_year = int(roc_date_str[:3])
    month = roc_date_str[3:5]
    day = roc_date_str[5:7]

    # 轉換為西元年
    ad_year = roc_year + 1911

    # 組合成西元日期
    ad_date_str = f"{ad_year:04d}{month}{day}"

    return ad_date_str


def ad_to_roc(ad_date_str: str) -> str:
    """
    將西元日期轉換為民國日期

    Args:
        ad_date_str: 西元日期字串 (8位數字, 如 "20231228")

    Returns:
        民國日期字串 (7位數字, 如 "1121228")

    Raises:
        ValueError: 如果輸入格式不正確或年份小於1912

    Examples:
        >>> ad_to_roc("20231228")
        '1121228'
        >>> ad_to_roc("20260217")
        '1150217'
    """
    if not ad_date_str or len(ad_date_str) != 8:
        raise ValueError(f"西元日期必須為8位數字，收到: {ad_date_str}")

    if not ad_date_str.isdigit():
        raise ValueError(f"西元日期必須全為數字，收到: {ad_date_str}")

    # 解析西元年、月、日
    ad_year = int(ad_date_str[:4])
    month = ad_date_str[4:6]
    day = ad_date_str[6:8]

    # 檢查年份是否有效（民國元年為1912）
    if ad_year < 1912:
        raise ValueError(f"西元年份不能小於1912，收到: {ad_year}")

    # 轉換為民國年
    roc_year = ad_year - 1911

    # 組合成民國日期
    roc_date_str = f"{roc_year:03d}{month}{day}"

    return roc_date_str


def validate_roc_date_format(date_str: str) -> bool:
    """
    驗證民國日期字串是否為7位數字格式 (YYYMMDD)

    Args:
        date_str: 待驗證的民國日期字串

    Returns:
        True 如果格式正確 (7位數字), 否則 False

    Examples:
        >>> validate_roc_date_format("1121228")
        True
        >>> validate_roc_date_format("112-12-28")
        False
        >>> validate_roc_date_format("20231228")
        False
        >>> validate_roc_date_format("")
        False
    """
    if not date_str or len(date_str) != 7:
        return False
    return date_str.isdigit()


def format_roc_date(roc_date_str: str) -> str:
    """
    格式化民國日期為易讀格式

    Args:
        roc_date_str: 民國日期字串 (7位數字, 如 "1121228")

    Returns:
        格式化的日期字串 (如 "112年12月28日")

    Raises:
        ValueError: 如果輸入格式不正確

    Examples:
        >>> format_roc_date("1121228")
        '112年12月28日'
        >>> format_roc_date("1150217")
        '115年02月17日'
    """
    if not validate_roc_date_format(roc_date_str):
        raise ValueError(f"民國日期格式不正確: {roc_date_str}")

    year = roc_date_str[:3]
    month = roc_date_str[3:5]
    day = roc_date_str[5:7]

    return f"{year}年{month}月{day}日"


def get_roc_year_from_ad(ad_year: int) -> int:
    """
    將西元年轉換為民國年

    Args:
        ad_year: 西元年份

    Returns:
        民國年份

    Examples:
        >>> get_roc_year_from_ad(2023)
        112
        >>> get_roc_year_from_ad(2026)
        115
    """
    return ad_year - 1911


def get_ad_year_from_roc(roc_year: int) -> int:
    """
    將民國年轉換為西元年

    Args:
        roc_year: 民國年份

    Returns:
        西元年份

    Examples:
        >>> get_ad_year_from_roc(112)
        2023
        >>> get_ad_year_from_roc(115)
        2026
    """
    return roc_year + 1911
