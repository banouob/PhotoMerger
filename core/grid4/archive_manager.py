"""
歸檔管理器模組

負責:
1. 建立歸檔目錄結構
2. 強制轉檔 JPG (方案 B)
3. 儲存四格合成圖
"""

import logging
import re  # 引入正則表達式
from datetime import datetime
from pathlib import Path

from PIL import Image

from core.grid4.config_manager import get_config
from core.grid4.image_processor import get_image_processor
from utils.validators import sanitize_filename

logger = logging.getLogger(__name__)


class ArchiveManager:
    """
    歸檔管理器 (方案 B)

    職責:
    1. 建立歸檔目錄結構
    2. 強制將原始圖片轉存為 JPG (1.jpg, 2.jpg, 3.jpg)
    3. 儲存四格合成圖
    """

    def __init__(self):
        """初始化歸檔管理器"""
        self.config = get_config()
        self.image_processor = get_image_processor()

    def archive_case(self, case, output_root: str) -> str:
        """
        歸檔單個案件

        目錄結構 (民國格式):
        {output_root}/{ROC_DATE}_{LOC}_{OFFICER}/
        ├── {ROC_DATE}_闖紅燈原檔/{PLATE}/
        │   ├── 1.jpg
        │   ├── 2.jpg
        │   └── 3.jpg
        └── {ROC_DATE}_闖紅燈後製/
            └── {ROC_DATE}_{PLATE}_53-1.jpg

        Args:
            case: CaseData 物件
            output_root: 輸出根目錄

        Returns:
            合成圖的輸出路徑
        """
        # 提取後設資料
        meta = case.meta_data
        plate = meta.get("plate", "未知車牌").replace(" ", "")
        location = sanitize_filename(meta.get("location", "未知地點"))
        officer = meta.get("officer", "未知人員")

        # === 日期處理 (支援民國格式) ===
        date_str = meta.get("datetime", "")
        # 嘗試解析民國日期字串
        date_short = self._parse_roc_date(date_str)

        if not date_short:
            # 解析失敗或無日期，使用今天 (轉為民國格式)
            now = datetime.now()
            roc_year = now.year - 1911
            date_short = f"{roc_year}{now.strftime('%m%d')}"
            logger.warning(f"Using today's date (ROC) {date_short} because '{date_str}' could not be parsed.")

        # 建立目錄結構
        root_path = Path(output_root)

        # 第一層: {ROC_DATE}_{LOC}_{OFFICER}
        first_level = root_path / f"{date_short}_{location}_{officer}"

        # 第二層: {ROC_DATE}_闖紅燈原檔
        original_folder = first_level / f"{date_short}_闖紅燈原檔"

        # 第三層: {PLATE}
        plate_folder = original_folder / plate
        plate_folder.mkdir(parents=True, exist_ok=True)

        # 後製資料夾
        processed_folder = first_level / f"{date_short}_闖紅燈後製"
        processed_folder.mkdir(parents=True, exist_ok=True)

        # 1. 轉存原始圖片 (方案 B: 強制轉 JPG)
        self._archive_original_images(case.image_paths, plate_folder)

        # 2. 生成四格合成圖
        output_filename = f"{date_short}_{plate}_53-1.jpg"
        output_path = processed_folder / output_filename

        composite = self.image_processor.process_case(case)
        quality = self.config.get("output_quality", 95)
        composite.save(str(output_path), "JPEG", quality=quality)

        logger.info(f"Archived case to: {first_level}")
        logger.info(f"  Original images: {plate_folder}")
        logger.info(f"  Composite image: {output_path}")

        return str(output_path)

    def _parse_roc_date(self, date_str: str) -> str | None:
        """
        解析民國日期字串

        Args:
            date_str: 例如 "112年05月20日..." 或 "112/05/20"

        Returns:
            格式化後的字串 "1120520" 或 None
        """
        if not date_str:
            return None

        # 使用正則表達式提取 年、月、日
        # 支援格式: 112年5月20日, 112/05/20
        match = re.search(r"(\d{2,3})\D+(\d{1,2})\D+(\d{1,2})", date_str)

        if match:
            year, month, day = match.groups()
            # 格式化為 YYYMMDD (補零)
            return f"{int(year)}{int(month):02d}{int(day):02d}"

        return None

    def _archive_original_images(self, image_paths: list, dest_folder: Path):
        """
        歸檔原始圖片 (方案 B: 強制轉 JPG)

        Args:
            image_paths: 原始圖片路徑列表
            dest_folder: 目標資料夾
        """
        quality = self.config.get("output_quality", 95)

        for i, src_path in enumerate(image_paths, 1):
            try:
                # Pillow 讀取
                img = Image.open(src_path)

                # 強制轉 RGB (處理 RGBA/P 等格式)
                img_rgb = img.convert("RGB")

                # 命名為 1.jpg, 2.jpg, 3.jpg
                dest_path = dest_folder / f"{i}.jpg"

                # 儲存 (強制 JPEG)
                img_rgb.save(str(dest_path), "JPEG", quality=quality)

                logger.info(f"  Archived: {Path(src_path).name} → {dest_path.name}")

            except Exception as e:
                logger.info(f"  Failed to archive {src_path}: {e}")

    def _sanitize_filename(self, name: str) -> str:
        """
        清理檔名 (移除非法字元)

        .. deprecated:: 2.0
            Use ``utils.validators.sanitize_filename`` instead.
        """
        return sanitize_filename(name)

    def get_suggested_output_root(self) -> str:
        """
        獲取建議的輸出根目錄

        Returns:
            建議的輸出路徑 (桌面/輸出)
        """
        desktop = Path.home() / "Desktop"
        output_folder = desktop / "PhotoMerger_輸出"
        output_folder.mkdir(exist_ok=True)
        return str(output_folder)


# === 快捷訪問介面 ===

_archive_manager: ArchiveManager | None = None


def get_archive_manager() -> ArchiveManager:
    """
    獲取全域性歸檔管理器例項（單例）

    Returns:
        ArchiveManager 例項
    """
    global _archive_manager
    if _archive_manager is None:
        _archive_manager = ArchiveManager()
    return _archive_manager
