"""
模式選擇器

提供 P52 和 4Grid 模式選擇介面，以及繼續之前進度的功能
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class ModeSelector(QDialog):
    """
    模式選擇對話框

    提供兩個按鈕讓使用者選擇工作模式:
    - P52 模式 (雙照片合併)
    - 4Grid 模式 (四格拼圖)
    """

    MODE_P52 = "p52"
    MODE_4GRID = "4grid"
    MODE_RESUME = "resume"

    def __init__(self, parent=None):
        """初始化模式選擇器"""
        super().__init__(parent)
        self.selected_mode = None
        self.resume_filepath = None
        self._init_ui()

    def _init_ui(self):
        """初始化使用者介面"""
        self.setWindowTitle("PhotoMerger - 選擇模式")
        self.setFixedSize(500, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 標題
        title = QLabel("PhotoMerger")
        title.setFont(QFont("Microsoft YaHei UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #333;")
        layout.addWidget(title)

        # 說明
        desc = QLabel("請選擇工作模式")
        desc.setFont(QFont("Microsoft YaHei UI", 11))
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        layout.addSpacing(10)

        # 按鈕區域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)

        # P52 模式按鈕
        self.btn_p52 = QPushButton("📷 P52 模式\n(雙照片合併)")
        self.btn_p52.setFont(QFont("Microsoft YaHei UI", 12))
        self.btn_p52.setMinimumSize(200, 120)
        self.btn_p52.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_p52.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.btn_p52.clicked.connect(lambda: self._select_mode(self.MODE_P52))
        btn_layout.addWidget(self.btn_p52)

        # 4Grid 模式按鈕
        self.btn_4grid = QPushButton("📐 4Grid 模式\n(四格拼圖)")
        self.btn_4grid.setFont(QFont("Microsoft YaHei UI", 12))
        self.btn_4grid.setMinimumSize(200, 120)
        self.btn_4grid.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_4grid.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        self.btn_4grid.clicked.connect(lambda: self._select_mode(self.MODE_4GRID))
        btn_layout.addWidget(self.btn_4grid)

        layout.addLayout(btn_layout)

        # 分隔線
        sep = QLabel("— 或是 —")
        sep.setFont(QFont("Microsoft YaHei UI", 9))
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep.setStyleSheet("color: #999;")
        layout.addWidget(sep)

        # 繼續之前進度按鈕
        self.btn_resume = QPushButton("📂 繼續之前進度")
        self.btn_resume.setFont(QFont("Microsoft YaHei UI", 11))
        self.btn_resume.setMinimumSize(200, 40)
        self.btn_resume.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_resume.setToolTip("載入先前儲存的專案檔 (*超速.json *闖紅燈.json)")
        self.btn_resume.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #EF6C00;
            }
        """)
        self.btn_resume.clicked.connect(self._on_resume)
        layout.addWidget(self.btn_resume)

        layout.addStretch()

        # 整體樣式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
        """)

    def _select_mode(self, mode: str):
        """
        選擇模式

        Args:
            mode: 模式字串 ("p52" 或 "4grid")
        """
        self.selected_mode = mode
        self.accept()

    def _on_resume(self):
        """處理繼續之前進度按鈕"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "選擇專案檔",
            "",
            "PhotoMerger 專案檔 (*超速.json *闖紅燈.json);;所有檔案 (*)",
        )

        if filepath:
            self.resume_filepath = filepath
            self.selected_mode = self.MODE_RESUME
            self.accept()

    def get_selected_mode(self) -> str:
        """
        獲取選擇的模式

        Returns:
            模式字串，如果未選擇返回 None
        """
        return self.selected_mode

    def get_resume_filepath(self) -> str | None:
        """
        獲取 resume 模式的專案檔路徑

        Returns:
            JSON 檔案路徑，非 resume 模式時返回 None
        """
        return self.resume_filepath
