"""
編輯元素模組

自定義 QGraphicsItem 子類用於箭頭
"""

import math

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsPixmapItem


class ResizablePixmapItem(QGraphicsPixmapItem):
    """
    可縮放的圖片元素 (用於子圖/畫中畫)

    特性:
    - 鎖定長寬比縮放
    - 僅支援四角拖拽
    - 邊界限制
    - 所見即所得樣式
    """

    HANDLE_SIZE = 10
    HIT_TEST_SIZE = 40

    HANDLE_TOP_LEFT = 0
    HANDLE_TOP_RIGHT = 1
    HANDLE_BOTTOM_LEFT = 2
    HANDLE_BOTTOM_RIGHT = 3

    def __init__(self, pixmap: QPixmap, parent: QGraphicsItem | None = None):
        super().__init__(pixmap, parent)

        # 設定標誌
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        # 拖拽狀態
        self.is_resizing = False
        self.resize_handle = None
        self.resize_start_pos = None
        self.resize_start_rect = None
        self.resize_start_pixmap = None
        self.original_aspect_ratio = None
        self.source_roi = None  # 原始裁切區域 (Scene 座標)

        if pixmap and not pixmap.isNull():
            self.original_aspect_ratio = pixmap.width() / pixmap.height()

        self.scene_bounds = QRectF(0, 0, 4096, 3000)  # 預設值，之後需設定

    def set_scene_bounds(self, bounds: QRectF):
        self.scene_bounds = bounds

    def set_source_roi(self, roi: QRectF):
        self.source_roi = roi

    def get_final_geometry(self) -> tuple:
        rect = self.sceneBoundingRect()
        return (rect.x(), rect.y(), rect.width(), rect.height())

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            self._draw_handles(painter)

    def _draw_handles(self, painter: QPainter):
        rect = self.boundingRect()
        pen = QPen(QColor(0, 120, 215), 2)
        painter.setPen(pen)
        painter.setBrush(QColor(255, 255, 255))
        handle_size = self.HANDLE_SIZE

        corners = [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]

        for corner in corners:
            handle_rect = QRectF(
                corner.x() - handle_size / 2,
                corner.y() - handle_size / 2,
                handle_size,
                handle_size,
            )
            painter.drawRect(handle_rect)

    def _get_handle_at_pos(self, pos: QPointF) -> int | None:
        rect = self.boundingRect()
        hit_size = self.HIT_TEST_SIZE
        corners = [
            (rect.topLeft(), self.HANDLE_TOP_LEFT),
            (rect.topRight(), self.HANDLE_TOP_RIGHT),
            (rect.bottomLeft(), self.HANDLE_BOTTOM_LEFT),
            (rect.bottomRight(), self.HANDLE_BOTTOM_RIGHT),
        ]

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
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            handle = self._get_handle_at_pos(pos)

            if handle is not None:
                self.is_resizing = True
                self.resize_handle = handle
                self.resize_start_pos = event.scenePos()
                self.resize_start_rect = self.sceneBoundingRect()
                self.resize_start_pixmap = self.pixmap()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_resizing:
            self._handle_resize(event)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_resizing:
            self.is_resizing = False
            self.resize_handle = None
            self.resize_start_pixmap = None
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def hoverMoveEvent(self, event):
        if not self.isSelected():
            super().hoverMoveEvent(event)
            return

        pos = event.pos()
        handle = self._get_handle_at_pos(pos)

        if handle is not None:
            if handle == self.HANDLE_TOP_LEFT or handle == self.HANDLE_BOTTOM_RIGHT:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        event.accept()

    def _handle_resize(self, event):
        if not self.original_aspect_ratio or not self.resize_start_rect or not self.resize_start_pixmap:
            return

        current_pos = event.scenePos()
        delta = current_pos - self.resize_start_pos
        start_rect = self.resize_start_rect

        if self.resize_handle == self.HANDLE_TOP_LEFT:
            new_width = start_rect.width() - delta.x()
            new_height = new_width / self.original_aspect_ratio
            new_x = start_rect.x() + delta.x()
            new_y = start_rect.y() + (start_rect.height() - new_height)
        elif self.resize_handle == self.HANDLE_TOP_RIGHT:
            new_width = start_rect.width() + delta.x()
            new_height = new_width / self.original_aspect_ratio
            new_x = start_rect.x()
            new_y = start_rect.y() + (start_rect.height() - new_height)
        elif self.resize_handle == self.HANDLE_BOTTOM_LEFT:
            new_width = start_rect.width() - delta.x()
            new_height = new_width / self.original_aspect_ratio
            new_x = start_rect.x() + delta.x()
            new_y = start_rect.y()
        else:
            new_width = start_rect.width() + delta.x()
            new_height = new_width / self.original_aspect_ratio
            new_x = start_rect.x()
            new_y = start_rect.y()

        MIN_SIZE = 50
        if new_width < MIN_SIZE or new_height < MIN_SIZE:
            return

        # Simple bounds check (clamping)
        if new_x < self.scene_bounds.left():
            new_x = self.scene_bounds.left()
        if new_y < self.scene_bounds.top():
            new_y = self.scene_bounds.top()

        # Apply strict aspect ratio scaling
        scaled_pixmap = self.resize_start_pixmap.scaled(
            int(new_width), int(new_height),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled_pixmap)
        self.setPos(new_x, new_y)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value
            rect = self.boundingRect()
            item_rect = QRectF(new_pos.x(), new_pos.y(), rect.width(), rect.height())

            if not self.scene_bounds.contains(item_rect):
                # Clamp position
                x = max(self.scene_bounds.left(), min(new_pos.x(), self.scene_bounds.right() - rect.width()))
                y = max(self.scene_bounds.top(), min(new_pos.y(), self.scene_bounds.bottom() - rect.height()))
                new_pos.setX(x)
                new_pos.setY(y)
            return new_pos
        return super().itemChange(change, value)


