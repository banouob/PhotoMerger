"""
控制面板模組

顯示和編輯案件資訊
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QLineEdit, QPushButton, QGroupBox,
    QDateTimeEdit, QFormLayout, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime, QTimer
from PyQt6.QtGui import QFont

from core.grid4.config_manager import get_config
from typing import Dict, Any


class ControlPanel(QWidget):
    """
    控制面板

    功能:
    - 編輯案件後設資料（承辦人、地點、時間等）
    - 影象調整（亮度、對比度、飽和度、銳化）
    - 提供輸出控制
    - 顯示案件狀態
    """

    metadata_changed = pyqtSignal(dict)  # 後設資料改變訊號
    enhancement_changed = pyqtSignal(int, int, int, int)  # 影象增強訊號 (brightness, contrast, saturation, sharpness)
    ocr_requested = pyqtSignal()  # OCR 辨識請求訊號

    def __init__(self, parent=None):
        """初始化控制面板"""
        super().__init__(parent)

        self.config = get_config()

        # 防抖定時器（300ms）
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self._emit_enhancement)

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # === 案件資訊組 ===
        info_group = self._create_info_group()
        layout.addWidget(info_group)

        # === 影象調整組 ===
        adjustment_group = self._create_adjustment_group()
        layout.addWidget(adjustment_group)

        # === 輸出控制組 ===
        output_group = self._create_output_group()
        layout.addWidget(output_group)

        layout.addStretch()

    def _create_info_group(self) -> QGroupBox:
        """
        建立案件資訊組

        Returns:
            案件資訊組框
        """
        group = QGroupBox("案件資訊")
        group.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))

        form_layout = QFormLayout(group)
        form_layout.setSpacing(10)

        # 車牌號碼 (必填) + OCR 辨識按鈕
        plate_layout = QHBoxLayout()
        self.edit_plate = QLineEdit()
        self.edit_plate.setPlaceholderText("必填，例如: ABC-1234")
        self.edit_plate.setFont(QFont("Microsoft YaHei UI", 9))
        plate_layout.addWidget(self.edit_plate)
        self.btn_ocr = QPushButton("🔍 辨識")
        self.btn_ocr.setToolTip("從子圖辨識車牌號碼")
        self.btn_ocr.setFont(QFont("Microsoft YaHei UI", 9))
        self.btn_ocr.clicked.connect(lambda: self.ocr_requested.emit())
        plate_layout.addWidget(self.btn_ocr)
        form_layout.addRow("🚗 違規車號:", plate_layout)

        # 信心度標籤
        self.label_confidence = QLabel("")
        self.label_confidence.setStyleSheet("color: gray; font-size: 10px;")
        form_layout.addRow("", self.label_confidence)

        # 承辦人 (可記憶下拉框)
        self.combo_officer = QComboBox()
        self.combo_officer.setEditable(True)
        self.combo_officer.addItems(self.config.get_officers())
        self.combo_officer.setFont(QFont("Microsoft YaHei UI", 9))
        form_layout.addRow("採證人員:", self.combo_officer)

        # 地點 (可記憶下拉框)
        self.combo_location = QComboBox()
        self.combo_location.setEditable(True)
        self.combo_location.addItems(self.config.get_locations())
        self.combo_location.setFont(QFont("Microsoft YaHei UI", 9))
        form_layout.addRow("違規地點:", self.combo_location)

        # 時間 (可編輯 - 自動從 EXIF 讀取並轉換為民國年，可手動修正)
        self.edit_datetime = QLineEdit()
        self.edit_datetime.setPlaceholderText("例如: 115年01月05日14時30分")
        self.edit_datetime.setFont(QFont("Microsoft YaHei UI", 9))
        form_layout.addRow("違規時間:", self.edit_datetime)

        return group

    def _create_adjustment_group(self) -> QGroupBox:
        """
        建立影象調整組

        Returns:
            影象調整組框
        """
        group = QGroupBox("影象調整")
        group.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # 亮度滑塊
        self.slider_brightness, brightness_layout = self._create_slider_with_label(
            "亮度", -100, 100, 0
        )
        layout.addLayout(brightness_layout)

        # 對比度滑塊
        self.slider_contrast, contrast_layout = self._create_slider_with_label(
            "對比度", -100, 100, 0
        )
        layout.addLayout(contrast_layout)

        # 飽和度滑塊
        self.slider_saturation, saturation_layout = self._create_slider_with_label(
            "飽和度", -100, 100, 0
        )
        layout.addLayout(saturation_layout)

        # 銳化滑塊
        self.slider_sharpness, sharpness_layout = self._create_slider_with_label(
            "銳化", -100, 100, 0
        )
        layout.addLayout(sharpness_layout)

        # 連線訊號（防抖）
        self.slider_brightness.valueChanged.connect(self._on_slider_changed)
        self.slider_contrast.valueChanged.connect(self._on_slider_changed)
        self.slider_saturation.valueChanged.connect(self._on_slider_changed)
        self.slider_sharpness.valueChanged.connect(self._on_slider_changed)

        # 重置按鈕
        self.btn_reset = QPushButton("↺ 重置所有調整")
        self.btn_reset.setFont(QFont("Microsoft YaHei UI", 9))
        self.btn_reset.setMinimumHeight(35)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
             QPushButton {
                 background-color: #f5f5f5;
                 color: #333;
                 border: 1px solid #ddd;
                 border-radius: 4px;
                 padding: 5px;
             }
             QPushButton:hover {
                 background-color: #e0e0e0;
                 border-color: #ccc;
             }
             QPushButton:pressed {
                 background-color: #d6d6d6;
             }
        """)
        self.btn_reset.clicked.connect(self._reset_adjustments)
        layout.addWidget(self.btn_reset)

        return group

    def _create_slider_with_label(self, name: str, min_val: int,
                                   max_val: int, default: int) -> tuple:
        """
        建立帶標籤的滑塊

        Args:
            name: 標籤名稱
            min_val: 最小值
            max_val: 最大值
            default: 預設值

        Returns:
            (slider, layout) 元組
        """
        layout = QHBoxLayout()

        # 標籤
        label = QLabel(f"{name}:")
        label.setFont(QFont("Microsoft YaHei UI", 8))
        label.setMinimumWidth(50)
        layout.addWidget(label)

        # 滑塊
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(50)
        layout.addWidget(slider)

        # 數值標籤
        value_label = QLabel(str(default))
        value_label.setFont(QFont("Microsoft YaHei UI", 8))
        value_label.setMinimumWidth(35)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(value_label)

        # 更新數值標籤
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))

        return slider, layout

    def _on_slider_changed(self):
        """滑塊改變槽函式（啟動防抖定時器）"""
        # 重啟防抖定時器
        self.debounce_timer.stop()
        self.debounce_timer.start()

    def _emit_enhancement(self):
        """傳送影象增強訊號"""
        self.enhancement_changed.emit(
            self.slider_brightness.value(),
            self.slider_contrast.value(),
            self.slider_saturation.value(),
            self.slider_sharpness.value()
        )

    def _reset_adjustments(self):
        """重置所有調整"""
        self.slider_brightness.setValue(0)
        self.slider_contrast.setValue(0)
        self.slider_saturation.setValue(0)
        self.slider_sharpness.setValue(0)

    def get_enhancement_values(self) -> Dict[str, int]:
        """
        獲取影象增強引數

        Returns:
            增強引數字典
        """
        return {
            "brightness": self.slider_brightness.value(),
            "contrast": self.slider_contrast.value(),
            "saturation": self.slider_saturation.value(),
            "sharpness": self.slider_sharpness.value()
        }

    def set_enhancement_values(self, values: Dict[str, int]):
        """
        設定影象增強引數

        Args:
            values: 增強引數字典
        """
        self.slider_brightness.setValue(values.get("brightness", 0))
        self.slider_contrast.setValue(values.get("contrast", 0))
        self.slider_saturation.setValue(values.get("saturation", 0))
        self.slider_sharpness.setValue(values.get("sharpness", 0))

    def _create_output_group(self) -> QGroupBox:
        """
        建立輸出控制組

        Returns:
            輸出控制組框
        """
        group = QGroupBox("輸出控制")
        group.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # 輸出按鈕
        self.btn_export = QPushButton("📄 輸出當前案件")
        self.btn_export.setFont(QFont("Microsoft YaHei UI", 10))
        self.btn_export.setMinimumHeight(40)
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        layout.addWidget(self.btn_export)

        # 批次輸出按鈕
        self.btn_batch_export = QPushButton("📦 批次輸出所有待處理案件")
        self.btn_batch_export.setFont(QFont("Microsoft YaHei UI", 9))
        self.btn_batch_export.setMinimumHeight(35)
        self.btn_batch_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_export.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        layout.addWidget(self.btn_batch_export)

        # 標記為完成按鈕
        self.btn_mark_done = QPushButton("✅ 標記為已完成")
        self.btn_mark_done.setFont(QFont("Microsoft YaHei UI", 9))
        self.btn_mark_done.setMinimumHeight(35)
        self.btn_mark_done.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mark_done.setStyleSheet("""
             QPushButton {
                 background-color: #f5f5f5;
                 color: #333;
                 border: 1px solid #ddd;
                 border-radius: 4px;
                 padding: 8px;
             }
             QPushButton:hover {
                 background-color: #e0e0e0;
                 border-color: #ccc;
             }
             QPushButton:pressed {
                 background-color: #d6d6d6;
             }
        """)
        layout.addWidget(self.btn_mark_done)

        return group

    def get_metadata(self) -> Dict[str, Any]:
        """
        獲取當前後設資料

        Returns:
            後設資料字典
        """
        return {
            "plate": self.edit_plate.text().strip(),
            "officer": self.combo_officer.currentText(),
            "location": self.combo_location.currentText(),
            "datetime": self.edit_datetime.text().strip(),
        }

    def set_metadata(self, metadata: Dict[str, Any]):
        """
        設定後設資料

        Args:
            metadata: 後設資料字典
        """
        # 強制更新車牌欄位：若 metadata 無 "plate"，填入空字串達到清空效果
        self.edit_plate.setText(metadata.get("plate", ""))
        self.label_confidence.clear()

        if "officer" in metadata:
            self.combo_officer.setCurrentText(metadata["officer"])

        if "location" in metadata:
            self.combo_location.setCurrentText(metadata["location"])

        if "datetime" in metadata:
            self.edit_datetime.setText(metadata["datetime"])

    def clear(self):
        """清空控制面板"""
        self.edit_plate.clear()
        self.label_confidence.clear()
        self.combo_officer.setCurrentIndex(0)
        self.combo_location.setCurrentIndex(0)
        self.edit_datetime.clear()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    # 測試控制面板
    app = QApplication(sys.argv)

    widget = ControlPanel()
    widget.resize(400, 600)
    widget.show()

    sys.exit(app.exec())
