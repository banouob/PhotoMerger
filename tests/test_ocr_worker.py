"""
測試 core.ocr_worker 模組

測試 OcrWorker 的結果解析和車牌正規化，不依賴 PaddleOCR 引擎。
"""

import pytest
from unittest.mock import MagicMock, patch
from core.ocr_worker import OcrWorker, OcrManager


class TestNormalizePlate:
    """測試車牌正規化邏輯"""

    def test_dot_separator_replaced(self):
        """中間的 · 應替換為 -"""
        assert OcrWorker._normalize_plate("ANW·7355") == "ANW-7355"

    def test_bullet_separator_replaced(self):
        """中間的 • 應替換為 -"""
        assert OcrWorker._normalize_plate("ANW•7355") == "ANW-7355"

    def test_dash_preserved(self):
        """已經是 - 的應保持不變"""
        assert OcrWorker._normalize_plate("ANW-7355") == "ANW-7355"

    def test_multiple_separators_collapsed(self):
        """多個連續符號應合併為一個 -"""
        assert OcrWorker._normalize_plate("ANW··7355") == "ANW-7355"
        assert OcrWorker._normalize_plate("ANW--7355") == "ANW-7355"

    def test_leading_trailing_symbols_stripped(self):
        """首尾的符號應去除"""
        assert OcrWorker._normalize_plate("-ANW-7355-") == "ANW-7355"
        assert OcrWorker._normalize_plate("·ANW·7355·") == "ANW-7355"

    def test_lowercase_converted_to_upper(self):
        """小寫字母應轉為大寫"""
        assert OcrWorker._normalize_plate("anw-7355") == "ANW-7355"
        assert OcrWorker._normalize_plate("Abc·1234") == "ABC-1234"

    def test_pure_numbers(self):
        """純數字車牌"""
        assert OcrWorker._normalize_plate("1234") == "1234"

    def test_chinese_chars_replaced(self):
        """中文字元應被替換為 -"""
        assert OcrWorker._normalize_plate("ANW號7355") == "ANW-7355"

    def test_space_replaced(self):
        """空格應被替換為 -"""
        assert OcrWorker._normalize_plate("ANW 7355") == "ANW-7355"

    def test_empty_string(self):
        """空字串應回傳空字串"""
        assert OcrWorker._normalize_plate("") == ""

    def test_only_symbols(self):
        """全符號應回傳空字串"""
        assert OcrWorker._normalize_plate("···---") == ""


class TestOcrResultParsing:
    """測試 PaddleOCR 結果解析"""

    @pytest.fixture
    def worker(self):
        """建立 OcrWorker 實例（不初始化 OCR 引擎）"""
        w = OcrWorker()
        # Mock 掉引擎和 signal
        w.finished = MagicMock()
        w.error = MagicMock()
        w.model_loading = MagicMock()
        return w

    def test_parse_v3_paddlex_format(self, worker):
        """PaddleOCR v3.x (PaddleX) 的 dict 格式應正確解析"""
        import numpy as np
        from PIL import Image

        # 設定一張小測試圖片
        worker._image = Image.new("RGB", (100, 50), color="white")

        # Mock OCR 引擎回傳 v3.x 格式
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [{
            "input_path": None,
            "rec_texts": ["ANW·7355"],
            "rec_scores": [0.95],
            "dt_polys": [],
        }]
        worker._ocr_engine = mock_engine

        worker.process()

        # 應發射 finished 信號，且結果已正規化
        worker.finished.emit.assert_called_once_with("ANW-7355")
        worker.error.emit.assert_not_called()

    def test_parse_v2_legacy_format(self, worker):
        """PaddleOCR v2.x 的 list 格式應正確解析"""
        import numpy as np
        from PIL import Image

        worker._image = Image.new("RGB", (100, 50), color="white")

        # Mock OCR 引擎回傳 v2.x 格式
        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [
            [
                [[[0, 0], [100, 0], [100, 50], [0, 50]], ("AJK-3239", 0.93)]
            ]
        ]
        worker._ocr_engine = mock_engine

        worker.process()

        worker.finished.emit.assert_called_once_with("AJK-3239")

    def test_no_text_detected(self, worker):
        """無辨識結果應發射 error 信號"""
        from PIL import Image

        worker._image = Image.new("RGB", (100, 50), color="white")

        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [{"rec_texts": [], "rec_scores": []}]
        worker._ocr_engine = mock_engine

        worker.process()

        worker.error.emit.assert_called_once()
        worker.finished.emit.assert_not_called()

    def test_none_result(self, worker):
        """OCR 回傳 None 結果應發射 error 信號"""
        from PIL import Image

        worker._image = Image.new("RGB", (100, 50), color="white")

        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [None]
        worker._ocr_engine = mock_engine

        worker.process()

        worker.error.emit.assert_called_once()

    def test_no_image_set(self, worker):
        """未設定圖片應發射 error 信號"""
        worker._image = None
        worker.process()

        worker.error.emit.assert_called_once_with("沒有設定待辨識圖片")

    def test_multiple_texts_joined(self, worker):
        """多行文字應合併"""
        from PIL import Image

        worker._image = Image.new("RGB", (100, 50), color="white")

        mock_engine = MagicMock()
        mock_engine.ocr.return_value = [{
            "rec_texts": ["ANW", "7355"],
            "rec_scores": [0.95, 0.90],
        }]
        worker._ocr_engine = mock_engine

        worker.process()

        # "ANW" + "7355" → "ANW7355" (no separator)
        worker.finished.emit.assert_called_once_with("ANW7355")


class TestOcrWorkerSetImage:
    """測試圖片設定"""

    def test_set_image_copies(self):
        """set_image 應複製圖片（跨執行緒安全）"""
        from PIL import Image

        original = Image.new("RGB", (100, 50), color="red")
        worker = OcrWorker()
        worker.set_image(original)

        # 修改原始圖片不應影響 worker 的副本
        assert worker._image is not original
        assert worker._image.size == (100, 50)
