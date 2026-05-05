"""
縮圖列表模組

支援拖曳排序的圖片縮圖列表
"""

from pathlib import Path

from PIL import Image
from PyQt6.QtCore import QByteArray, QMimeData, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ThumbnailItem(QFrame):
    """
    單個縮圖項

    功能:
    - 顯示圖片縮圖
    - 顯示序號
    - 支援點選選中
    - 支援拖曳
    """

    clicked = pyqtSignal(int)  # 點選訊號（引數：索引）

    def __init__(self, index: int, image_path: str, parent=None):
        """
        初始化縮圖項

        Args:
            index: 圖片索引（0-2）
            image_path: 圖片路徑
            parent: 父部件
        """
        super().__init__(parent)

        self.index = index
        self.image_path = image_path
        self.is_selected = False

        self._init_ui()
        self._load_thumbnail()

    def _init_ui(self):
        """初始化 UI"""
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setMinimumSize(150, 120)
        self.setMaximumSize(200, 160)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        # 佈局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 序號標籤
        self.label_index = QLabel(f"圖片 {self.index + 1}")
        self.label_index.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_index.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))
        layout.addWidget(self.label_index)

        # 縮圖標籤
        self.label_thumbnail = QLabel()
        self.label_thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_thumbnail.setMinimumSize(140, 90)
        self.label_thumbnail.setScaledContents(False)
        layout.addWidget(self.label_thumbnail, stretch=1)

        # 預設樣式（未選中）
        self._update_style()

    def _load_thumbnail(self):
        """載入縮圖"""
        try:
            # 使用 PIL 載入圖片
            pil_image = Image.open(self.image_path)

            # 縮放到合適大小（保持寬高比）
            pil_image.thumbnail((140, 90), Image.Resampling.LANCZOS)

            # 轉換為 QPixmap
            pil_image = pil_image.convert("RGB")
            data = pil_image.tobytes("raw", "RGB")
            qimage = QImage(
                data,
                pil_image.width,
                pil_image.height,
                pil_image.width * 3,
                QImage.Format.Format_RGB888
            )
            pixmap = QPixmap.fromImage(qimage)

            self.label_thumbnail.setPixmap(pixmap)

        except Exception:
            # 載入失敗，顯示錯誤資訊
            self.label_thumbnail.setText(f"載入失敗\n{Path(self.image_path).name}")
            self.label_thumbnail.setStyleSheet("color: red;")

    def mousePressEvent(self, event):
        """滑鼠點選事件 - 記錄起始位置用於拖曳"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
            self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """滑鼠移動事件 - 啟動拖曳"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        # 檢查是否超過拖曳閾值
        if not hasattr(self, 'drag_start_position'):
            return

        distance = (event.pos() - self.drag_start_position).manhattanLength()
        if distance < QApplication.startDragDistance():
            return

        # 建立拖曳物件
        drag = QDrag(self)
        mime_data = QMimeData()

        # 攜帶索引資訊
        mime_data.setData("application/x-thumbnail-index", QByteArray(str(self.index).encode()))
        drag.setMimeData(mime_data)

        # 設定拖曳時的縮圖預覽
        if self.label_thumbnail.pixmap():
            drag.setPixmap(self.label_thumbnail.pixmap().scaled(
                80, 60, Qt.AspectRatioMode.KeepAspectRatio
            ))
            drag.setHotSpot(QPoint(40, 30))

        # 執行拖曳
        drag.exec(Qt.DropAction.MoveAction)

    def set_selected(self, selected: bool):
        """
        設定選中狀態

        Args:
            selected: 是否選中
        """
        self.is_selected = selected
        self._update_style()

    def _update_style(self):
        """更新樣式"""
        if self.is_selected:
            # 選中狀態：藍色邊框
            self.setStyleSheet("""
                ThumbnailItem {
                    background-color: #e3f2fd;
                    border: 2px solid #2196f3;
                    border-radius: 5px;
                }
            """)
            self.label_index.setStyleSheet("color: #2196f3;")
        else:
            # 未選中狀態：灰色邊框
            self.setStyleSheet("""
                ThumbnailItem {
                    background-color: white;
                    border: 2px solid #ddd;
                    border-radius: 5px;
                }
                ThumbnailItem:hover {
                    border-color: #aaa;
                }
            """)
            self.label_index.setStyleSheet("color: #333;")


