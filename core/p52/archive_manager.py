"""
歸檔管理器模組

負責日期歸檔系統的文件操作
實現文件夾結構管理、警52照片複製、原檔歸檔等功能
"""

import os
import shutil
import glob
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ArchiveManager:
    """
    歸檔管理器

    職責:
    1. 創建並管理基於日期的文件夾結構
    2. 複製警52照片 (會話期間只複製一次)
    3. 歸檔目標照片原檔 (重命名為 {車牌}_{原檔名})
    4. 生成合成照片路徑
    5. 刪除歸檔文件
    """

    def __init__(self, base_dir: str, date_str: str, police_photo_path: str):
        """
        初始化歸檔管理器

        Args:
            base_dir: 基準目錄 (第一張目標照片所在目錄)
            date_str: 民國日期字串 (7位數字, 如 "1121228")
            police_photo_path: 警52照片路徑
        """
        self.base_dir = base_dir
        self.date_str = date_str
        self.police_photo_path = police_photo_path
        self._police_copied = False  # 跟蹤警52照片是否已複製
        self._folder_structure = self._build_folder_paths()

    def _build_folder_paths(self) -> Dict[str, str]:
        """
        構建所有文件夾路徑

        Returns:
            包含所有文件夾路徑的字典
        """
        original_root = os.path.join(self.base_dir, f"{self.date_str}超速原檔")
        composite_root = os.path.join(self.base_dir, f"{self.date_str}超速後製")

        return {
            "original_root": original_root,
            "composite_root": composite_root,
            "police_original": os.path.join(original_root, "警52"),
            "original_normal": os.path.join(original_root, "一般"),
            "original_severe": os.path.join(original_root, "嚴重"),
            "composite_normal": os.path.join(composite_root, "一般"),
            "composite_severe": os.path.join(composite_root, "嚴重"),
        }

    def ensure_folders_exist(self):
        """創建所有必要的文件夾"""
        for folder_path in self._folder_structure.values():
            os.makedirs(folder_path, exist_ok=True)

    def copy_police_photo_once(self) -> bool:
        """
        複製警52照片到歸檔文件夾 (會話期間只複製一次)

        Returns:
            True 如果成功, False 如果失敗
        """
        if self._police_copied:
            return True  # 已複製

        try:
            police_folder = self._folder_structure["police_original"]
            os.makedirs(police_folder, exist_ok=True)

            # 構建目標文件路徑
            police_filename = os.path.basename(self.police_photo_path)
            dest_path = os.path.join(police_folder, police_filename)

            # 關鍵：檢查目標文件是否存在 (而非檢查文件夾是否為空)
            # 避免被系統文件 (如 Thumbs.db) 誤導
            if os.path.exists(dest_path):
                self._police_copied = True
                return True  # 文件已存在, 跳過複製

            # 複製文件並保留元數據
            shutil.copy2(self.police_photo_path, dest_path)

            self._police_copied = True
            return True

        except Exception as e:
            logger.warning(f"無法複製警52照片: {e}")
            return False

    def archive_target_original(
        self, target_path: str, plate: str, is_severe: bool
    ) -> bool:
        """
        歸檔目標照片原檔

        Args:
            target_path: 目標照片原始路徑
            plate: 車牌號 (已清洗)
            is_severe: True 為嚴重超速, False 為一般超速

        Returns:
            True 如果成功, False 如果失敗
        """
        try:
            category = "嚴重" if is_severe else "一般"
            original_folder = os.path.join(
                self._folder_structure["original_root"], category
            )
            os.makedirs(original_folder, exist_ok=True)

            # 構建檔名: {車牌}_{原檔名}
            original_name = os.path.basename(target_path)
            dest_filename = f"{plate}_{original_name}"
            dest_path = os.path.join(original_folder, dest_filename)

            # 邊緣情況處理: 原檔命名衝突
            # 如果目標文件已存在 (可能來自不同文件夾的同名照片)
            # 在檔名後添加序號 _1, _2 等
            if os.path.exists(dest_path):
                base_name, ext = os.path.splitext(dest_filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_filename = f"{base_name}_{counter}{ext}"
                    dest_path = os.path.join(original_folder, dest_filename)
                    counter += 1
                    if counter > 100:  # 防止無限循環
                        raise RuntimeError(f"原檔命名衝突超過100次: {dest_filename}")

            # 複製並保留元數據
            shutil.copy2(target_path, dest_path)
            return True

        except Exception as e:
            logger.error(f"無法歸檔原檔: {e}")
            return False

    def get_composite_path(self, plate: str, is_severe: bool) -> str:
        """
        獲取合成照片的完整路徑

        Args:
            plate: 車牌號 (已清洗)
            is_severe: True 為嚴重超速, False 為一般超速

        Returns:
            合成照片的完整路徑
        """
        category = "嚴重" if is_severe else "一般"
        composite_folder = os.path.join(
            self._folder_structure["composite_root"], category
        )
        # 合成照片統一使用大寫 .JPG 擴展名
        return os.path.join(composite_folder, f"{plate}.JPG")

    def check_composite_exists(self, plate: str, category: str) -> bool:
        """
        檢查合成照片是否存在於指定類別

        Args:
            plate: 車牌號 (已清洗)
            category: 類別 ("一般" 或 "嚴重")

        Returns:
            True 如果文件存在, 否則 False
        """
        is_severe = category == "嚴重"
        composite_path = self.get_composite_path(plate, is_severe)
        return os.path.exists(composite_path)

    def delete_archived_files(self, plate: str, category: str):
        """
        刪除指定類別中該車牌的所有歸檔文件

        刪除內容:
        1. 合成照片: {日期}超速後製/{category}/{plate}.JPG
        2. 所有原檔: {日期}超速原檔/{category}/{plate}_*

        Args:
            plate: 車牌號 (已清洗)
            category: 類別 ("一般" 或 "嚴重")
        """
        # 1. 刪除合成照片
        is_severe = category == "嚴重"
        composite_path = self.get_composite_path(plate, is_severe)

        if os.path.exists(composite_path):
            try:
                os.remove(composite_path)
                logger.info(f"已刪除合成照片: {composite_path}")
            except OSError as e:
                logger.warning(f"無法刪除合成照片 {composite_path}: {e}")

        # 2. 刪除所有關聯原檔 (使用glob匹配所有 {plate}_* 文件)
        original_folder = os.path.join(
            self._folder_structure["original_root"], category
        )
        original_pattern = os.path.join(original_folder, f"{plate}_*")
        originals = glob.glob(original_pattern)

        for orig in originals:
            try:
                os.remove(orig)
                logger.info(f"已刪除原檔: {orig}")
            except OSError as e:
                logger.warning(f"無法刪除原檔 {orig}: {e}")
