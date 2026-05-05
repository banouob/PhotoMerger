"""
OCR 辨識 Worker 模組

背景執行緒處理車牌 OCR 辨識，避免阻塞 UI
使用 PaddleOCR 進行文字辨識
"""

import logging
import re

from PIL import Image
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)


class OcrWorker(QObject):
    """
    OCR Worker（執行在獨立執行緒）

    功能:
    - 延遲載入 PaddleOCR 模型（首次辨識時才初始化）
    - 在背景執行緒處理 OCR 辨識
    - 透過 signal 回傳辨識結果
    """

    # 訊號：觸發處理
    request_processing = pyqtSignal()

    # 訊號：辨識完成 (辨識文字, 信心度)
    finished = pyqtSignal(str, float)

    # 訊號：辨識錯誤 (錯誤訊息)
    error = pyqtSignal(str)

    # 訊號：模型載入狀態 (is_loading)
    model_loading = pyqtSignal(bool)

    def __init__(self):
        """初始化 Worker"""
        super().__init__()

        self._image: Image.Image | None = None
        self._ocr_engine = None  # 延遲初始化

    def set_image(self, pil_image: Image.Image):
        """
        設定待辨識圖片（主執行緒呼叫）

        Args:
            pil_image: PIL Image 物件
        """
        self._image = pil_image.copy()

    def _init_ocr_engine(self):
        """延遲初始化 PaddleOCR 引擎"""
        if self._ocr_engine is not None:
            return

        self.model_loading.emit(True)
        try:
            import os  # noqa: E402 — 延遲 import，避免未安裝時啟動失敗
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            # 停用 oneDNN (MKL-DNN)，修復 PaddlePaddle 3.x PIR executor 相容性問題
            # 錯誤: ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute]
            os.environ["FLAGS_use_mkldnn"] = "0"
            from paddleocr import (
                PaddleOCR,  # noqa: E402 — 延遲 import，首次辨識時才載入
            )
            self._ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang="ch",
                enable_mkldnn=False,
            )
        finally:
            self.model_loading.emit(False)

    @staticmethod
    def _normalize_plate(text: str) -> str:
        """
        車牌後處理：正規化車牌號碼格式

        - 將非英數字元（如 ·、•、.、—）替換為 "-"
        - 合併連續 "-" 並去除首尾 "-"
        - 統一大寫

        Args:
            text: OCR 辨識的原始文字

        Returns:
            正規化後的車牌號碼
        """
        result = re.sub(r'[^A-Za-z0-9]', '-', text)
        result = re.sub(r'-+', '-', result).strip('-')
        return result.upper()

    @pyqtSlot()
    def process(self):
        """執行 OCR 辨識"""
        if self._image is None:
            self.error.emit("沒有設定待辨識圖片")
            return

        try:
            # 確保引擎已初始化
            self._init_ocr_engine()

            # PIL Image -> numpy array
            import numpy as np  # noqa: E402 — 延遲 import，避免未安裝時啟動失敗
            img_array = np.array(self._image)
            logger.debug("OCR 圖片大小: %s", img_array.shape)

            # 執行 OCR
            results = self._ocr_engine.ocr(img_array)

            # 解析結果（相容 PaddleOCR v3.x PaddleX 格式 和 v2.x 舊格式）
            texts = []
            scores = []
            if results:
                for page in results:
                    if page is None:
                        continue

                    # PaddleOCR v3.x (PaddleX) 格式:
                    # page 是 dict，含 'rec_texts' 和 'rec_scores'
                    if isinstance(page, dict):
                        rec_texts = page.get("rec_texts", [])
                        rec_scores = page.get("rec_scores", [])
                        for i, text in enumerate(rec_texts):
                            score = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                            logger.info("OCR 辨識: %s (信心度: %.2f)", text, score)
                            texts.append(str(text))
                            scores.append(score)
                        continue

                    # PaddleOCR v2.x 舊格式:
                    # page 是 list of [box, (text, confidence)]
                    if isinstance(page, list):
                        for line in page:
                            try:
                                if isinstance(line, (list, tuple)) and len(line) >= 2:
                                    if isinstance(line[1], (tuple, list)):
                                        texts.append(str(line[1][0]))
                                        scores.append(float(line[1][1]))
                            except (IndexError, KeyError, TypeError) as e:
                                logger.warning("OCR 解析行失敗: %s, line=%s", e, line)

            if texts:
                # 合併所有辨識文字（車牌通常只有一行）
                raw_text = "".join(texts).strip()
                result_text = self._normalize_plate(raw_text)
                avg_score = sum(scores) / len(scores) if scores else 0.0
                logger.info("OCR 辨識完成: %s (原始: %s, 平均信心度: %.2f)", result_text, raw_text, avg_score)
                self.finished.emit(result_text, avg_score)
            else:
                logger.warning("OCR 未辨識到文字")
                self.error.emit("未辨識到文字，請確認框選範圍包含車牌")

        except ImportError as e:
            logger.error("PaddleOCR 未安裝: %s", e)
            self.error.emit("PaddleOCR 未安裝，請執行: pip install paddlepaddle paddleocr")
        except Exception as e:
            logger.error("OCR 辨識失敗: %s", e)
            self.error.emit(f"OCR 辨識失敗: {e}")


class OcrManager(QObject):
    """
    OCR 辨識管理器

    功能:
    - 管理 Worker 執行緒
    - 提供統一的辨識介面
    """

    # 訊號：辨識完成 (辨識文字, 信心度)
    ocr_finished = pyqtSignal(str, float)

    # 訊號：辨識錯誤 (錯誤訊息)
    ocr_error = pyqtSignal(str)

    # 訊號：模型載入狀態 (is_loading)
    model_loading = pyqtSignal(bool)

    def __init__(self):
        """初始化管理器"""
        super().__init__()

        # 建立 Worker 和執行緒
        self.worker = OcrWorker()
        self.thread = QThread()

        # 移動 Worker 到執行緒
        self.worker.moveToThread(self.thread)

        # 連線訊號
        self.worker.request_processing.connect(self.worker.process)
        self.worker.finished.connect(self._on_ocr_finished)
        self.worker.error.connect(self._on_ocr_error)
        self.worker.model_loading.connect(self.model_loading)

        # 啟動執行緒
        self.thread.start()

    def request_ocr(self, pil_image: Image.Image):
        """
        請求 OCR 辨識

        Args:
            pil_image: 待辨識的 PIL Image（子圖裁切）
        """
        # 設定圖片（主執行緒中 copy）
        self.worker.set_image(pil_image)

        # 觸發背景處理
        self.worker.request_processing.emit()

    @pyqtSlot(str, float)
    def _on_ocr_finished(self, text: str, score: float):
        """辨識完成槽函式"""
        self.ocr_finished.emit(text, score)

    @pyqtSlot(str)
    def _on_ocr_error(self, msg: str):
        """辨識錯誤槽函式"""
        self.ocr_error.emit(msg)

    def cleanup(self):
        """清理資源"""
        self.thread.quit()
        self.thread.wait()
