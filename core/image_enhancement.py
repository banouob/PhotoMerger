"""
影象增強模組 (共用層)

提供:
1. apply_enhancements() - 獨立的影象增強函式
2. ImageEnhancementWorker - 背景執行緒 Worker
3. ImageEnhancementManager - 管理 Worker 生命週期
"""


from PIL import Image, ImageEnhance
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QImage


def apply_enhancements(img: Image.Image, brightness: int = 0,
                       contrast: int = 0, saturation: int = 0,
                       sharpness: int = 0) -> Image.Image:
    """
    應用影象增強 (獨立函式，不依賴 QThread)

    Args:
        img: PIL Image
        brightness: 亮度 (-100 ~ 100)
        contrast: 對比度 (-100 ~ 100)
        saturation: 飽和度 (-100 ~ 100)
        sharpness: 銳化 (-100 ~ 100)

    Returns:
        處理後的 PIL Image

    Examples:
        >>> from PIL import Image
        >>> img = Image.new("RGB", (100, 100), "white")
        >>> result = apply_enhancements(img, brightness=50, contrast=20)
    """
    result = img.copy()

    if brightness != 0:
        enhancer = ImageEnhance.Brightness(result)
        factor = 1.0 + (brightness / 100.0)
        result = enhancer.enhance(max(0.0, factor))

    if contrast != 0:
        enhancer = ImageEnhance.Contrast(result)
        factor = 1.0 + (contrast / 100.0)
        result = enhancer.enhance(max(0.0, factor))

    if saturation != 0:
        enhancer = ImageEnhance.Color(result)
        factor = 1.0 + (saturation / 100.0)
        result = enhancer.enhance(max(0.0, factor))

    if sharpness != 0:
        enhancer = ImageEnhance.Sharpness(result)
        factor = 1.0 + (sharpness / 100.0)
        result = enhancer.enhance(max(0.0, factor))

    return result


class ImageEnhancementWorker(QObject):
    """
    影象增強 Worker（執行在獨立執行緒）

    功能:
    - 在後臺執行緒處理影象增強
    - 使用 Request ID 機制防止串圖
    - 支援亮度、對比度、飽和度、銳化調整
    """

    # 訊號：處理請求 (brightness, contrast, saturation, sharpness, width, height, request_id)
    request_processing = pyqtSignal(int, int, int, int, int, int, int)

    # 訊號：處理完成 (QImage, request_id)
    finished = pyqtSignal(QImage, int)

    def __init__(self):
        """初始化 Worker"""
        super().__init__()

        self.original_pil_image: Image.Image | None = None
        self.current_request_id = 0

    def set_original_image(self, pil_image: Image.Image):
        """
        設定原始圖片

        Args:
            pil_image: PIL Image 物件
        """
        self.original_pil_image = pil_image.copy()

    @pyqtSlot(int, int, int, int, int, int, int)
    def process_image(self, brightness: int, contrast: int, saturation: int,
                      sharpness: int, width: int, height: int, request_id: int):
        """
        處理影象增強

        Args:
            brightness: 亮度調整 (-100 ~ 100)
            contrast: 對比度調整 (-100 ~ 100)
            saturation: 飽和度調整 (-100 ~ 100)
            sharpness: 銳化調整 (-100 ~ 100)
            width: 目標寬度
            height: 目標高度
            request_id: 請求 ID
        """
        if self.original_pil_image is None:
            return

        try:
            # 使用共用 apply_enhancements 函式
            img = apply_enhancements(
                self.original_pil_image,
                brightness, contrast, saturation, sharpness
            )

            # 縮放到目標尺寸（如果需要）
            if width > 0 and height > 0:
                img = img.resize((width, height), Image.Resampling.LANCZOS)

            # 轉換為 QImage
            img_rgb = img.convert("RGB")
            data = img_rgb.tobytes("raw", "RGB")
            qimage = QImage(
                data,
                img_rgb.width,
                img_rgb.height,
                img_rgb.width * 3,
                QImage.Format.Format_RGB888
            )

            # 複製 QImage（避免資料被釋放）
            qimage_copy = qimage.copy()

            # 傳送完成訊號
            self.finished.emit(qimage_copy, request_id)

        except Exception as e:
            print(f"影象增強處理錯誤: {e}")


class ImageEnhancementManager(QObject):
    """
    影象增強管理器

    功能:
    - 管理 Worker 執行緒
    - 防抖處理
    - Request ID 管理
    """

    # 訊號：增強完成 (QImage)
    enhancement_finished = pyqtSignal(QImage)

    def __init__(self):
        """初始化管理器"""
        super().__init__()

        # 建立 Worker 和執行緒
        self.worker = ImageEnhancementWorker()
        self.thread = QThread()

        # 移動 Worker 到執行緒
        self.worker.moveToThread(self.thread)

        # 連線訊號
        self.worker.request_processing.connect(self.worker.process_image)
        self.worker.finished.connect(self._on_enhancement_finished)

        # 啟動執行緒
        self.thread.start()

        # Request ID 管理
        self.current_request_id = 0
        self.latest_request_id = 0

    def set_original_image(self, pil_image: Image.Image):
        """
        設定原始圖片

        Args:
            pil_image: PIL Image 物件
        """
        self.worker.set_original_image(pil_image)

    def request_enhancement(self, brightness: int, contrast: int,
                            saturation: int, sharpness: int,
                            width: int, height: int):
        """
        請求影象增強

        Args:
            brightness: 亮度調整 (-100 ~ 100)
            contrast: 對比度調整 (-100 ~ 100)
            saturation: 飽和度調整 (-100 ~ 100)
            sharpness: 銳化調整 (-100 ~ 100)
            width: 目標寬度
            height: 目標高度
        """
        # 生成新 Request ID
        self.current_request_id += 1
        self.latest_request_id = self.current_request_id

        # 傳送處理請求
        self.worker.request_processing.emit(
            brightness, contrast, saturation, sharpness,
            width, height, self.current_request_id
        )

    @pyqtSlot(QImage, int)
    def _on_enhancement_finished(self, qimage: QImage, request_id: int):
        """
        增強完成槽函式

        Args:
            qimage: 處理後的 QImage
            request_id: 請求 ID
        """
        # 檢查是否為最新請求（防止串圖）
        if request_id == self.latest_request_id:
            self.enhancement_finished.emit(qimage)

    def cleanup(self):
        """清理資源"""
        self.thread.quit()
        self.thread.wait()
