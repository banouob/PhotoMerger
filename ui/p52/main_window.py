"""
主視窗模組

PhotoMerger_P52 的主用戶介面

佈局:
- 左側: 照片列表
- 中間: 編輯畫布
- 右側: 車牌輸入和保存按鈕
"""

import json
import logging
import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.ocr_worker import OcrManager
from core.p52.data_manager import DataManager
from core.p52.image_processor import ImageProcessor
from ui.p52.editor_canvas import EditorCanvas
from utils.paths import get_config_dir
from utils.validators import sanitize_filename

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    主視窗

    管理整個應用的介面和交互邏輯
    """

    def __init__(
        self, data_manager: DataManager, image_processor: ImageProcessor,
        parent=None, resume_officer: str = "",
    ):
        """
        初始化主視窗

        Args:
            data_manager: 數據管理器
            image_processor: 圖像處理器
            parent: 父部件
            resume_officer: 從專案檔恢復的警員選擇（可選）
        """
        super().__init__(parent)

        self.data_manager = data_manager
        self.image_processor = image_processor
        self.date_str = data_manager.date_str  # 從data_manager獲取日期
        self._resume_officer = resume_officer

        # 警員清單（從 config.json 載入）
        self._p52_officers: list = self._load_p52_officers()

        # OCR 辨識管理器
        self.ocr_manager = OcrManager()
        self.ocr_manager.ocr_finished.connect(self._on_ocr_result)
        self.ocr_manager.ocr_error.connect(self._on_ocr_error)

        # 圖像增強防抖定時器
        self.enhancement_timer = QTimer()
        self.enhancement_timer.setSingleShot(True)
        self.enhancement_timer.setInterval(300)  # 300ms 防抖
        self.enhancement_timer.timeout.connect(self._apply_enhancements)

        self.setWindowTitle("PhotoMerger_P52 - 警52照片合併工具")
        self.setGeometry(100, 100, 1400, 900)

        self._init_ui()
        self._connect_signals()
        self._load_first_photo()

        # 恢復警員選擇（如有）
        if self._resume_officer:
            idx = self.officer_id_combo.findText(self._resume_officer)
            if idx >= 0:
                self.officer_id_combo.setCurrentIndex(idx)
            else:
                self.officer_id_combo.setCurrentText(self._resume_officer)

    def _init_ui(self):
        """
        初始化用戶介面
        """
        # 創建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主佈局 (水平)
        main_layout = QHBoxLayout(central_widget)

        # === 左側面板: 照片列表 ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        list_label = QLabel("目標照片列表:")
        self.photo_list = QListWidget()
        self.photo_list.setMaximumWidth(250)

        left_layout.addWidget(list_label)
        left_layout.addWidget(self.photo_list)

        # 填充照片列表
        self._populate_photo_list()

        # === 中間面板: 編輯畫布 ===
        self.canvas = EditorCanvas()

        # === 右側面板: 控制區 ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setMaximumWidth(200)

        # 車牌輸入
        plate_label = QLabel("車牌號碼:")
        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("例如: ABC123")

        # OCR 辨識車牌按鈕
        self.ocr_button = QPushButton("辨識車牌")
        self.ocr_button.setToolTip("從框選區域自動辨識車牌號碼")

        # 信心度標籤
        self.confidence_label = QLabel("")
        self.confidence_label.setStyleSheet("color: gray; font-size: 10px;")

        # 保存按鈕
        self.save_button = QPushButton("保存 (Ctrl+S)")
        self.save_button.setShortcut("Ctrl+S")

        # 嚴重超速核取方塊
        self.severe_checkbox = QCheckBox("嚴重超速")
        self.severe_checkbox.setChecked(False)  # 默認: 一般超速

        # === 人員資訊控件 ===
        officer_group = QGroupBox("人員資訊")
        officer_layout = QVBoxLayout(officer_group)

        self.officer_id_combo = QComboBox()
        self.officer_id_combo.setEditable(True)
        self.officer_id_combo.setPlaceholderText("請選擇或輸入警員編號")
        self.officer_id_combo.addItems(self._p52_officers)
        self.officer_id_combo.setCurrentIndex(-1)

        officer_layout.addWidget(self.officer_id_combo)

        # 添加到右側佈局
        right_layout.addWidget(officer_group)
        right_layout.addWidget(plate_label)
        right_layout.addWidget(self.plate_input)
        right_layout.addWidget(self.ocr_button)
        right_layout.addWidget(self.confidence_label)
        right_layout.addWidget(self.save_button)
        right_layout.addWidget(self.severe_checkbox)

        # === 圖像增強控件 ===
        enhancement_group = QGroupBox("圖像增強")
        enhancement_layout = QVBoxLayout(enhancement_group)

        # 亮度滑桿
        brightness_label = QLabel("亮度 (Brightness):")
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.brightness_slider.setTickInterval(25)
        self.brightness_value_label = QLabel("0")
        enhancement_layout.addWidget(brightness_label)
        slider_layout_b = QHBoxLayout()
        slider_layout_b.addWidget(self.brightness_slider)
        slider_layout_b.addWidget(self.brightness_value_label)
        enhancement_layout.addLayout(slider_layout_b)

        # 對比度滑桿
        contrast_label = QLabel("對比度 (Contrast):")
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(-100, 100)
        self.contrast_slider.setValue(0)
        self.contrast_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.contrast_slider.setTickInterval(25)
        self.contrast_value_label = QLabel("0")
        enhancement_layout.addWidget(contrast_label)
        slider_layout_c = QHBoxLayout()
        slider_layout_c.addWidget(self.contrast_slider)
        slider_layout_c.addWidget(self.contrast_value_label)
        enhancement_layout.addLayout(slider_layout_c)

        # 飽和度滑桿
        saturation_label = QLabel("飽和度 (Saturation):")
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(-100, 100)
        self.saturation_slider.setValue(0)
        self.saturation_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.saturation_slider.setTickInterval(25)
        self.saturation_value_label = QLabel("0")
        enhancement_layout.addWidget(saturation_label)
        slider_layout_s = QHBoxLayout()
        slider_layout_s.addWidget(self.saturation_slider)
        slider_layout_s.addWidget(self.saturation_value_label)
        enhancement_layout.addLayout(slider_layout_s)

        # 銳利度滑桿
        sharpness_label = QLabel("銳利度 (Sharpness):")
        self.sharpness_slider = QSlider(Qt.Orientation.Horizontal)
        self.sharpness_slider.setRange(-100, 100)
        self.sharpness_slider.setValue(0)
        self.sharpness_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sharpness_slider.setTickInterval(25)
        self.sharpness_value_label = QLabel("0")
        enhancement_layout.addWidget(sharpness_label)
        slider_layout_sh = QHBoxLayout()
        slider_layout_sh.addWidget(self.sharpness_slider)
        slider_layout_sh.addWidget(self.sharpness_value_label)
        enhancement_layout.addLayout(slider_layout_sh)

        # 重置按鈕
        self.reset_enhancements_button = QPushButton("重置增強")
        enhancement_layout.addWidget(self.reset_enhancements_button)

        # 添加增強組到右側佈局
        right_layout.addWidget(enhancement_group)

        right_layout.addStretch()

        # 組裝主佈局
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(self.canvas, 4)
        main_layout.addWidget(right_panel, 1)

    def _connect_signals(self):
        """
        連接信號
        """
        self.photo_list.currentRowChanged.connect(self._on_photo_selected)
        self.save_button.clicked.connect(self._on_save_clicked)
        self.ocr_button.clicked.connect(self._on_ocr_clicked)

        # 警員資訊
        self.officer_id_combo.currentTextChanged.connect(self._on_officer_text_changed)

        # 圖像增強滑桿連接
        self.brightness_slider.valueChanged.connect(self._on_enhancement_changed)
        self.contrast_slider.valueChanged.connect(self._on_enhancement_changed)
        self.saturation_slider.valueChanged.connect(self._on_enhancement_changed)
        self.sharpness_slider.valueChanged.connect(self._on_enhancement_changed)

        # 更新數值標籤
        self.brightness_slider.valueChanged.connect(
            lambda v: self.brightness_value_label.setText(str(v))
        )
        self.contrast_slider.valueChanged.connect(
            lambda v: self.contrast_value_label.setText(str(v))
        )
        self.saturation_slider.valueChanged.connect(
            lambda v: self.saturation_value_label.setText(str(v))
        )
        self.sharpness_slider.valueChanged.connect(
            lambda v: self.sharpness_value_label.setText(str(v))
        )

        # 重置按鈕
        self.reset_enhancements_button.clicked.connect(self._reset_enhancements)

    def _populate_photo_list(self):
        """
        填充照片列表
        """
        for i in range(self.data_manager.get_photo_count()):
            info = self.data_manager.get_photo_info(i)
            if info:
                filename = info["filename"]
                processed = info["processed"]

                # 添加列表項
                item = QListWidgetItem(f"{'✅' if processed else '  '} {filename}")
                self.photo_list.addItem(item)

    def _load_first_photo(self):
        """
        加載第一張照片
        """
        if self.data_manager.get_photo_count() > 0:
            self.photo_list.setCurrentRow(0)

    def _on_enhancement_changed(self, value):
        """
        處理滑桿值改變(帶防抖)
        """
        # 重啟防抖定時器
        self.enhancement_timer.stop()
        self.enhancement_timer.start()

    def _load_p52_officers(self) -> list:
        """從 config.json 讀取 p52_officers 清單"""
        try:
            config_path = get_config_dir() / "config.json"
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            return config.get("p52_officers", [])
        except Exception:
            return []

    def _save_p52_officers(self) -> None:
        """將更新後的 p52_officers 清單寫回 config.json"""
        try:
            config_path = get_config_dir() / "config.json"
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            config["p52_officers"] = self._p52_officers
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"寫入 config.json 失敗: {e}")

    def _on_officer_text_changed(self):
        """警員編號或姓名變更時即時更新畫布預覽"""
        badge = self.officer_id_combo.currentText().strip()
        self.canvas.set_officer_preview(badge)

    def _get_officer_text(self) -> str:
        """取得目前輸入的完整警員字串（用於輸出）"""
        return self.officer_id_combo.currentText().strip()

    def _prompt_save_new_officer(self, badge: str) -> None:
        """若 badge 不在清單中，詢問是否加入常用選單"""
        if not badge or badge in self._p52_officers:
            return
        reply = QMessageBox.question(
            self,
            "加入常用選單",
            f"『{badge}』不在常用選單中，是否加入？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._p52_officers.append(badge)
            self.officer_id_combo.addItem(badge)
            self._save_p52_officers()

    def _reset_enhancements(self):
        """
        重置所有圖像增強滑桿到0
        """
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(0)
        self.saturation_slider.setValue(0)
        self.sharpness_slider.setValue(0)

    def _apply_enhancements(self):
        """
        應用圖像增強到畫布並儲存到資料管理器
        """
        # 獲取滑桿值
        brightness = self.brightness_slider.value()
        contrast = self.contrast_slider.value()
        saturation = self.saturation_slider.value()
        sharpness = self.sharpness_slider.value()

        # 應用到畫布
        self.canvas.apply_enhancements(brightness, contrast, saturation, sharpness)

        # 儲存參數到資料管理器
        current_photo = self.data_manager.get_current_photo()
        if current_photo:
            self.data_manager.set_enhancement_params(
                current_photo, brightness, contrast, saturation, sharpness
            )

    def _on_photo_selected(self, index: int):
        """
        照片選中事件並恢復增強參數

        Args:
            index: 選中的索引
        """
        if index < 0:
            return

        # 更新數據管理器
        self.data_manager.set_current_photo(index)

        # 清空車牌輸入框 (防止誤用)
        self.plate_input.clear()
        self.confidence_label.clear()

        # 重置"嚴重超速"核取方塊為默認狀態 (防呆機制)
        self.severe_checkbox.setChecked(False)

        # 加載照片到畫布
        photo_path = self.data_manager.get_current_photo()
        if photo_path:
            self.canvas.load_photo(photo_path)

            # 從資料管理器恢復增強參數
            params = self.data_manager.get_enhancement_params(photo_path)
            self.brightness_slider.setValue(params.get("brightness", 0))
            self.contrast_slider.setValue(params.get("contrast", 0))
            self.saturation_slider.setValue(params.get("saturation", 0))
            self.sharpness_slider.setValue(params.get("sharpness", 0))

    def _on_ocr_clicked(self):
        """
        OCR 辨識車牌按鈕點擊事件

        從畫布的框選區域裁切 PIL Image，送入 OcrManager 非同步辨識。
        結果透過 ocr_finished / ocr_error 信號回傳。
        """
        # 取得框選區域的 PIL Image
        pil_image = self.canvas.get_subimage_pil()
        if not pil_image:
            QMessageBox.warning(self, "提示", "請先在畫布上框選車牌區域！")
            return

        # 非同步請求 OCR 辨識
        self.ocr_manager.request_ocr(pil_image)

    def _on_ocr_result(self, text: str, score: float):
        """OCR 辨識完成，自動填入車牌輸入框，並顯示信心度"""
        self.plate_input.setText(text)
        self.confidence_label.setText(f"信心度: {score:.2f}")

    def _on_ocr_error(self, msg: str):
        """OCR 辨識錯誤"""
        QMessageBox.information(self, "辨識結果", f"未能辨識出車牌號碼：{msg}")

    def _on_save_clicked(self):
        """
        保存按鈕點擊事件 (新歸檔系統)
        """
        # 1. 驗證車牌輸入
        plate = self.plate_input.text().strip()
        if not plate:
            QMessageBox.warning(self, "警告", "請輸入車牌號碼!")
            return

        safe_plate = sanitize_filename(plate)

        # 2. 獲取當前照片
        current_photo = self.data_manager.get_current_photo()
        if not current_photo:
            QMessageBox.warning(self, "警告", "沒有選中的照片!")
            return

        # 3. 獲取子圖信息
        subimage_info = self.canvas.get_subimage_info()
        if not subimage_info:
            QMessageBox.warning(self, "警告", "請先框選需要放大的區域!")
            return

        source_roi = subimage_info["source_roi"]
        final_geometry = subimage_info["final_geometry"]

        # 4. 確定類別
        is_severe = self.severe_checkbox.isChecked()
        current_category = "嚴重" if is_severe else "一般"

        # 5. 檢查跨類別衝突 (第一層檢查)
        conflict, opposite_category, conflict_path = (
            self.data_manager.check_cross_category_conflict(safe_plate, is_severe)
        )

        if conflict:
            reply = QMessageBox.question(
                self,
                "跨類別衝突",
                f"此車牌已存在於『{opposite_category}超速』。\n"
                f"是否刪除舊檔並儲存到『{current_category}超速』?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                return

            # 刪除舊類別文件
            self.data_manager.delete_cross_category_files(safe_plate, opposite_category)

        # 6. 檢查同類別衝突 (第二層檢查)
        composite_path = self.data_manager.archive_manager.get_composite_path(
            safe_plate, is_severe
        )

        if os.path.exists(composite_path):
            reply = QMessageBox.question(
                self,
                "文件已存在",
                f"文件 '{safe_plate}.JPG' 已存在於當前類別『{current_category}超速』。\n"
                f"是否覆蓋?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                return

        # 7. 潔癖模式 - 清理此照片的歷史舊檔
        output_path = self.data_manager.archive_manager.get_composite_path(
            safe_plate, is_severe
        )

        old_output_path = self.data_manager.output_history.get(current_photo)
        if old_output_path and old_output_path != output_path:
            if os.path.exists(old_output_path):
                try:
                    os.remove(old_output_path)
                    print(f"已清理此照片的舊輸出檔: {old_output_path}")
                except OSError:
                    pass  # 忽略刪除錯誤

        # 8. 確保歸檔文件夾存在
        self.data_manager.archive_manager.ensure_folders_exist()

        # 9. 複製警52照片 (會話期間只複製一次)
        if not self.data_manager.archive_manager.copy_police_photo_once():
            QMessageBox.warning(self, "警告", "警52照片複製失敗!")
            # 繼續執行, 不是致命錯誤

        # 10. 複製目標原檔 (帶車牌前綴)
        if not self.data_manager.archive_manager.archive_target_original(
            current_photo, safe_plate, is_severe
        ):
            QMessageBox.warning(self, "警告", "原檔複製失敗!")
            return

        # 11. 準備圖像處理數據
        roi_for_processor = source_roi
        subimage_size = (int(final_geometry[2]), int(final_geometry[3]))
        subimage_position = (int(final_geometry[0]), int(final_geometry[1]))

        # 12. 取得當前增強參數
        enhancement_params = self.data_manager.get_enhancement_params(current_photo)

        # 13. 取得警員文字
        officer_text = self._get_officer_text()

        # 14. 生成合成照片 (帶增強參數與警員文字)
        success = self.image_processor.process_and_merge(
            current_photo,
            roi_for_processor,
            subimage_size,
            subimage_position,
            output_path,
            enhancement_params,
            officer_text or None,
        )

        if success:
            # 15. 更新數據管理器
            self.data_manager.mark_as_processed(current_photo, output_path)

            # 16. 更新UI列表
            current_row = self.photo_list.currentRow()
            if current_row >= 0:
                info = self.data_manager.get_photo_info(current_row)
                if info:
                    self.photo_list.item(current_row).setText(f"✅ {info['filename']}")

            # 17. 詢問是否將新警員加入常用選單
            self._prompt_save_new_officer(officer_text)

            # 18. 成功提示
            QMessageBox.information(
                self,
                "成功",
                f"已保存到:\n{output_path}\n\n類別: {current_category}超速",
            )
        else:
            QMessageBox.critical(self, "錯誤", "圖像處理失敗!")

    def closeEvent(self, event):
        """視窗關閉時自動儲存專案進度並清理資源"""
        try:
            from core.project_manager import get_p52_project_path, save_p52_project

            base_dir = self.data_manager.get_base_dir()
            if base_dir:
                filepath = get_p52_project_path(base_dir, self.data_manager.ad_date_str)
                officer = self.officer_id_combo.currentText().strip()
                save_p52_project(self.data_manager, officer, filepath)
        except Exception as e:
            logger.warning(f"無法儲存 P52 專案進度: {e}")
        self.ocr_manager.cleanup()
        super().closeEvent(event)
