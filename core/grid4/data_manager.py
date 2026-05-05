"""
資料管理器模組

負責批次案件管理、圖片排序、編輯狀態追蹤
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)


class CaseStatus(Enum):
    """案件狀態"""
    PENDING = "pending"  # 待處理（3張圖片）
    ERROR = "error"      # 錯誤（圖片數量 != 3）
    DONE = "done"        # 已完成


@dataclass
class ImageState:
    """
    單張圖片的編輯狀態

    包含箭頭、標註點、影象調整引數等
    """
    arrows: list[tuple[float, float, float, float]] = field(default_factory=list)
    sub_image: dict[str, Any] | None = None  # {"source": [x,y,w,h], "target": [x,y,w,h]}
    brightness: int = 0
    contrast: int = 0
    saturation: int = 0
    sharpness: int = 0


@dataclass
class CaseData:
    """
    案件資料（3張圖片為一組）

    Attributes:
        folder_path: 案件資料夾路徑
        image_paths: 圖片路徑列表（最多3張）
        image_states: 對應每張圖片的編輯狀態
        meta_data: 案件後設資料（承辦人、地點、時間等）
        status: 案件狀態
    """
    folder_path: str = ""
    image_paths: list[str] = field(default_factory=list)
    image_states: list[ImageState] = field(default_factory=lambda: [
        ImageState(), ImageState(), ImageState()
    ])
    meta_data: dict[str, Any] = field(default_factory=dict)
    status: CaseStatus = CaseStatus.PENDING


class DataManager:
    """
    資料管理器

    職責:
    1. 掃描根目錄的所有子資料夾（每個子資料夾 = 一個案件）
    2. 驗證圖片數量（3 張 = PENDING，其他 = ERROR）
    3. 按 EXIF 時間排序圖片（降級為檔名）
    4. 提供拖曳排序介面
    5. 追蹤案件處理狀態
    """

    # 支援的圖片格式
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}

    def __init__(self):
        """初始化資料管理器"""
        self.cases: list[CaseData] = []
        self.current_case_index: int = -1

    def scan_root_folder(self, root_folder: str) -> int:
        """
        掃描根目錄的所有子資料夾，每個子資料夾視為一個案件

        支援兩種模式：
        1. 批次模式：根目錄包含多個子資料夾，每個子資料夾是一個案件
        2. 單案件模式：根目錄本身就包含圖片（沒有子資料夾）

        Args:
            root_folder: 根目錄路徑

        Returns:
            掃描到的案件數量

        Examples:
            >>> dm = DataManager()
            >>> count = dm.scan_root_folder("D:/超速案件/20240115")
            >>> logger.info(f"Found {count} cases")
        """
        self.cases.clear()
        self.current_case_index = -1

        root_path = Path(root_folder)

        if not root_path.exists() or not root_path.is_dir():
            logger.info(f"Root folder does not exist: {root_folder}")
            return 0

        # 先檢查根目錄本身是否包含圖片（單案件模式）
        root_images = self._scan_images_in_folder(root_path)
        if root_images:
            # 單案件模式：根目錄本身就是一個案件
            case = CaseData(
                folder_path=str(root_path),
                image_paths=root_images,
                status=CaseStatus.PENDING if len(root_images) == 3 else CaseStatus.ERROR
            )

            if case.status == CaseStatus.PENDING:
                self._sort_images(case)

            self.cases.append(case)
            logger.info(f"Single case mode: found {len(root_images)} images in {root_folder}")
        else:
            # 批次模式：掃描所有子資料夾
            for subfolder in sorted(root_path.iterdir()):
                if not subfolder.is_dir():
                    continue

                # 掃描子資料夾中的圖片檔案
                image_files = self._scan_images_in_folder(subfolder)

                # 建立案件資料
                case = CaseData(
                    folder_path=str(subfolder),
                    image_paths=image_files,
                    status=CaseStatus.PENDING if len(image_files) == 3 else CaseStatus.ERROR
                )

                # 如果是有效案件（3張圖片），自動排序
                if case.status == CaseStatus.PENDING:
                    self._sort_images(case)

                self.cases.append(case)

            logger.info(f"Batch mode: scanned {len(self.cases)} cases from {root_folder}")

        # 自動選中第一個待處理案件
        if self.cases:
            self.current_case_index = 0

        return len(self.cases)

    def _scan_images_in_folder(self, folder: Path) -> list[str]:
        """
        掃描資料夾中的圖片檔案

        Args:
            folder: 資料夾路徑

        Returns:
            圖片檔案路徑列表（絕對路徑）
        """
        image_files = []

        for file_path in folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.IMAGE_EXTENSIONS:
                image_files.append(str(file_path))

        return image_files

    def _sort_images(self, case: CaseData):
        """
        按 EXIF 拍攝時間排序圖片（降級為檔名）

        排序策略:
        1. 優先使用 EXIF DateTime / DateTimeOriginal
        2. 降級使用檔名字典序
        3. 同步交換 image_paths 和 image_states

        Args:
            case: 案件資料
        """
        if len(case.image_paths) <= 1:
            return

        # 提取 EXIF 時間或檔名作為排序鍵
        sort_keys = []
        for img_path in case.image_paths:
            exif_time = self._extract_exif_datetime(img_path)
            if exif_time:
                sort_keys.append((exif_time, img_path))
            else:
                # 降級為檔名
                filename = os.path.basename(img_path)
                sort_keys.append((filename, img_path))

        # 排序
        sort_keys.sort(key=lambda x: x[0])

        # 建立排序後的索引對映
        sorted_paths = [path for _, path in sort_keys]

        # 根據新順序重新排列 image_states
        old_to_new_index = {}
        for new_idx, path in enumerate(sorted_paths):
            old_idx = case.image_paths.index(path)
            old_to_new_index[old_idx] = new_idx

        # 重新排列 image_states
        sorted_states = [ImageState() for _ in range(len(case.image_states))]
        for old_idx, new_idx in old_to_new_index.items():
            if old_idx < len(case.image_states):
                sorted_states[new_idx] = case.image_states[old_idx]

        # 更新案件資料
        case.image_paths = sorted_paths
        case.image_states = sorted_states[:len(sorted_paths)]

    def _extract_exif_datetime(self, image_path: str) -> str | None:
        """
        提取 EXIF 拍攝時間

        Args:
            image_path: 圖片檔案路徑

        Returns:
            EXIF 時間字串（格式: "YYYY:MM:DD HH:MM:SS"），失敗返回 None
        """
        try:
            img = Image.open(image_path)
            exif_data = img.getexif()

            if not exif_data:
                return None

            # 嘗試讀取時間標籤（優先順序: DateTimeOriginal > DateTime > DateTimeDigitized）
            time_tags = [36867, 306, 36868]  # EXIF 標籤 ID

            for tag_id in time_tags:
                if tag_id in exif_data:
                    return exif_data[tag_id]

            return None

        except Exception:
            # 無法讀取 EXIF（檔案損壞、無 EXIF 等）
            return None

    def convert_to_roc_datetime(self, exif_datetime: str) -> str:
        """
        將 EXIF 時間轉換為民國年格式

        Args:
            exif_datetime: EXIF 時間字串 (格式: "YYYY:MM:DD HH:MM:SS")

        Returns:
            民國年格式字串 (格式: "YYY年MM月DD日HH時MM分")
        """
        if not exif_datetime:
            return ""

        try:
            # 解析 EXIF 格式: "YYYY:MM:DD HH:MM:SS"
            parts = exif_datetime.split(" ")
            date_parts = parts[0].split(":")
            time_parts = parts[1].split(":") if len(parts) > 1 else ["00", "00", "00"]

            year = int(date_parts[0])
            month = int(date_parts[1])
            day = int(date_parts[2])
            hour = int(time_parts[0])
            minute = int(time_parts[1])

            # 轉換為民國年
            roc_year = year - 1911

            # 格式化 (補零)
            return f"{roc_year}年{month:02d}月{day:02d}日{hour:02d}時{minute:02d}分"

        except (ValueError, IndexError):
            # 解析失敗，返回原始字串
            return exif_datetime

    def swap_images(self, case: CaseData, idx1: int, idx2: int):
        """
        交換案件中兩張圖片的位置（拖曳排序）

        - 交換 image_paths[idx1] ↔ image_paths[idx2]
        - 交換 image_states[idx1] ↔ image_states[idx2]
        - 確保編輯內容跟著圖片走

        Args:
            case: 案件資料
            idx1: 第一張圖片的索引
            idx2: 第二張圖片的索引

        Examples:
            >>> dm.swap_images(case, 0, 2)  # 交換第1張和第3張
        """
        if idx1 < 0 or idx1 >= len(case.image_paths):
            raise IndexError(f"Index {idx1} out of range")

        if idx2 < 0 or idx2 >= len(case.image_paths):
            raise IndexError(f"Index {idx2} out of range")

        # 交換圖片路徑
        case.image_paths[idx1], case.image_paths[idx2] = \
            case.image_paths[idx2], case.image_paths[idx1]

        # 交換編輯狀態
        case.image_states[idx1], case.image_states[idx2] = \
            case.image_states[idx2], case.image_states[idx1]

        logger.info(f"Swapped images at index {idx1} and {idx2}")

    def get_current_case(self) -> CaseData | None:
        """
        獲取當前選中的案件

        Returns:
            當前案件資料，如果沒有案件返回 None
        """
        if 0 <= self.current_case_index < len(self.cases):
            return self.cases[self.current_case_index]
        return None

    def set_current_case(self, index: int) -> bool:
        """
        切換當前案件（需觸發狀態儲存）

        Args:
            index: 案件索引

        Returns:
            True 如果切換成功，False 如果索引無效
        """
        if 0 <= index < len(self.cases):
            self.current_case_index = index
            logger.info(f"Switched to case {index}: {self.cases[index].folder_path}")
            return True
        return False

    def mark_case_as_done(self, case: CaseData):
        """
        標記案件為已完成

        Args:
            case: 案件資料
        """
        case.status = CaseStatus.DONE
        logger.info(f"Case marked as done: {case.folder_path}")

    def get_case_summary(self) -> dict[str, int]:
        """
        獲取案件統計摘要

        Returns:
            {"total": N, "pending": N, "done": N, "error": N}
        """
        summary = {
            "total": len(self.cases),
            "pending": 0,
            "done": 0,
            "error": 0
        }

        for case in self.cases:
            if case.status == CaseStatus.PENDING:
                summary["pending"] += 1
            elif case.status == CaseStatus.DONE:
                summary["done"] += 1
            elif case.status == CaseStatus.ERROR:
                summary["error"] += 1

        return summary

    def get_next_pending_case_index(self) -> int | None:
        """
        獲取下一個待處理案件的索引

        Returns:
            下一個待處理案件的索引，如果沒有返回 None
        """
        for i, case in enumerate(self.cases):
            if case.status == CaseStatus.PENDING:
                return i
        return None


# === 快捷訪問介面 ===

_data_manager: DataManager | None = None


def get_data_manager() -> DataManager:
    """
    獲取全域性資料管理器例項（單例）

    Returns:
        DataManager 例項

    Examples:
        >>> from core.grid4.data_manager import get_data_manager
        >>> dm = get_data_manager()
        >>> dm.scan_root_folder("D:/案件資料夾")
    """
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager


if __name__ == "__main__":
    # 測試資料管理器
    print("=== DataManager Test ===")

    dm = DataManager()

    # 測試資料結構
    test_case = CaseData(
        folder_path="D:/test/case1",
        image_paths=["img1.jpg", "img2.jpg", "img3.jpg"],
        status=CaseStatus.PENDING
    )

    print(f"\nTest case: {test_case.folder_path}")
    print(f"Status: {test_case.status.value}")
    print(f"Images: {len(test_case.image_paths)}")

    # 測試交換
    print("\nBefore swap:")
    print(f"  Images: {test_case.image_paths}")

    dm.swap_images(test_case, 0, 2)

    print("After swap:")
    print(f"  Images: {test_case.image_paths}")
