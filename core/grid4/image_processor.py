"""
影象處理器模組

負責:
1. 重繪 ImageState 到原圖 (箭頭/增強)
2. 生成資訊卡 (懸掛縮排)
3. 合成四格拼圖 (2400×1600)
"""

import logging
import math
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from core.grid4.config_manager import get_config
from core.image_enhancement import apply_enhancements as _shared_apply_enhancements
from utils.paths import get_font_path

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    影象處理器

    職責:
    1. 讀取原圖 → 重繪 ImageState → Resize
    2. 生成資訊卡 (懸掛縮排排版)
    3. 合成四格拼圖
    """

    # 輸出尺寸
    CANVAS_WIDTH = 2400
    CANVAS_HEIGHT = 1600

    # 單張圖片尺寸 (2x2 佈局，3:2 比例)
    CELL_WIDTH = 1200
    CELL_HEIGHT = 800

    # 資訊卡尺寸 (右下角，3:2 比例)
    INFO_CARD_WIDTH = 1200
    INFO_CARD_HEIGHT = 800

    def __init__(self):
        """初始化影象處理器"""
        self.config = get_config()
        self._load_font()

    def _load_font(self):
        """載入字型"""
        try:
            font_path = get_font_path()
            # 放大字型以確保資訊卡清晰可讀
            self.font_large = ImageFont.truetype(str(font_path), size=72)
            self.font_medium = ImageFont.truetype(str(font_path), size=48)
            self.font_small = ImageFont.truetype(str(font_path), size=36)
            logger.info(f"Font loaded: {font_path}")
        except Exception as e:
            logger.error(f"Failed to load font: {e}, using default")
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

    def redraw_image(self, image_path: str, image_state) -> Image.Image:
        """
        重繪圖片 (在原圖上繪製 ImageState 的內容)

        Args:
            image_path: 圖片路徑
            image_state: ImageState 物件 (包含箭頭/PIP/增強引數)

        Returns:
            處理後的 PIL Image 物件
        """
        # 讀取原圖
        img = Image.open(image_path).convert("RGB")
        original_width, original_height = img.size

        # 應用影象增強
        img = self._apply_enhancements(
            img,
            image_state.brightness,
            image_state.contrast,
            image_state.saturation,
            image_state.sharpness
        )

        # 備份增強後的基底圖 (用於子圖裁切，避免包含箭頭)
        enhanced_base = img.copy()

        # 建立繪圖物件
        draw = ImageDraw.Draw(img)

        # 繪製箭頭 (相對座標 → 原影象素)
        arrow_color = self.config.get("default_arrow_color", "#FF0000")
        base_arrow_width = self.config.get("default_arrow_width", 5)

        # 根據圖片尺寸自動調整線寬和箭頭大小
        # 假設基準寬度 1200px 對應 5px
        scale_factor = max(1.0, original_width / 1200.0)
        arrow_width = int(base_arrow_width * scale_factor)

        for rel_x1, rel_y1, rel_x2, rel_y2 in image_state.arrows:
            x1 = int(rel_x1 * original_width)
            y1 = int(rel_y1 * original_height)
            x2 = int(rel_x2 * original_width)
            y2 = int(rel_y2 * original_height)

            self._draw_arrow(draw, x1, y1, x2, y2, arrow_color, arrow_width)

        # 繪製子圖 (如果存在)
        if image_state.sub_image:
            self._draw_sub_image(img, enhanced_base, image_state.sub_image)

        return img

    def _apply_enhancements(self, img: Image.Image, brightness: int,
                            contrast: int, saturation: int,
                            sharpness: int) -> Image.Image:
        """
        應用影象增強（委派給共用模組）

        .. deprecated:: 2.0
            Internal wrapper; actual logic in ``core.image_enhancement.apply_enhancements``.
        """
        return _shared_apply_enhancements(img, brightness, contrast, saturation, sharpness)

    def _draw_arrow(self, draw: ImageDraw.Draw, x1: int, y1: int,
                    x2: int, y2: int, color: str, width: int):
        """
        繪製箭頭

        Args:
            draw: ImageDraw 物件
            x1, y1: 起點座標
            x2, y2: 終點座標
            color: 箭頭顏色
            width: 線寬
        """
        # 計算箭頭角度
        angle = math.atan2(y2 - y1, x2 - x1)

        # 加大箭頭尺寸 (線寬的 8 倍)
        arrow_length = width * 8

        # 箭頭角度
        angle1 = angle + math.pi * 0.85
        angle2 = angle - math.pi * 0.85

        x3 = x2 + int(arrow_length * math.cos(angle1))
        y3 = y2 + int(arrow_length * math.sin(angle1))
        x4 = x2 + int(arrow_length * math.cos(angle2))
        y4 = y2 + int(arrow_length * math.sin(angle2))

        # 計算縮短距離（避免粗線覆蓋箭頭三角形尖端）
        shorten = arrow_length * math.cos(math.pi * 0.15)
        short_x2 = x2 - int(shorten * math.cos(angle))
        short_y2 = y2 - int(shorten * math.sin(angle))

        # 繪製縮短後的線段
        draw.line([(x1, y1), (short_x2, short_y2)], fill=color, width=width)

        # 繪製箭頭
        draw.polygon([(x2, y2), (x3, y3), (x4, y4)], fill=color)

    def _draw_sub_image(self, img: Image.Image, source_img: Image.Image, sub_image_data: dict[str, Any]):
        """
        繪製子圖

        Args:
            img: 目標畫布圖片
            source_img: 來源圖片 (用於裁切)
            sub_image_data: 子圖資料 {"source": [x,y,w,h], "target": [x,y,w,h]}
        """
        src = sub_image_data.get("source")
        tgt = sub_image_data.get("target")

        if not src or not tgt:
            return

        w, h = img.size

        # 1. 裁剪
        sx = int(src[0] * w)
        sy = int(src[1] * h)
        sw = int(src[2] * w)
        sh = int(src[3] * h)

        # 邊界檢查
        sx = max(0, sx)
        sy = max(0, sy)
        if sx + sw > w:
            sw = w - sx
        if sy + sh > h:
            sh = h - sy

        if sw <= 0 or sh <= 0:
            return

        crop_img = source_img.crop((sx, sy, sx + sw, sy + sh))

        # 2. 縮放
        tx = int(tgt[0] * w)
        ty = int(tgt[1] * h)
        tw = int(tgt[2] * w)
        th = int(tgt[3] * h)

        if tw <= 0 or th <= 0:
            return

        resized_img = crop_img.resize((tw, th), Image.Resampling.LANCZOS)

        # 3. 貼上
        img.paste(resized_img, (tx, ty))

        # 4. 繪製邊框
        draw = ImageDraw.Draw(img)
        border_width = max(2, int(w * 0.002))  # 0.2% width as border
        draw.rectangle([tx, ty, tx+tw, ty+th], outline="#FFFFFF", width=border_width)

    def create_info_card(self, meta_data: dict[str, Any]) -> Image.Image:
        """
        建立資訊卡 (紅色文字，懸掛縮排排版)

        Args:
            meta_data: 後設資料字典 {plate, location, datetime, officer, violation}

        Returns:
            1200×800 的資訊卡 PIL Image
        """
        # 建立空白資訊卡
        card = Image.new("RGB", (self.INFO_CARD_WIDTH, self.INFO_CARD_HEIGHT), "#FFFFFF")
        draw = ImageDraw.Draw(card)

        # 邊距和行高 (放大後需要更大的行高)
        padding = 40
        line_height = 60
        y = padding

        # 欄位列表 (按照需求重組)
        # 1. 違規車號
        # 2. 違規時間
        # 3. 違規法條 (固定 "53條第1項")
        # 4. 採證人員
        # 5. 違規地點
        fields = [
            ("違規車號：", meta_data.get("plate", "")),
            ("違規時間：", meta_data.get("datetime", "")),
            ("違規法條：", "53條第1項"),
            ("採證人員：", meta_data.get("officer", "")),
            ("違規地點：", meta_data.get("location", "")),
        ]

        for label, value in fields:
            y = self._draw_hanging_indent_field(draw, padding, y, label, value, line_height)
            y += 15  # 欄位間距

        return card

    def _draw_hanging_indent_field(self, draw: ImageDraw.Draw, x: int, y: int,
                                    label: str, value: str,
                                    line_height: int) -> int:
        """
        繪製懸掛縮排欄位 (紅色文字)

        Args:
            draw: ImageDraw 物件
            x: 起始 X 座標
            y: 起始 Y 座標
            label: 標籤 (如 "違規地點：")
            value: 內容
            line_height: 行高

        Returns:
            繪製完成後的 Y 座標
        """
        # 紅色文字
        text_color = "#FF0000"

        max_width = self.INFO_CARD_WIDTH - x * 2

        # 計算標籤寬度
        label_bbox = draw.textbbox((0, 0), label, font=self.font_medium)
        label_width = label_bbox[2] - label_bbox[0]

        # 可用於內容的寬度
        value_max_width = max_width - label_width

        # 換行處理
        value_lines = self._wrap_text(draw, value, self.font_medium, value_max_width)

        if not value_lines:
            value_lines = [""]

        # 第一行: 標籤 + 內容
        first_line = label + value_lines[0]
        draw.text((x, y), first_line, fill=text_color, font=self.font_medium)
        y += line_height

        # 後續行: 縮排 (對齊到標籤後)
        for line in value_lines[1:]:
            draw.text((x + label_width, y), line, fill=text_color, font=self.font_medium)
            y += line_height

        return y

    def _wrap_text(self, draw: ImageDraw.Draw, text: str,
                   font: ImageFont.FreeTypeFont,
                   max_width: int) -> list[str]:
        """
        文字換行

        Args:
            draw: ImageDraw 物件
            text: 要換行的文字
            font: 字型
            max_width: 最大寬度

        Returns:
            換行後的行列表
        """
        if not text:
            return [""]

        lines = []
        current_line = ""

        for char in text:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font)
            test_width = bbox[2] - bbox[0]

            if test_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char

        if current_line:
            lines.append(current_line)

        return lines if lines else [""]

    def merge_four_grid(self, images: list[Image.Image],
                        info_card: Image.Image) -> Image.Image:
        """
        合成四格拼圖 (2x2 佈局)

        佈局:
        ┌─────────┬─────────┐
        │  圖1    │   圖2   │
        │ (遠景)  │  (過程) │
        ├─────────┼─────────┤
        │  圖3    │ 資訊卡  │
        │ (特寫)  │        │
        └─────────┴─────────┘

        每格 1200x800 (3:2 比例)，6000x4000 原圖縮放後剛好填滿，無白邊

        Args:
            images: 3 張處理後的圖片列表
            info_card: 資訊卡圖片

        Returns:
            2400×1600 的合成圖
        """
        # 建立畫布
        canvas = Image.new("RGB", (self.CANVAS_WIDTH, self.CANVAS_HEIGHT), "#FFFFFF")

        # 2x2 佈局位置: 左上, 右上, 左下
        positions = [
            (0, 0),                           # 圖 1 (左上)
            (self.CELL_WIDTH, 0),             # 圖 2 (右上)
            (0, self.CELL_HEIGHT)             # 圖 3 (左下)
        ]

        # 縮放並放置 3 張圖片
        for i, img in enumerate(images[:3]):
            # 縮放到 1200×800 (保持寬高比，3:2 圖片剛好填滿)
            resized = self._resize_to_fit(img, self.CELL_WIDTH, self.CELL_HEIGHT)

            # 計算位置 (居中放置，以防微小比例誤差)
            x, y = positions[i]
            offset_x = (self.CELL_WIDTH - resized.width) // 2
            offset_y = (self.CELL_HEIGHT - resized.height) // 2

            canvas.paste(resized, (x + offset_x, y + offset_y))

        # 放置資訊卡到右下角
        info_x = self.CELL_WIDTH
        info_y = self.CELL_HEIGHT
        canvas.paste(info_card, (info_x, info_y))

        return canvas

    def _resize_to_fit(self, img: Image.Image, max_width: int,
                       max_height: int) -> Image.Image:
        """
        縮放圖片以適應指定尺寸 (保持寬高比)

        Args:
            img: PIL Image
            max_width: 最大寬度
            max_height: 最大高度

        Returns:
            縮放後的 PIL Image
        """
        ratio = min(max_width / img.width, max_height / img.height)
        new_width = int(img.width * ratio)
        new_height = int(img.height * ratio)

        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def process_case(self, case) -> Image.Image:
        """
        處理完整案件 (重繪 + 資訊卡 + 合成)

        Args:
            case: CaseData 物件

        Returns:
            合成後的四格拼圖 PIL Image
        """
        # 重繪 3 張圖片
        processed_images = []
        for i, img_path in enumerate(case.image_paths[:3]):
            image_state = case.image_states[i] if i < len(case.image_states) else None

            if image_state:
                processed = self.redraw_image(img_path, image_state)
            else:
                processed = Image.open(img_path).convert("RGB")

            processed_images.append(processed)

        # 建立資訊卡
        info_card = self.create_info_card(case.meta_data)

        # 合成四格拼圖
        result = self.merge_four_grid(processed_images, info_card)

        return result


# === 快捷訪問介面 ===

_image_processor: ImageProcessor | None = None


def get_image_processor() -> ImageProcessor:
    """
    獲取全域性影象處理器例項（單例）

    Returns:
        ImageProcessor 例項
    """
    global _image_processor
    if _image_processor is None:
        _image_processor = ImageProcessor()
    return _image_processor


if __name__ == "__main__":
    # 測試影象處理器
    print("=== ImageProcessor Test ===")

    processor = ImageProcessor()

    # 測試資訊卡生成
    test_meta = {
        "plate": "ABC-1234",
        "location": "臺北市中正區重慶南路一段122號前方路口",
        "datetime": "2026-01-05 14:30:00",
        "officer": "陳大明",
        "violation": "闖紅燈"
    }

    info_card = processor.create_info_card(test_meta)
    info_card.save("tmp/test_info_card.jpg", "JPEG", quality=95)
    print("Info card saved to tmp/test_info_card.jpg")
