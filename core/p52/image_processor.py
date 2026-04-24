"""
影像引擎模組

使用 Pillow 處理圖像:縮放、裁剪、合併和保存
"""

from PIL import Image, ImageDraw, ImageFont
from core.image_enhancement import apply_enhancements as _shared_apply_enhancements
from utils.paths import get_font_path
from typing import Tuple, Optional
import os
import logging

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    圖像處理器

    職責:
    1. 警52照片預處理 (強制縮放到 4096x3000)
    2. ROI 裁剪和縮放
    3. 圖片合併 (8192x3000)
    4. JPG 保存
    """

    # 標準尺寸定義
    TARGET_SIZE = (4096, 3000)  # 目標照片和警52照片的標準尺寸
    OUTPUT_SIZE = (8192, 3000)  # 最終輸出尺寸 (寬度=2倍標準寬度)

    def __init__(self, police_photo_path: str):
        """
        初始化圖像處理器

        Args:
            police_photo_path: 警52照片路徑
        """
        self.police_photo_path = police_photo_path
        self.police_photo = None
        self._load_and_prepare_police_photo()

    def _load_and_prepare_police_photo(self):
        """
        加載並預處理警52照片

        強制縮放到 4096x3000,忽略原始長寬比
        """
        try:
            img = Image.open(self.police_photo_path)
            # 強制縮放到標準尺寸,忽略長寬比
            self.police_photo = img.resize(self.TARGET_SIZE, Image.Resampling.LANCZOS)
        except Exception as e:
            raise RuntimeError(f"無法加載警52照片: {e}")

    @staticmethod
    def apply_enhancements(
        img: Image.Image, brightness: int, contrast: int, saturation: int, sharpness: int
    ) -> Image.Image:
        """
        套用圖像增強效果到 PIL Image

        .. deprecated:: 2.0
            Internal wrapper; actual logic in ``core.image_enhancement.apply_enhancements``.
        """
        return _shared_apply_enhancements(img, brightness, contrast, saturation, sharpness)

    def process_and_merge(
        self,
        target_photo_path: str,
        roi: Tuple[int, int, int, int],
        subimage_size: Tuple[int, int],
        subimage_position: Tuple[int, int],
        output_path: str,
        enhancement_params: Optional[dict] = None,
        officer_text: Optional[str] = None,
    ) -> bool:
        """
        處理目標照片並與警52照片合併

        工作流程:
        1. 加載目標照片
        2. 套用圖像增強 (如果有提供)
        3. 從 ROI 裁剪區域
        4. 縮放裁剪區域到子圖大小
        5. 將子圖貼回目標照片
        6. 創建 8192x3000 畫布
        7. 左側貼處理後的目標圖,右側貼警52圖
        8. 保存為 JPG

        Args:
            target_photo_path: 目標照片路徑
            roi: ROI 區域 (x, y, width, height) - 基於 4096x3000 座標系
            subimage_size: 子圖最終尺寸 (width, height)
            subimage_position: 子圖在目標圖上的位置 (x, y)
            output_path: 輸出文件路徑
            enhancement_params: 可選的增強參數字典 {brightness, contrast, saturation, sharpness}

        Returns:
            True 如果成功,False 如果失敗

        Note:
            所有座標基於 4096x3000 的 Scene 座標系統
        """
        try:
            # 1. 加載目標照片
            target_img = Image.open(target_photo_path)

            # 確保目標照片是 4096x3000
            if target_img.size != self.TARGET_SIZE:
                target_img = target_img.resize(
                    self.TARGET_SIZE, Image.Resampling.LANCZOS
                )

            # 2. 套用增強效果 (如果有提供)
            if enhancement_params:
                target_img = self.apply_enhancements(
                    target_img,
                    enhancement_params.get("brightness", 0),
                    enhancement_params.get("contrast", 0),
                    enhancement_params.get("saturation", 0),
                    enhancement_params.get("sharpness", 0),
                )

            # 3. 從 ROI 裁剪區域
            x, y, w, h = roi
            crop_box = (x, y, x + w, y + h)
            cropped = target_img.crop(crop_box)

            # 4. 縮放裁剪區域到子圖大小
            subimage = cropped.resize(subimage_size, Image.Resampling.LANCZOS)

            # 5. 將子圖貼回目標照片
            # 創建目標照片的副本
            processed_target = target_img.copy()
            sub_x, sub_y = subimage_position
            processed_target.paste(subimage, (sub_x, sub_y))

            # 5b. 繪製警員資訊文字（右上角）
            if officer_text:
                self._draw_officer_text(processed_target, officer_text)

            # 6. 創建 8192x3000 畫布
            canvas = Image.new("RGB", self.OUTPUT_SIZE, (255, 255, 255))

            # 7. 左側貼處理後的目標圖,右側貼警52圖
            canvas.paste(processed_target, (0, 0))  # 左側
            canvas.paste(self.police_photo, (4096, 0))  # 右側

            # 8. 保存為 JPG
            canvas.save(output_path, "JPEG", quality=95)

            return True

        except Exception as e:
            logger.info(f"圖像處理失敗: {e}")
            return False

    def _draw_officer_text(self, img: Image.Image, text: str) -> None:
        """在圖片右上角繪製警員文字（黑色描邊 + 黃色字）"""
        draw = ImageDraw.Draw(img)
        font_size = max(40, int(img.width * 0.015))

        try:
            font = ImageFont.truetype(str(get_font_path()), size=font_size)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        margin = max(30, int(img.width * 0.007))
        x = img.width - text_w - margin
        y = margin

        # 黑色描邊（提升可讀性）
        for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
            draw.text((x + dx, y + dy), text, font=font, fill="#000000")
        draw.text((x, y), text, font=font, fill="#FFFF00")

    def get_police_photo_size(self) -> Tuple[int, int]:
        """
        獲取警52照片的尺寸

        Returns:
            (width, height)
        """
        if self.police_photo:
            return self.police_photo.size
        return (0, 0)

    @staticmethod
    def validate_target_photo(photo_path: str) -> bool:
        """
        驗證目標照片是否有效

        檢查:
        1. 文件是否存在
        2. 是否可以作為圖片打開
        3. (可選) 尺寸是否為 4096x3000

        Args:
            photo_path: 照片路徑

        Returns:
            True 如果有效,否則 False
        """
        if not os.path.exists(photo_path):
            return False

        try:
            img = Image.open(photo_path)
            # 驗證可以打開即可,尺寸會在處理時自動調整
            img.close()
            return True
        except Exception:
            return False

    @staticmethod
    def get_image_info(photo_path: str) -> dict:
        """
        獲取圖片信息

        Args:
            photo_path: 照片路徑

        Returns:
            包含圖片信息的字典:
            - size: (width, height)
            - format: 圖片格式
            - mode: 顏色模式
            - valid: 是否有效
        """
        try:
            img = Image.open(photo_path)
            info = {
                "size": img.size,
                "format": img.format,
                "mode": img.mode,
                "valid": True,
            }
            img.close()
            return info
        except Exception as e:
            return {
                "size": (0, 0),
                "format": None,
                "mode": None,
                "valid": False,
                "error": str(e),
            }
