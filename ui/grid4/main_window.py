"""
主視窗模組

PhotoMerger_4Grid 的主介面
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QStatusBar,
    QFileDialog, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path

from core.grid4.config_manager import get_config
from core.grid4.data_manager import get_data_manager
from core.ocr_worker import OcrManager
from ui.grid4.thumbnail_list import ThumbnailList
from ui.grid4.canvas_view import CanvasView
from ui.grid4.control_panel import ControlPanel
from ui.grid4.edit_toolbar import EditToolbar


class MainWindow(QMainWindow):
    """
    主視窗

    佈局結構:
    ┌─────────────────────────────────────────────────────┐
    │  [案件選擇] [掃描資料夾] [統計資訊]                  │
    ├─────────┬──────────────────────┬────────────────────┤
    │         │                      │                    │
    │ 縮圖  │      畫布檢視        │    控制面板        │
    │ 列表    │   (當前圖片)         │  (承辦人/地點等)   │
    │ (3張)   │                      │                    │
    │         │                      │                    │
    ├─────────┴──────────────────────┴────────────────────┤
    │  狀態列                                             │
    └─────────────────────────────────────────────────────┘
    """

    def __init__(self):
        """初始化主視窗"""
        super().__init__()

        # 獲取配置和資料管理器
        self.config = get_config()
        self.data_manager = get_data_manager()

        # 用於儲存當前掃描的根目錄
        self.current_scan_root = None

        # OCR 辨識管理器
        self.ocr_manager = OcrManager()

        # 初始化 UI
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """初始化使用者介面"""
        self.setWindowTitle("PhotoMerger_4Grid - 批次案件管理版")
        self.setMinimumSize(1400, 900)

        # 建立中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主佈局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # === 頂部工具欄 ===
        toolbar_layout = self._create_toolbar()
        main_layout.addLayout(toolbar_layout)

        # === 編輯工具欄 ===
        self.edit_toolbar = EditToolbar()
        main_layout.addWidget(self.edit_toolbar)

        # === 中間內容區域 ===
        content_splitter = self._create_content_area()
        main_layout.addWidget(content_splitter, stretch=1)

        # === 底部狀態列 ===
        self._create_statusbar()

    def _create_toolbar(self) -> QHBoxLayout:
        """
        建立頂部工具欄

        Returns:
            工具欄佈局
        """
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)

        # 案件選擇標籤
        label_case = QLabel("當前案件:")
        label_case.setFont(QFont("Microsoft YaHei UI", 10))
        toolbar_layout.addWidget(label_case)

        # 案件選擇下拉框
        self.case_combo = QComboBox()
        self.case_combo.setMinimumWidth(300)
        self.case_combo.setFont(QFont("Microsoft YaHei UI", 9))
        toolbar_layout.addWidget(self.case_combo)

        # 掃描資料夾按鈕
        self.btn_scan = QPushButton("📁 掃描資料夾")
        self.btn_scan.setFont(QFont("Microsoft YaHei UI", 9))
        self.btn_scan.setMinimumHeight(30)
        toolbar_layout.addWidget(self.btn_scan)

        # 統計資訊標籤
        self.label_stats = QLabel("案件統計: 0 總計 | 0 待處理 | 0 已完成 | 0 錯誤")
        self.label_stats.setFont(QFont("Microsoft YaHei UI", 9))
        self.label_stats.setStyleSheet("color: #666;")
        toolbar_layout.addWidget(self.label_stats)

        toolbar_layout.addStretch()

        # 配置按鈕
        self.btn_config = QPushButton("⚙️ 配置")
        self.btn_config.setFont(QFont("Microsoft YaHei UI", 9))
        toolbar_layout.addWidget(self.btn_config)

        return toolbar_layout

    def _create_content_area(self) -> QSplitter:
        """
        建立中間內容區域

        Returns:
            內容區域分割器
        """
        # 水平分割器（左中右三欄）
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # === 左側：縮圖列表 ===
        self.thumbnail_widget = self._create_thumbnail_placeholder()
        content_splitter.addWidget(self.thumbnail_widget)

        # === 中間：畫布檢視 ===
        self.canvas_widget = self._create_canvas_placeholder()
        content_splitter.addWidget(self.canvas_widget)

        # === 右側：控制面板 ===
        self.control_widget = self._create_control_placeholder()
        content_splitter.addWidget(self.control_widget)

        # 設定初始比例（左:中:右 = 1:3:1）
        content_splitter.setSizes([200, 800, 400])

        return content_splitter

    def _create_thumbnail_placeholder(self) -> QWidget:
        """
        建立縮圖列表

        Returns:
            縮圖列表部件
        """
        self.thumbnail_list = ThumbnailList()
        self.thumbnail_list.thumbnail_clicked.connect(self._on_thumbnail_clicked)
        return self.thumbnail_list

    def _create_canvas_placeholder(self) -> QWidget:
        """
        建立畫布檢視

        Returns:
            畫布檢視部件
        """
        self.canvas_view = CanvasView()
        return self.canvas_view

    def _create_control_placeholder(self) -> QWidget:
        """
        建立控制面板

        Returns:
            控制面板部件
        """
        self.control_panel = ControlPanel()
        self.control_panel.btn_export.clicked.connect(self._on_export_current)
        self.control_panel.btn_batch_export.clicked.connect(self._on_batch_export)
        self.control_panel.btn_mark_done.clicked.connect(self._on_mark_done)
        return self.control_panel

    def _create_statusbar(self):
        """建立狀態列"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就緒")

    def _connect_signals(self):
        """連線訊號與槽"""
        # 掃描資料夾按鈕
        self.btn_scan.clicked.connect(self._on_scan_folder)

        # 案件選擇下拉框
        self.case_combo.currentIndexChanged.connect(self._on_case_changed)

        # 配置按鈕
        self.btn_config.clicked.connect(self._on_open_config)

        # 編輯工具欄訊號
        self.edit_toolbar.mode_changed.connect(self.canvas_view.set_edit_mode)
        self.edit_toolbar.undo_clicked.connect(self.canvas_view.undo)
        self.edit_toolbar.redo_clicked.connect(self.canvas_view.redo)
        self.edit_toolbar.clear_clicked.connect(self._on_clear_edits)

        # 畫布歷史改變訊號（更新撤銷/重做按鈕狀態）
        self.canvas_view.history_changed.connect(self._on_history_changed)

        # 影象增強訊號
        self.control_panel.enhancement_changed.connect(self.canvas_view.apply_enhancements)

        # 縮圖順序改變訊號（拖曳排序後重新整理畫布）
        self.thumbnail_list.order_changed.connect(self._on_order_changed)

        # OCR 辨識訊號
        self.control_panel.ocr_requested.connect(self._on_ocr_requested)
        self.ocr_manager.ocr_finished.connect(self._on_ocr_finished)
        self.ocr_manager.ocr_error.connect(self._on_ocr_error)
        self.ocr_manager.model_loading.connect(self._on_model_loading)

    def _on_scan_folder(self):
        """掃描資料夾槽函式"""
        # 開啟資料夾選擇對話方塊
        folder = QFileDialog.getExistingDirectory(
            self,
            "選擇案件根目錄",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not folder:
            return

        # 記錄當前掃描的根目錄
        self.current_scan_root = folder

        # 掃描資料夾
        self.statusbar.showMessage(f"正在掃描: {folder}")
        count = self.data_manager.scan_root_folder(folder)

        if count == 0:
            QMessageBox.warning(
                self,
                "掃描結果",
                f"未找到有效案件\n\n路徑: {folder}"
            )
            self.statusbar.showMessage("掃描完成 - 未找到案件")
            return

        # 更新 UI
        self._update_case_list()
        self._update_stats()
        self.statusbar.showMessage(f"掃描完成 - 找到 {count} 個案件")

        QMessageBox.information(
            self,
            "掃描完成",
            f"成功掃描 {count} 個案件\n\n路徑: {folder}"
        )

    def _on_case_changed(self, index: int):
        """案件選擇改變槽函式"""
        if index < 0:
            return

        # === 修改點 1：先手動儲存舊案件的狀態 ===
        # 在切換 DataManager 指標前，先將畫面上目前的編輯內容存回「舊案件」中。
        # 確保舊案件的編輯不會遺失，也不會汙染新案件。
        if self.canvas_view.current_image_path:
            self.canvas_view._save_current_state_to_data_manager()

        # 切換當前案件 (此時 DataManager 指向新案件)
        success = self.data_manager.set_current_case(index)
        if success:
            self.statusbar.showMessage(f"已切換到案件 {index + 1}")

            # 更新縮圖列表
            current_case = self.data_manager.get_current_case()
            if current_case:
                self.thumbnail_list.load_images(current_case.image_paths)

                # 預設顯示第一張圖片
                if current_case.image_paths:
                    # === 修改點 2：載入新圖時禁止自動儲存 ===
                    # 傳入 save_state=False。
                    # 因為我們在上面已經存過舊狀態了，且此時畫面上還殘留著舊圖的內容，
                    # 這裡必須禁止 load_image 再次觸發儲存，否則會把舊內容寫入新案件。
                    self.canvas_view.load_image(current_case.image_paths[0], save_state=False)
                    
                    # 讀取第一張圖片的 EXIF 時間並設定到控制面板
                    exif_time = self.data_manager._extract_exif_datetime(current_case.image_paths[0])
                    if exif_time:
                        roc_time = self.data_manager.convert_to_roc_datetime(exif_time)
                        # 設定到後設資料中
                        if not current_case.meta_data:
                            current_case.meta_data = {}
                        current_case.meta_data["datetime"] = roc_time

                # 載入後設資料
                if current_case.meta_data:
                    self.control_panel.set_metadata(current_case.meta_data)
        else:
            self.statusbar.showMessage("切換案件失敗")

    def _on_open_config(self):
        """開啟配置檔案槽函式"""
        try:
            self.config.open_in_editor()
            QMessageBox.information(
                self,
                "配置檔案",
                "已使用系統預設編輯器開啟配置檔案\n\n"
                f"路徑: {self.config.config_path}\n\n"
                "修改後請重啟程式生效"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "錯誤",
                f"無法開啟配置檔案\n\n錯誤: {e}"
            )

    def _update_case_list(self):
        """更新案件下拉選單"""
        self.case_combo.clear()

        for i, case in enumerate(self.data_manager.cases):
            folder_name = Path(case.folder_path).name
            status_icon = {
                "pending": "⏳",
                "done": "✅",
                "error": "❌"
            }.get(case.status.value, "❓")

            display_text = f"{status_icon} 案件 {i + 1}: {folder_name} ({len(case.image_paths)} 張)"
            self.case_combo.addItem(display_text)

        # 選中第一個案件
        if self.data_manager.cases:
            self.case_combo.setCurrentIndex(0)

    def _update_stats(self):
        """更新統計資訊"""
        summary = self.data_manager.get_case_summary()

        stats_text = (
            f"案件統計: {summary['total']} 總計 | "
            f"{summary['pending']} 待處理 | "
            f"{summary['done']} 已完成 | "
            f"{summary['error']} 錯誤"
        )

        self.label_stats.setText(stats_text)

    def _on_thumbnail_clicked(self, index: int):
        """縮圖點選槽函式"""
        current_case = self.data_manager.get_current_case()
        if current_case and 0 <= index < len(current_case.image_paths):
            # 在畫布中顯示選中的圖片（傳遞索引用於狀態持久化）
            self.canvas_view.load_image(current_case.image_paths[index], image_index=index)

            # 恢復影象增強引數到控制面板
            image_state = current_case.image_states[index]
            enhancement_values = {
                "brightness": image_state.brightness,
                "contrast": image_state.contrast,
                "saturation": image_state.saturation,
                "sharpness": image_state.sharpness
            }
            self.control_panel.set_enhancement_values(enhancement_values)

            self.statusbar.showMessage(f"正在顯示圖片 {index + 1}")

    def _on_export_current(self):
        """輸出當前案件槽函式"""
        current_case = self.data_manager.get_current_case()

        if not current_case:
            QMessageBox.warning(self, "錯誤", "沒有選中的案件")
            return

        if current_case.status.value == "error":
            QMessageBox.warning(self, "錯誤", "此案件圖片數量不正確，無法輸出")
            return

        # 儲存當前畫布狀態
        self.canvas_view._save_current_state_to_data_manager()

        # 儲存後設資料
        current_case.meta_data = self.control_panel.get_metadata()

        # 檢查必填欄位
        if not current_case.meta_data.get("plate"):
            QMessageBox.warning(self, "缺少資訊", "請先填寫車牌號碼")
            return

        # 選擇輸出目錄
        from core.grid4.archive_manager import get_archive_manager
        archive_manager = get_archive_manager()
        
        default_output = archive_manager.get_suggested_output_root()
        output_root = QFileDialog.getExistingDirectory(
            self,
            "選擇輸出目錄",
            default_output,
            QFileDialog.Option.ShowDirsOnly
        )

        if not output_root:
            return

        try:
            self.statusbar.showMessage("正在輸出...")
            
            # 執行歸檔
            output_path = archive_manager.archive_case(current_case, output_root)

            # 標記為完成
            self.data_manager.mark_case_as_done(current_case)
            self._update_case_list()
            self._update_stats()

            QMessageBox.information(
                self,
                "輸出成功",
                f"案件已成功輸出！\n\n合成圖路徑:\n{output_path}"
            )

            self.statusbar.showMessage(f"輸出完成: {output_path}")

        except Exception as e:
            QMessageBox.critical(self, "輸出失敗", f"發生錯誤:\n{e}")
            self.statusbar.showMessage("輸出失敗")

    def _on_batch_export(self):
        """批次輸出槽函式 (修改版：輸出已完成案件至原資料夾)"""
        summary = self.data_manager.get_case_summary()

        # 修改點 1: 檢查 'done' 而不是 'pending'
        if summary['done'] == 0:
            QMessageBox.information(self, "批次輸出", "沒有已完成的案件")
            return

        # 修改點 2: 確認訊息變更
        reply = QMessageBox.question(
            self,
            "批次輸出",
            f"將輸出 {summary['done']} 個已完成案件至各自的原始資料夾\n\n確定要繼續嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 獲取歸檔管理器
        from core.grid4.archive_manager import get_archive_manager
        archive_manager = get_archive_manager()

        # 檢查是否有根目錄記錄
        if not self.current_scan_root:
            QMessageBox.warning(self, "錯誤", "無法確認輸出根目錄，請重新掃描資料夾。")
            return

        # 批次處理
        success_count = 0
        fail_count = 0

        for case in self.data_manager.cases:
            # 只處理狀態為 'done' 的案件
            if case.status.value != "done":
                continue

            try:
                # 使用 self.current_scan_root 作為輸出根目錄
                # 這樣所有案件都會輸出到 Root 底下的同一個資料夾中
                archive_manager.archive_case(case, self.current_scan_root)
                
                # 案件原本就是 done，這裡可以省略 mark_case_as_done
                
                success_count += 1
            except Exception as e:
                print(f"Failed to export case {case.folder_path}: {e}")
                fail_count += 1

        self._update_case_list()
        self._update_stats()

        QMessageBox.information(
            self,
            "批次輸出完成",
            f"成功: {success_count} 個\n失敗: {fail_count} 個\n\n檔案已輸出至各案件的原始資料夾內。"
        )

    def _on_mark_done(self):
        """標記為已完成槽函式"""
        current_case = self.data_manager.get_current_case()

        if not current_case:
            QMessageBox.warning(
                self,
                "標記為已完成",
                "沒有選中的案件"
            )
            return

        # 儲存後設資料
        current_case.meta_data = self.control_panel.get_metadata()

        # 標記為已完成
        self.data_manager.mark_case_as_done(current_case)

        # 更新 UI
        self._update_case_list()
        self._update_stats()

        self.statusbar.showMessage(f"案件已標記為完成: {Path(current_case.folder_path).name}")

        # 切換到下一個待處理案件
        next_index = self.data_manager.get_next_pending_case_index()
        if next_index is not None:
            self.case_combo.setCurrentIndex(next_index)
        else:
            QMessageBox.information(
                self,
                "所有案件已完成",
                "所有待處理案件已完成！"
            )

    def _on_clear_edits(self):
        """清空編輯槽函式"""
        reply = QMessageBox.question(
            self,
            "清空編輯",
            "確定要清空當前圖片的所有編輯（箭頭）嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 清空箭頭
            self.canvas_view.clear_arrows()
            self.statusbar.showMessage("已清空編輯內容")

    def _on_history_changed(self, can_undo: bool, can_redo: bool):
        """
        歷史改變槽函式（更新撤銷/重做按鈕狀態）

        Args:
            can_undo: 是否可以撤銷
            can_redo: 是否可以重做
        """
        self.edit_toolbar.set_undo_enabled(can_undo)
        self.edit_toolbar.set_redo_enabled(can_redo)

    def _on_order_changed(self, source_index: int, target_index: int):
        """
        縮圖順序改變槽函式（拖曳排序後重新整理畫布）

        Args:
            source_index: 源索引（被拖曳的圖片）
            target_index: 目標索引（放置的位置）
        """
        current_case = self.data_manager.get_current_case()

        if current_case and current_case.image_paths:
            # 重新整理畫布，顯示目標位置的圖片
            self.canvas_view.load_image(
                current_case.image_paths[target_index],
                image_index=target_index,
                save_state=False  # 已經由 ThumbnailList 觸發儲存，無需重複
            )

            # 恢復影象增強引數到控制面板
            image_state = current_case.image_states[target_index]
            enhancement_values = {
                "brightness": image_state.brightness,
                "contrast": image_state.contrast,
                "saturation": image_state.saturation,
                "sharpness": image_state.sharpness
            }
            self.control_panel.set_enhancement_values(enhancement_values)

            self.statusbar.showMessage(
                f"已交換圖片 {source_index + 1} 和 {target_index + 1} 的位置"
            )


    def _on_ocr_requested(self):
        """OCR 辨識請求槽函式"""
        pil_img = self.canvas_view.get_subimage_pil()

        if pil_img is None:
            self.statusbar.showMessage("請先框選車牌區域（在檢視模式下左鍵拖曳框選）")
            return

        # 停用按鈕 + 更新文字
        self.control_panel.btn_ocr.setText("⏳ 辨識中...")
        self.control_panel.btn_ocr.setEnabled(False)
        self.statusbar.showMessage("正在辨識車牌...")

        # 送入背景辨識
        self.ocr_manager.request_ocr(pil_img)

    def _on_ocr_finished(self, text: str):
        """OCR 辨識完成槽函式"""
        self.control_panel.edit_plate.setText(text)
        self.control_panel.btn_ocr.setText("🔍 辨識")
        self.control_panel.btn_ocr.setEnabled(True)
        self.statusbar.showMessage(f"辨識完成: {text}")

    def _on_ocr_error(self, msg: str):
        """OCR 辨識錯誤槽函式"""
        self.control_panel.btn_ocr.setText("🔍 辨識")
        self.control_panel.btn_ocr.setEnabled(True)
        self.statusbar.showMessage(f"辨識失敗: {msg}")

    def _on_model_loading(self, is_loading: bool):
        """OCR 模型載入狀態槽函式"""
        if is_loading:
            self.statusbar.showMessage("首次載入 OCR 模型中，請稍候…")
        else:
            self.statusbar.showMessage("OCR 模型載入完成")

    def closeEvent(self, event):
        """關閉視窗事件 - 清理背景執行緒"""
        self.ocr_manager.cleanup()
        self.canvas_view.enhancement_manager.cleanup()
        super().closeEvent(event)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