class ThumbnailList(QWidget):
    """
    縮圖列表

    功能:
    - 顯示 3 張圖片的縮圖
    - 支援拖曳排序
    - 點選切換當前圖片
    """

    thumbnail_clicked = pyqtSignal(int)  # 縮圖點選訊號（引數：索引）
    order_changed = pyqtSignal(int, int)  # 順序改變訊號（引數：idx1, idx2）

    def __init__(self, parent=None):
        """初始化縮圖列表"""
        super().__init__(parent)

        self.thumbnails: list[ThumbnailItem] = []
        self.current_index = -1

        # 啟用拖曳接受
        self.setAcceptDrops(True)

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # 標題
        title = QLabel("圖片列表")
        title.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 縮圖容器
        self.thumbnail_layout = QVBoxLayout()
        self.thumbnail_layout.setSpacing(10)
        layout.addLayout(self.thumbnail_layout)

        layout.addStretch()

        # 提示標籤
        self.hint_label = QLabel("請先掃描案件資料夾")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setStyleSheet("color: #999; font-size: 12px;")
        layout.addWidget(self.hint_label)

    def load_images(self, image_paths: list[str]):
        """
        載入圖片列表

        Args:
            image_paths: 圖片路徑列表（最多3張）
        """
        # 清空現有縮圖
        self.clear()

        # 建立新縮圖
        for i, img_path in enumerate(image_paths[:3]):
            thumbnail = ThumbnailItem(i, img_path)
            thumbnail.clicked.connect(self._on_thumbnail_clicked)

            self.thumbnails.append(thumbnail)
            self.thumbnail_layout.addWidget(thumbnail)

        # 預設選中第一張
        if self.thumbnails:
            self.set_current_index(0)
            self.hint_label.hide()
        else:
            self.hint_label.show()

    def clear(self):
        """清空縮圖列表"""
        # 移除所有縮圖
        for thumbnail in self.thumbnails:
            self.thumbnail_layout.removeWidget(thumbnail)
            thumbnail.deleteLater()

        self.thumbnails.clear()
        self.current_index = -1
        self.hint_label.setText("請先掃描案件資料夾")
        self.hint_label.show()

    def set_current_index(self, index: int):
        """
        設定當前選中的縮圖

        Args:
            index: 索引（0-2）
        """
        if index < 0 or index >= len(self.thumbnails):
            return

        # 取消之前的選中
        if 0 <= self.current_index < len(self.thumbnails):
            self.thumbnails[self.current_index].set_selected(False)

        # 選中新的縮圖
        self.current_index = index
        self.thumbnails[index].set_selected(True)

    def _on_thumbnail_clicked(self, index: int):
        """縮圖點選槽函式"""
        self.set_current_index(index)
        self.thumbnail_clicked.emit(index)

    def dragEnterEvent(self, event):
        """拖曳進入事件 - 檢查是否接受拖曳"""
        if event.mimeData().hasFormat("application/x-thumbnail-index"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖曳移動事件 - 持續接受拖曳"""
        if event.mimeData().hasFormat("application/x-thumbnail-index"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """
        拖曳釋放事件 - 執行交換

        從 MimeData 獲取源索引，根據釋放位置計算目標索引，
        呼叫 DataManager.swap_images 進行交換，並重新整理 UI。
        """
        if not event.mimeData().hasFormat("application/x-thumbnail-index"):
            event.ignore()
            return

        # 獲取源索引
        source_index = int(event.mimeData().data("application/x-thumbnail-index").data().decode())

        # 計算目標索引（根據釋放位置判斷）
        target_index = self._get_target_index_at_pos(event.position().toPoint())

        if target_index is None or source_index == target_index:
            event.ignore()
            return

        # 呼叫 DataManager 進行交換（同時交換 paths 和 states）
        from core.grid4.data_manager import get_data_manager
        data_manager = get_data_manager()
        current_case = data_manager.get_current_case()

        if current_case:
            data_manager.swap_images(current_case, source_index, target_index)

            # 重新整理 UI（重新載入圖片列表）
            self.load_images(current_case.image_paths)

            # 保持原來選中的位置
            self.set_current_index(target_index)

            # 傳送順序改變訊號
            self.order_changed.emit(source_index, target_index)

        event.acceptProposedAction()

    def _get_target_index_at_pos(self, pos) -> int:
        """
        根據位置計算目標索引

        Args:
            pos: 釋放位置 (相對於 ThumbnailList)

        Returns:
            目標索引 (0-2)，如果無效返回 None
        """
        for i, thumbnail in enumerate(self.thumbnails):
            # 獲取縮圖在 ThumbnailList 中的位置
            thumb_rect = thumbnail.geometry()
            if thumb_rect.contains(pos):
                return i

        return None


if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    # 測試縮圖列表
    app = QApplication(sys.argv)

    widget = ThumbnailList()

    # 測試載入圖片（使用測試圖片）
    test_images = [
        "tmp/test_cases/case001/img1.jpg",
        "tmp/test_cases/case001/img2.jpg",
        "tmp/test_cases/case001/img3.jpg",
    ]

    widget.load_images(test_images)
    widget.show()

    sys.exit(app.exec())
