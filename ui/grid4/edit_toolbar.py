"""
編輯工具欄模組

提供編輯模式切換和操作按鈕
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QButtonGroup,
    QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class EditToolbar(QWidget):
    """
    編輯工具欄

    功能:
    - 編輯模式切換（檢視/箭頭）
    - 撤銷/重做
    - 清空
    """

    # 訊號
    mode_changed = pyqtSignal(str)      # 模式改變訊號 ("view", "arrow")
    undo_clicked = pyqtSignal()         # 撤銷訊號
    redo_clicked = pyqtSignal()         # 重做訊號
    clear_clicked = pyqtSignal()        # 清空訊號

    def __init__(self, parent=None):
        """初始化編輯工具欄"""
        super().__init__(parent)

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # === 編輯模式組 ===
        mode_label = QLabel("編輯模式:")
        mode_label.setFont(QFont("Microsoft YaHei UI", 9))
        layout.addWidget(mode_label)

        # 建立按鈕組（實現互斥）
        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.setExclusive(True)

        # 檢視模式按鈕
        self.btn_view = QPushButton("👁️ 檢視")
        self.btn_view.setFont(QFont("Microsoft YaHei UI", 9))
        self.btn_view.setCheckable(True)
        self.btn_view.setChecked(True)  # 預設選中
        self.btn_view.setMinimumWidth(80)
        self.btn_view.clicked.connect(lambda: self._on_mode_clicked("view"))
        self.mode_button_group.addButton(self.btn_view)
        layout.addWidget(self.btn_view)

        # 箭頭模式按鈕
        self.btn_arrow = QPushButton("➡️ 箭頭")
        self.btn_arrow.setFont(QFont("Microsoft YaHei UI", 9))
        self.btn_arrow.setCheckable(True)
        self.btn_arrow.setMinimumWidth(80)
        self.btn_arrow.clicked.connect(lambda: self._on_mode_clicked("arrow"))
        self.mode_button_group.addButton(self.btn_arrow)
        layout.addWidget(self.btn_arrow)

        # 分隔線
        separator1 = self._create_separator()
        layout.addWidget(separator1)

        # === 操作按鈕組 ===
        operation_label = QLabel("操作:")
        operation_label.setFont(QFont("Microsoft YaHei UI", 9))
        layout.addWidget(operation_label)

        # 撤銷按鈕
        self.btn_undo = QPushButton("↶ 撤銷")
        self.btn_undo.setFont(QFont("Microsoft YaHei UI", 9))
        self.btn_undo.setMinimumWidth(70)
        self.btn_undo.clicked.connect(self.undo_clicked.emit)
        self.btn_undo.setEnabled(False)  # 初始禁用
        layout.addWidget(self.btn_undo)

        # 重做按鈕
        self.btn_redo = QPushButton("↷ 重做")
        self.btn_redo.setFont(QFont("Microsoft YaHei UI", 9))
        self.btn_redo.setMinimumWidth(70)
        self.btn_redo.clicked.connect(self.redo_clicked.emit)
        self.btn_redo.setEnabled(False)  # 初始禁用
        layout.addWidget(self.btn_redo)

        # 清空按鈕
        self.btn_clear = QPushButton("🗑️ 清空")
        self.btn_clear.setFont(QFont("Microsoft YaHei UI", 9))
        self.btn_clear.setMinimumWidth(70)
        self.btn_clear.clicked.connect(self.clear_clicked.emit)
        layout.addWidget(self.btn_clear)

        layout.addStretch()

        # 樣式
        self._apply_styles()

    def _create_separator(self) -> QFrame:
        """
        建立分隔線

        Returns:
            分隔線 Frame
        """
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setLineWidth(1)
        return separator

    def _apply_styles(self):
        """應用樣式"""
        # 模式按鈕樣式
        mode_button_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #bbb;
            }
            QPushButton:checked {
                background-color: #2196f3;
                color: white;
                border-color: #1976d2;
            }
        """

        self.btn_view.setStyleSheet(mode_button_style)
        self.btn_arrow.setStyleSheet(mode_button_style)

        # 操作按鈕樣式
        operation_button_style = """
            QPushButton {
                background-color: #f9f9f9;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
            QPushButton:pressed {
                background-color: #d8d8d8;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #999;
            }
        """

        self.btn_undo.setStyleSheet(operation_button_style)
        self.btn_redo.setStyleSheet(operation_button_style)
        self.btn_clear.setStyleSheet(operation_button_style)

    def _on_mode_clicked(self, mode: str):
        """
        模式按鈕點選槽函式

        Args:
            mode: 模式字串 ("view", "arrow")
        """
        self.mode_changed.emit(mode)

    def set_undo_enabled(self, enabled: bool):
        """
        設定撤銷按鈕啟用狀態

        Args:
            enabled: 是否啟用
        """
        self.btn_undo.setEnabled(enabled)

    def set_redo_enabled(self, enabled: bool):
        """
        設定重做按鈕啟用狀態

        Args:
            enabled: 是否啟用
        """
        self.btn_redo.setEnabled(enabled)

    def get_current_mode(self) -> str:
        """
        獲取當前編輯模式

        Returns:
            模式字串 ("view", "arrow")
        """
        if self.btn_view.isChecked():
            return "view"
        elif self.btn_arrow.isChecked():
            return "arrow"
        else:
            return "view"


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QTextEdit

    # 測試編輯工具欄
    app = QApplication(sys.argv)

    widget = QWidget()
    layout = QVBoxLayout(widget)

    # 工具欄
    toolbar = EditToolbar()
    layout.addWidget(toolbar)

    # 日誌文字框
    log = QTextEdit()
    log.setReadOnly(True)
    layout.addWidget(log)

    # 連線訊號
    toolbar.mode_changed.connect(lambda m: log.append(f"模式改變: {m}"))
    toolbar.undo_clicked.connect(lambda: log.append("撤銷"))
    toolbar.redo_clicked.connect(lambda: log.append("重做"))
    toolbar.clear_clicked.connect(lambda: log.append("清空"))

    # 啟用撤銷/重做（測試）
    toolbar.set_undo_enabled(True)
    toolbar.set_redo_enabled(True)

    widget.resize(800, 400)
    widget.show()

    sys.exit(app.exec())