class ArrowItem(QGraphicsLineItem):
    """
    箭頭圖形元素

    功能:
    - 顯示從起點到終點的箭頭
    - 箭頭末端帶三角形箭頭
    - 可配置顏色和粗細
    """

    def __init__(self, start_pos: QPointF, end_pos: QPointF,
                 color: str = "#FF0000", width: int = 5):
        """
        初始化箭頭

        Args:
            start_pos: 起點位置 (Scene 座標)
            end_pos: 終點位置 (Scene 座標)
            color: 箭頭顏色 (hex)
            width: 箭頭粗細
        """
        super().__init__()

        # 設定線段
        self.setLine(QLineF(start_pos, end_pos))

        # 設定樣式
        pen = QPen(QColor(color))
        pen.setWidth(width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)

        # 設定可選中
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

        # 箭頭引數 (加大箭頭頭部比例)
        self.arrow_size = width * 6  # 箭頭大小與線寬成比例
        self.arrow_color = QColor(color)

    def paint(self, painter, option, widget=None):
        """
        繪製箭頭

        Args:
            painter: QPainter 物件
            option: 繪製選項
            widget: 部件 (可選)
        """
        line = self.line()

        # 計算箭頭角度
        angle = math.atan2(-line.dy(), line.dx())

        # 箭頭三角形的三個頂點
        arrow_p1 = line.p2()  # 箭頭尖端

        # 左側點
        arrow_p2 = arrow_p1 - QPointF(
            math.cos(angle - math.pi / 6) * self.arrow_size,
            -math.sin(angle - math.pi / 6) * self.arrow_size
        )

        # 右側點
        arrow_p3 = arrow_p1 - QPointF(
            math.cos(angle + math.pi / 6) * self.arrow_size,
            -math.sin(angle + math.pi / 6) * self.arrow_size
        )

        # 計算線段縮短距離（避免粗線覆蓋箭頭三角形尖端）
        shorten = self.arrow_size * math.cos(math.pi / 6)
        shortened_end = QPointF(
            line.p2().x() - math.cos(angle) * shorten,
            line.p2().y() + math.sin(angle) * shorten
        )

        # 繪製縮短後的線段
        painter.setPen(self.pen())
        painter.drawLine(QLineF(line.p1(), shortened_end))

        # 繪製填充三角形
        arrow_head = QPolygonF([arrow_p1, arrow_p2, arrow_p3])
        painter.setBrush(QBrush(self.arrow_color))
        painter.setPen(QPen(self.arrow_color))
        painter.drawPolygon(arrow_head)

    def boundingRect(self):
        """
        返回邊界矩形

        Returns:
            邊界矩形
        """
        extra = (self.pen().width() + self.arrow_size) / 2.0
        p1 = self.line().p1()
        p2 = self.line().p2()

        return QRectF(p1, p2).normalized().adjusted(-extra, -extra, extra, extra)


if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView

    # 測試箭頭和標註點
    app = QApplication(sys.argv)

    # 建立場景和檢視
    scene = QGraphicsScene(0, 0, 800, 600)
    view = QGraphicsView(scene)

    # 新增箭頭
    arrow1 = ArrowItem(QPointF(100, 100), QPointF(300, 200), "#FF0000", 5)
    scene.addItem(arrow1)

    arrow2 = ArrowItem(QPointF(200, 300), QPointF(400, 400), "#00FF00", 8)
    scene.addItem(arrow2)

    view.resize(800, 600)
    view.show()

    sys.exit(app.exec())
