"""
配置管理器模組

管理外部 JSON 配置檔案的讀寫
提供配置項的統一訪問介面
"""

import copy
import json
import logging
import os
import platform
import shutil
import subprocess
import time
from typing import Any

from utils.paths import get_config_dir

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    配置管理器

    職責:
    1. 載入/儲存 config.json
    2. 提供配置項 get/set 介面
    3. 自動生成預設配置
    4. 支援配置驗證和重置
    """

    # 配置檔名
    CONFIG_FILENAME = "config.json"

    # 預設配置
    DEFAULT_CONFIG = {
        "version": "1.0.0",
        "officers": [
            "陳OO",
            "林OO",
            "王OO"
        ],
        "locations": [
            "臺1線100K",
            "中山路口",
            "高速公路南下80K"
        ],
        "canvas_size": [2400, 1600],
        "info_card_size": [800, 1600],
        "font_size": 32,
        "font_family": "kaiu",
        "default_arrow_color": "#FF0000",
        "default_arrow_width": 15,
        "auto_save": False,
        "output_quality": 95
    }

    def __init__(self):
        """初始化配置管理器"""
        self.config_dir = get_config_dir()
        self.config_path = self.config_dir / self.CONFIG_FILENAME
        self.config: dict[str, Any] = {}

        # 載入配置（首次執行會自動生成）
        self.load_config()

    def load_config(self) -> dict[str, Any]:
        """
        載入配置檔案

        - 如果檔案不存在 → 生成預設配置
        - 如果檔案損壞 → 備份後重置為預設配置

        Returns:
            配置字典
        """
        if not self.config_path.exists():
            # 首次執行,生成預設配置
            logger.info(f"Config file not found, generating default config: {self.config_path}")
            self.config = copy.deepcopy(self.DEFAULT_CONFIG)
            self.save_config()
            return self.config

        try:
            # 讀取配置檔案
            with open(self.config_path, encoding='utf-8') as f:
                loaded_config = json.load(f)

            # 驗證配置完整性（合併預設值）
            self.config = self._merge_with_defaults(loaded_config)

            logger.info(f"Config loaded successfully: {self.config_path}")
            return self.config

        except (OSError, json.JSONDecodeError) as e:
            # 配置檔案損壞,備份後重置
            logger.info(f"Config file corrupted: {e}")
            self._backup_corrupted_config()

            self.config = copy.deepcopy(self.DEFAULT_CONFIG)
            self.save_config()
            return self.config

    def save_config(self, data: dict[str, Any] | None = None):
        """
        儲存配置到檔案

        Args:
            data: 要儲存的配置字典,如果為 None 則儲存當前配置
        """
        if data is not None:
            self.config = data

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(
                    self.config,
                    f,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=False
                )
            logger.info(f"Config saved successfully: {self.config_path}")

        except OSError as e:
            logger.error(f"Failed to save config: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        獲取配置項

        Args:
            key: 配置鍵名
            default: 預設值（如果鍵不存在）

        Returns:
            配置值

        Examples:
            >>> config = ConfigManager()
            >>> officers = config.get("officers", [])
            >>> font_size = config.get("font_size", 32)
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """
        設定配置項

        Args:
            key: 配置鍵名
            value: 配置值

        Note:
            此方法會立即儲存配置到檔案

        Examples:
            >>> config = ConfigManager()
            >>> config.set("font_size", 36)
            >>> config.set("officers", ["張三", "李四"])
        """
        self.config[key] = value
        self.save_config()

    def get_officers(self) -> list[str]:
        """
        獲取承辦人列表（快捷方法）

        Returns:
            承辦人列表
        """
        return self.get("officers", [])

    def add_officer(self, name: str):
        """
        新增承辦人

        Args:
            name: 承辦人姓名
        """
        officers = self.get_officers()
        if name not in officers:
            officers.append(name)
            self.set("officers", officers)

    def get_locations(self) -> list[str]:
        """
        獲取地點列表（快捷方法）

        Returns:
            地點列表
        """
        return self.get("locations", [])

    def add_location(self, location: str):
        """
        新增地點

        Args:
            location: 地點名稱
        """
        locations = self.get_locations()
        if location not in locations:
            locations.append(location)
            self.set("locations", locations)

    def get_canvas_size(self) -> tuple[int, int]:
        """
        獲取畫布尺寸（快捷方法）

        Returns:
            (width, height)
        """
        size = self.get("canvas_size", [2400, 1600])
        return (size[0], size[1])

    def get_info_card_size(self) -> tuple[int, int]:
        """
        獲取資訊卡尺寸（快捷方法）

        Returns:
            (width, height)
        """
        size = self.get("info_card_size", [800, 1600])
        return (size[0], size[1])

    def reset_to_defaults(self):
        """
        重置配置為預設值

        Warning:
            此操作會覆蓋所有使用者配置
        """
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        self.save_config()
        logger.info("Config reset to defaults")

    def open_in_editor(self):
        """
        使用系統預設編輯器開啟配置檔案

        - Windows: notepad
        - macOS: open -e
        - Linux: xdg-open
        """
        try:
            system = platform.system()

            if system == "Windows":
                os.startfile(str(self.config_path))
            elif system == "Darwin":  # macOS
                subprocess.run(["open", "-e", str(self.config_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(self.config_path)])

            logger.info(f"Opened config file in editor: {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to open config file: {e}")
            raise

    def _merge_with_defaults(self, loaded_config: dict[str, Any]) -> dict[str, Any]:
        """
        合併載入的配置與預設配置

        確保所有預設鍵都存在,避免缺失配置導致錯誤

        Args:
            loaded_config: 從檔案載入的配置

        Returns:
            合併後的配置字典
        """
        merged = copy.deepcopy(self.DEFAULT_CONFIG)
        merged.update(loaded_config)
        return merged

    def _backup_corrupted_config(self):
        """
        備份損壞的配置檔案

        備份檔名: config.json.corrupted.{timestamp}
        """
        if self.config_path.exists():
            timestamp = int(time.time())
            backup_path = self.config_path.parent / f"{self.CONFIG_FILENAME}.corrupted.{timestamp}"

            try:
                shutil.copy2(self.config_path, backup_path)
                logger.info(f"Corrupted config backed up to: {backup_path}")
            except Exception as e:
                logger.error(f"Failed to backup corrupted config: {e}")


# === 快捷訪問介面 ===

# 全域性配置管理器例項（單例模式）
_config_manager: ConfigManager | None = None


def get_config() -> ConfigManager:
    """
    獲取全域性配置管理器例項（單例）

    Returns:
        ConfigManager 例項

    Examples:
        >>> from core.grid4.config_manager import get_config
        >>> config = get_config()
        >>> font_size = config.get("font_size")
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


if __name__ == "__main__":
    # 測試配置管理器
    print("=== ConfigManager Test ===")

    config = ConfigManager()

    print("\nCurrent config:")
    print(json.dumps(config.config, ensure_ascii=False, indent=2))

    print("\nOfficers list:", config.get_officers())
    print("Locations list:", config.get_locations())
    print("Canvas size:", config.get_canvas_size())
    print("Font size:", config.get("font_size"))
