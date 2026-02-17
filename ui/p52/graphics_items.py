"""
自定義圖形元件模組

提供可縮放的子圖元件,支持:
- 鎖定長寬比縮放
- 四角拖拽手柄
- 所見即所得樣式
"""

from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsItem
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QColor, QPainter, QPixmap
from typing import Optional


class ResizablePixmapItem(QGraphicsPixmapItem):
    """
    可縮放的圖片元件

    特性:
    - 鎖定長寬比縮放
    - 僅支持四角拖拽 (不支持邊框中間拖拽)
    - 邊界限制 (不能拖出 Scene 範圍)
    - 所見即所得樣式
    """

    # 拖拽手柄大小 (像素)
    HANDLE_SIZE = 10  # 視覺大小
    HIT_TEST_SIZE = 40  # 擊中判定範圍（感應區域）

    # 拖拽手柄類型
    HANDLE_TOP_LEFT = 0
    HANDLE_TOP_RIGHT = 1
    HANDLE_BOTTOM_LEFT = 2
    HANDLE_BOTTOM_RIGHT = 3

    def __init__(self, pixmap: QPixmap, parent: Optional[QGraphicsItem] = None):
        """
        初始化可縮放圖片元件

        Args:
            pixmap: 圖片
            parent: 父元件
        """
        super().__init__(pixmap, parent)

        # 設置標誌
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)  # 啟用懸停事件

        # 拖拽狀態
        self.is_resizing = False
        self.resize_handle = None  # 當前拖拽的手柄
        self.resize_start_pos = None  # 開始拖拽時的滑鼠位置
        self.resize_start_rect = None  # 開始拖拽時的矩形
        self.resize_start_pixmap = None  # 開始拖拽時的原始圖片（避免重複重採樣）
        self.original_aspect_ratio = None  # 原始長寬比

        # 原始裁切區域（Scene 座標）
        self.source_roi = None

        # 計算原始長寬比
        if pixmap and not pixmap.isNull():
            self.original_aspect_ratio = pixmap.width() / pixmap.height()

        # Scene 邊界 (4096x3000)
        self.scene_bounds = QRectF(0, 0, 4096, 3000)

    def set_scene_bounds(self, bounds: QRectF):
        """
        設置 Scene 邊界

        Args:
            bounds: Scene 邊界矩形
        """
        self.scene_bounds = bounds

    def set_source_roi(self, roi: QRectF):
        """
        設置原始裁切區域

        Args:
            roi: 原始裁切區域（Scene 座標）
        """
        self.source_roi = roi

    def get_final_geometry(self) -> tuple:
        """
        獲取最終幾何信息（Scene 座標）

        Returns:
            (x, y, width, height) - 子圖在 Scene 上的最終位置和尺寸
        """
        rect = self.sceneBoundingRect()
        return (rect.x(), rect.y(), rect.width(), rect.height())

    def paint(self, painter: QPainter, option, widget=None):
        """
        繪製元件

        繪製圖片和拖拽手柄

        Args:
            painter: 畫筆
            option: 選項
            widget: 部件
        """
        # 繪製圖片
        super().paint(painter, option, widget)

        # 如果被選中,繪製拖拽手柄
        if self.isSelected():
            self._draw_handles(painter)

    def _draw_handles(self, painter: QPainter):
        """
        繪製四角拖拽手柄

        Args:
            painter: 畫筆
        """
        rect = self.boundingRect()

        # 設置畫筆
        pen = QPen(QColor(0, 120, 215), 2)  # 藍色
        painter.setPen(pen)
        painter.setBrush(QColor(255, 255, 255))  # 白色填充

        # 計算手柄大小 (基於視圖縮放)
        handle_size = self.HANDLE_SIZE

        # 四個角的位置
        corners = [
            rect.topLeft(),  # 左上
            rect.topRight(),  # 右上
            rect.bottomLeft(),  # 左下
            rect.bottomRight(),  # 右下
        ]

        # 繪製四個角的手柄
        for corner in corners:
            handle_rect = QRectF(
                corner.x() - handle_size / 2,
                corner.y() - handle_size / 2,
                handle_size,
                handle_size,
            )
            painter.drawRect(handle_rect)

    def _get_handle_at_pos(self, pos: QPointF) -> Optional[int]:
        """
        獲取位置處的拖拽手柄（使用更大的擊中區域）

        Args:
            pos: 位置 (Item 座標系)

        Returns:
            手柄類型,如果沒有則返回 None
        """
        rect = self.boundingRect()
        hit_size = self.HIT_TEST_SIZE  # 使用擊中判定大小（40px）

        # 四個角的位置和對應的手柄類型
        corners = [
            (rect.topLeft(), self.HANDLE_TOP_LEFT),
            (rect.topRight(), self.HANDLE_TOP_RIGHT),
            (rect.bottomLeft(), self.HANDLE_BOTTOM_LEFT),
            (rect.bottomRight(), self.HANDLE_BOTTOM_RIGHT),
        ]

        # 檢查滑鼠是否在某個手柄上（使用更大的感應區域）
        for corner_pos, handle_type in corners:
            handle_rect = QRectF(
                corner_pos.x() - hit_size / 2,
                corner_pos.y() - hit_size / 2,
                hit_size,
                hit_size,
            )
            if handle_rect.contains(pos):
                return handle_type

        return None

    def mousePressEvent(self, event):
        """
        滑鼠按下事件

        Args:
            event: 事件對象
        """
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            handle = self._get_handle_at_pos(pos)

            if handle is not None:
                # 開始縮放
                self.is_resizing = True
                self.resize_handle = handle
                self.resize_start_pos = event.scenePos()
                self.resize_start_rect = self.sceneBoundingRect()
                self.resize_start_pixmap = self.pixmap()  # 記錄原始圖片，避免重複重採樣
                event.accept()
                return

        # 如果不是縮放,則繼續移動邏輯
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        滑鼠移動事件

        Args:
            event: 事件對象
        """
        if self.is_resizing:
            self._handle_resize(event)
            event.accept()
        else:
            # 移動邏輯
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        滑鼠釋放事件

        Args:
            event: 事件對象
        """
        if event.button() == Qt.MouseButton.LeftButton and self.is_resizing:
            self.is_resizing = False
            self.resize_handle = None
            self.resize_start_pixmap = None  # 清理，釋放內存
            self.unsetCursor()  # 恢復默認游標
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def hoverMoveEvent(self, event):
        """
        滑鼠懸停移動事件 - 動態更新游標形狀

        Args:
            event: 事件對象
        """
        # 只有在選中時才顯示縮放游標
        if not self.isSelected():
            super().hoverMoveEvent(event)
            return

        pos = event.pos()
        handle = self._get_handle_at_pos(pos)

        if handle is not None:
            # 根據控制點位置設置對應的縮放游標
            if handle == self.HANDLE_TOP_LEFT or handle == self.HANDLE_BOTTOM_RIGHT:
                # ↖↘ 對角線縮放
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:  # TOP_RIGHT or BOTTOM_LEFT
                # ↗↙ 反對角線縮放
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            # 不在控制點上，顯示移動游標
            self.setCursor(Qt.CursorShape.SizeAllCursor)

        event.accept()

    def _handle_resize(self, event):
        """
        處理縮放操作 - 基於四角拖拽，鎖定長寬比

        關鍵: 每次縮放都基於 resize_start_pixmap，避免重複重採樣

        Args:
            event: 滑鼠事件
        """
        if not self.original_aspect_ratio or not self.resize_start_rect:
            return

        # 使用拖拽開始時記錄的原始圖片
        if not self.resize_start_pixmap:
            return

        current_pos = event.scenePos()
        delta = current_pos - self.resize_start_pos

        # 獲取開始拖拽時的矩形
        start_rect = self.resize_start_rect

        # 根據拖拽的角計算新尺寸
        if self.resize_handle == self.HANDLE_TOP_LEFT:
            # 左上角: 向左上拖拽 = 縮小，向右下拖拽 = 放大
            new_width = start_rect.width() - delta.x()
            new_height = new_width / self.original_aspect_ratio
            new_x = start_rect.x() + delta.x()
            new_y = start_rect.y() + (start_rect.height() - new_height)

        elif self.resize_handle == self.HANDLE_TOP_RIGHT:
            # 右上角
            new_width = start_rect.width() + delta.x()
            new_height = new_width / self.original_aspect_ratio
            new_x = start_rect.x()
            new_y = start_rect.y() + (start_rect.height() - new_height)

        elif self.resize_handle == self.HANDLE_BOTTOM_LEFT:
            # 左下角
            new_width = start_rect.width() - delta.x()
            new_height = new_width / self.original_aspect_ratio
            new_x = start_rect.x() + delta.x()
            new_y = start_rect.y()

        else:  # HANDLE_BOTTOM_RIGHT
            # 右下角: 向右下拖拽 = 放大，向左上拖拽 = 縮小
            new_width = start_rect.width() + delta.x()
            new_height = new_width / self.original_aspect_ratio
            new_x = start_rect.x()
            new_y = start_rect.y()

        # 最小尺寸限制
        MIN_SIZE = 50
        if new_width < MIN_SIZE or new_height < MIN_SIZE:
            return

        # 邊界限制 (Clamp 而非硬阻擋)
        # 限制位置
        if new_x < self.scene_bounds.left():
            new_x = self.scene_bounds.left()
        if new_y < self.scene_bounds.top():
            new_y = self.scene_bounds.top()

        # 限制尺寸
        max_width = self.scene_bounds.right() - new_x
        max_height = self.scene_bounds.bottom() - new_y
        if new_width > max_width:
            new_width = max_width
            new_height = new_width / self.original_aspect_ratio
        if new_height > max_height:
            new_height = max_height
            new_width = new_height * self.original_aspect_ratio

        # 再次檢查最小尺寸
        if new_width < MIN_SIZE or new_height < MIN_SIZE:
            return

        # 應用新尺寸：基於 resize_start_pixmap 縮放
        scaled_pixmap = self.resize_start_pixmap.scaled(
            int(new_width),
            int(new_height),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.setPixmap(scaled_pixmap)
        self.setPos(new_x, new_y)

    def itemChange(self, change, value):
        """
        元件變化事件

        用於限制移動邊界

        Args:
            change: 變化類型
            value: 新值

        Returns:
            實際應用的值
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # 限制位置在 scene_bounds 內
            new_pos = value
            rect = self.boundingRect()

            # 計算元件在新位置的邊界
            item_rect = QRectF(
                new_pos.x(), new_pos.y(), rect.width(), rect.height()
            )

            # 如果超出邊界,調整位置
            if not self.scene_bounds.contains(item_rect):
                # 限制 x
                if item_rect.left() < self.scene_bounds.left():
                    new_pos.setX(self.scene_bounds.left())
                elif item_rect.right() > self.scene_bounds.right():
                    new_pos.setX(self.scene_bounds.right() - rect.width())

                # 限制 y
                if item_rect.top() < self.scene_bounds.top():
                    new_pos.setY(self.scene_bounds.top())
                elif item_rect.bottom() > self.scene_bounds.bottom():
                    new_pos.setY(self.scene_bounds.bottom() - rect.height())

            return new_pos

        return super().itemChange(change, value)

    def get_roi_rect(self) -> QRectF:
        """
        獲取 ROI 矩形 (Scene 座標系)

        Returns:
            ROI 矩形
        """
        return self.sceneBoundingRect()
