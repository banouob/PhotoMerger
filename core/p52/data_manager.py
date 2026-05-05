"""
數據管家模組

管理照片列表、歷史記錄和檔名衝突檢測
實現"潔癖模式":智能管理每張原始照片生成的輸出文件
"""

import logging
import os

from core.p52.archive_manager import ArchiveManager

logger = logging.getLogger(__name__)


class DataManager:
    """
    數據管理器

    職責:
    1. 維護目標照片列表
    2. 跟蹤每張照片的處理狀態 (已處理/未處理)
    3. 維護輸出歷史記錄 (潔癖模式)
    4. 檢測檔名衝突
    """

    def __init__(
        self, police_photo_path: str, target_photo_paths: list[str], roc_date_str: str, ad_date_str: str
    ):
        """
        初始化數據管理器

        Args:
            police_photo_path: 警52照片路徑
            target_photo_paths: 目標照片路徑列表
            roc_date_str: 民國日期字串 (7位數字, 如 "1121228")
            ad_date_str: 西元日期字串 (8位數字, 如 "20231228", 供內部使用)
        """
        self.police_photo_path = police_photo_path
        self.target_photo_paths = target_photo_paths
        self.roc_date_str = roc_date_str  # 民國格式，用於顯示
        self.ad_date_str = ad_date_str    # 西元格式，供內部使用
        self.date_str = roc_date_str      # 向後兼容，主要使用民國格式

        # BaseDir: 第一張目標照片所在目錄
        self.base_dir = os.path.dirname(target_photo_paths[0]) if target_photo_paths else ""

        # 歸檔管理器 (使用民國日期)
        self.archive_manager = ArchiveManager(
            self.base_dir, roc_date_str, police_photo_path
        )

        # 照片處理狀態: {照片路徑: True/False}
        self.processing_status: dict[str, bool] = {
            path: False for path in target_photo_paths
        }

        # 輸出歷史記錄 (潔癖模式): {原始照片路徑: 生成的輸出文件路徑}
        # 用於跟蹤每張原始照片最近生成的輸出文件
        self.output_history: dict[str, str] = {}

        # 圖像增強參數: {照片路徑: {brightness, contrast, saturation, sharpness}}
        self.enhancement_params: dict[str, dict] = {
            path: {"brightness": 0, "contrast": 0, "saturation": 0, "sharpness": 0}
            for path in target_photo_paths
        }

        # 當前選中的照片索引
        self.current_index = 0 if target_photo_paths else -1

    def get_current_photo(self) -> str | None:
        """
        獲取當前選中的照片路徑

        Returns:
            當前照片路徑,如果沒有則返回 None
        """
        if 0 <= self.current_index < len(self.target_photo_paths):
            return self.target_photo_paths[self.current_index]
        return None

    def set_current_photo(self, index: int) -> bool:
        """
        設置當前選中的照片

        Args:
            index: 照片索引

        Returns:
            True 如果成功,False 如果索引無效
        """
        if 0 <= index < len(self.target_photo_paths):
            self.current_index = index
            return True
        return False

    def mark_as_processed(self, photo_path: str, output_path: str):
        """
        標記照片為已處理

        Args:
            photo_path: 原始照片路徑
            output_path: 生成的輸出文件路徑
        """
        if photo_path in self.processing_status:
            self.processing_status[photo_path] = True
            self.output_history[photo_path] = output_path

    def is_processed(self, photo_path: str) -> bool:
        """
        檢查照片是否已處理

        Args:
            photo_path: 照片路徑

        Returns:
            True 如果已處理,否則 False
        """
        return self.processing_status.get(photo_path, False)

    def check_conflict(
        self, photo_path: str, proposed_filename: str
    ) -> tuple[bool, bool, str | None]:
        """
        檢查檔名衝突 (潔癖模式核心邏輯)

        邏輯:
        1. 如果文件不存在 → 無衝突
        2. 如果文件存在且在歷史記錄中屬於當前照片 → 允許覆蓋
        3. 如果文件存在但屬於其他照片或不在歷史記錄中 → 報告衝突

        Args:
            photo_path: 當前原始照片路徑
            proposed_filename: 擬使用的檔名 (不含路徑)

        Returns:
            (文件是否存在, 是否衝突, 衝突的歷史照片路徑或None)
            - (False, False, None): 文件不存在,無衝突
            - (True, False, photo_path): 文件存在但屬於當前照片,可覆蓋
            - (True, True, other_photo_path): 文件存在且屬於其他照片,衝突
            - (True, True, None): 文件存在但不在歷史記錄中,衝突
        """
        # 構建完整輸出路徑
        photo_dir = os.path.dirname(photo_path)
        output_path = os.path.join(photo_dir, proposed_filename)

        # 檢查文件是否存在
        if not os.path.exists(output_path):
            return (False, False, None)

        # 文件存在,檢查是否在輸出歷史中
        for original_path, generated_path in self.output_history.items():
            if generated_path == output_path:
                # 找到歷史記錄
                if original_path == photo_path:
                    # 屬於當前照片,允許覆蓋
                    return (True, False, original_path)
                else:
                    # 屬於其他照片,衝突
                    return (True, True, original_path)

        # 文件存在但不在歷史記錄中,衝突
        return (True, True, None)

    def cleanup_old_output(self, photo_path: str):
        """
        清理照片的舊輸出文件 (潔癖模式)

        如果用戶修改了車牌號,舊的輸出文件應該被刪除

        Args:
            photo_path: 原始照片路徑
        """
        if photo_path in self.output_history:
            old_output = self.output_history[photo_path]
            if os.path.exists(old_output):
                try:
                    os.remove(old_output)
                except OSError as e:
                    # 刪除失敗,記錄但不中斷
                    logger.warning(f"無法刪除舊文件 {old_output}: {e}")

    def get_photo_count(self) -> int:
        """
        獲取照片總數

        Returns:
            照片總數
        """
        return len(self.target_photo_paths)

    def get_processed_count(self) -> int:
        """
        獲取已處理照片數量

        Returns:
            已處理的照片數量
        """
        return sum(1 for status in self.processing_status.values() if status)

    def get_photo_info(self, index: int) -> dict[str, any] | None:
        """
        獲取照片信息

        Args:
            index: 照片索引

        Returns:
            包含照片信息的字典,如果索引無效則返回 None
            字典包含: path, filename, processed, output_file
        """
        if not (0 <= index < len(self.target_photo_paths)):
            return None

        photo_path = self.target_photo_paths[index]
        return {
            "path": photo_path,
            "filename": os.path.basename(photo_path),
            "processed": self.is_processed(photo_path),
            "output_file": self.output_history.get(photo_path),
        }

    def get_base_dir(self) -> str:
        """
        獲取基準目錄 (BaseDir)

        Returns:
            BaseDir路徑
        """
        return self.base_dir

    def check_cross_category_conflict(
        self, plate: str, is_severe: bool
    ) -> tuple[bool, str, str]:
        """
        檢查車牌是否存在於相反類別

        Args:
            plate: 車牌號 (已清洗)
            is_severe: True 為嚴重超速, False 為一般超速

        Returns:
            (衝突存在, 相反類別名稱, 衝突文件路徑)
            - (False, "", ""): 無衝突
            - (True, "一般", path): 存在於一般超速
            - (True, "嚴重", path): 存在於嚴重超速
        """
        # 確定相反類別
        opposite_category = "一般" if is_severe else "嚴重"

        # 檢查相反類別的合成照片是否存在
        opposite_composite_path = self.archive_manager.get_composite_path(
            plate, not is_severe
        )

        if os.path.exists(opposite_composite_path):
            return (True, opposite_category, opposite_composite_path)

        return (False, "", "")

    def delete_cross_category_files(self, plate: str, category: str):
        """
        刪除指定類別中該車牌的所有文件

        刪除內容:
        1. 合成照片: {日期}超速後製/{category}/{plate}.JPG
        2. 所有原檔: {日期}超速原檔/{category}/{plate}_*

        Args:
            plate: 車牌號 (已清洗)
            category: 類別 ("一般" 或 "嚴重")
        """
        self.archive_manager.delete_archived_files(plate, category)

    def set_enhancement_params(
        self, photo_path: str, brightness: int, contrast: int, saturation: int, sharpness: int
    ):
        """
        儲存照片的增強參數

        Args:
            photo_path: 照片路徑
            brightness: 亮度 (-100 到 100)
            contrast: 對比度 (-100 到 100)
            saturation: 飽和度 (-100 到 100)
            sharpness: 銳利度 (-100 到 100)
        """
        if photo_path in self.enhancement_params:
            self.enhancement_params[photo_path] = {
                "brightness": brightness,
                "contrast": contrast,
                "saturation": saturation,
                "sharpness": sharpness,
            }

    def get_enhancement_params(self, photo_path: str) -> dict:
        """
        取得照片的增強參數

        Args:
            photo_path: 照片路徑

        Returns:
            包含增強參數的字典 {brightness, contrast, saturation, sharpness}
            如果照片不存在,返回默認值 (全部為 0)
        """
        return self.enhancement_params.get(
            photo_path, {"brightness": 0, "contrast": 0, "saturation": 0, "sharpness": 0}
        )

    @classmethod
    def from_dict(cls, data: dict):
        """
        從專案檔 dict 建立 DataManager 實例

        Args:
            data: load_project() 回傳的 P52 專案資料

        Returns:
            已還原狀態的 DataManager 實例
        """
        dm = cls(
            police_photo_path=data["police_photo_path"],
            target_photo_paths=data["target_photo_paths"],
            roc_date_str=data["roc_date_str"],
            ad_date_str=data["ad_date_str"],
        )
        dm.current_index = data.get("current_index", 0)
        dm.processing_status = data.get("processing_status", {})
        dm.output_history = data.get("output_history", {})
        dm.enhancement_params = data.get("enhancement_params", {})
        return dm
