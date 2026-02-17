"""
畫布檢視模組

顯示和編輯當前圖片 (QGraphicsView 架構)
"""

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QBrush, QCursor, QPen, QPolygonF, QWheelEvent
from PIL import Image, ImageEnhance
from pathlib import Path
from typing import Optional, Tuple, List
from enum import Enum

from ui.grid4.edit_items import ArrowItem, ResizablePixmapItem
from core.image_enhancement import ImageEnhancementManager
from core.grid4.config_manager import get_config
from core.grid4.edit_history import EditHistory, EditSnapshot


class EditMode(Enum):
    """編輯模式"""
    VIEW = "view"       # 檢視模式（平移/縮放）
    ARROW = "arrow"     # 箭頭模式


class CanvasView(QGraphicsView):
    """
    畫布檢視 (基於 QGraphicsView + QGraphicsScene)

    功能:
    - 顯示當前選中的圖片
    - 支援縮放 (Ctrl+滾輪) 和平移 (右鍵拖拽)
    - 支援繪製箭頭和標註 (Phase 2-3 實現)
    - Scene 座標系統: 4096x3000 (固定)
    """

    # 訊號
    history_changed = pyqtSignal(bool, bool)  # (can_undo, can_redo)

    # 預設佔位符尺寸 (僅在無圖片時使用)
    DEFAULT_PLACEHOLDER_SIZE = (800, 600)

    def __init__(self, parent=None):
        """初始化畫布檢視"""
        super().__init__(parent)

        # 建立 Scene (初始大小使用佔位符尺寸，載入圖片後會動態調整)
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, *self.DEFAULT_PLACEHOLDER_SIZE)
        self.setScene(self.scene)

        # 圖片項
        self.image_item: Optional[QGraphicsPixmapItem] = None
        self.current_image_path: Optional[str] = None
        self.current_pil_image: Optional[Image.Image] = None  # 儲存原始 PIL 圖片
        self.current_image_index: int = -1  # 當前圖片索引（用於狀態持久化）

        # 佔位符文字項
        self.placeholder_text: Optional[QGraphicsTextItem] = None

        # 縮放/平移狀態
        self.zoom_factor = 1.0
        self.user_zoomed = False  # 跟蹤使用者是否手動縮放過
        self.is_panning = False
        self.pan_start_pos = None

        # 編輯模式
        self.edit_mode = EditMode.VIEW
        self.config = get_config()

        # 箭頭列表
        self.arrows: List[ArrowItem] = []
        self.temp_arrow_item: Optional[ArrowItem] = None
        self.arrow_start_pos: Optional[QPointF] = None

        # 子圖/框選
        self.current_subimage: Optional[ResizablePixmapItem] = None
        self.is_selecting = False
        self.selection_start: Optional[QPointF] = None
        self.selection_rect_item = None

        # 影象增強管理器
        self.enhancement_manager = ImageEnhancementManager()
        self.enhancement_manager.enhancement_finished.connect(self._on_enhancement_finished)

        # 當前影象增強引數
        self.current_brightness = 0
        self.current_contrast = 0
        self.current_saturation = 0
        self.current_sharpness = 0

        # 編輯歷史（撤銷/重做）
        self.edit_history = EditHistory(max_history=50)

        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        # 渲染設定
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        # 背景色
        self.setBackgroundBrush(QBrush(QColor("#f5f5f5")))

        # 最小尺寸
        self.setMinimumSize(400, 300)

        # 顯示佔位符
        self._show_placeholder("請選擇一張圖片", "#999")

    def _get_scaled_arrow_width(self) -> int:
        """
        根據圖片解析度動態計算箭頭寬度

        基準: 1200px 圖片使用基礎寬度
        高解析度圖片會自動放大箭頭
        """
        base_width = self.config.get("default_arrow_width", 15)
        
        if not self.image_item or not self.image_item.pixmap():
            return base_width
            
        # 圖片寬度
        img_width = self.image_item.pixmap().width()
        base_resolution = 1200  # 基準解析度
        
        # 縮放因子 (至少 1.0)
        scale_factor = max(1.0, img_width / base_resolution)
        
        return int(base_width * scale_factor)

    def _show_placeholder(self, text: str, color: str = "#999"):
        """
        顯示佔位符文字

        Args:
            text: 佔位符文字
            color: 文字顏色
        """
        # 移除現有佔位符
        if self.placeholder_text:
            self.scene.removeItem(self.placeholder_text)

        # 建立文字項
        self.placeholder_text = QGraphicsTextItem(text)
        font = QFont("Microsoft YaHei UI", 16)
        self.placeholder_text.setFont(font)
        self.placeholder_text.setDefaultTextColor(QColor(color))

        # 居中顯示 (使用當前 Scene 尺寸)
        scene_rect = self.scene.sceneRect()
        rect = self.placeholder_text.boundingRect()
        x = (scene_rect.width() - rect.width()) / 2
        y = (scene_rect.height() - rect.height()) / 2
        self.placeholder_text.setPos(x, y)

        self.scene.addItem(self.placeholder_text)

    def load_image(self, image_path: str, image_index: int = 0, save_state: bool = True):
        """
        載入並顯示圖片

        Args:
            image_path: 圖片路徑
            image_index: 圖片索引（用於狀態持久化）
            save_state: 是否儲存當前狀態
        """
        # 儲存當前圖片的編輯狀態（如果需要）
        if save_state and self.current_image_index >= 0:
            self._save_current_state_to_data_manager()

        try:
            self.current_image_path = image_path
            self.current_image_index = image_index

            # 移除佔位符
            if self.placeholder_text:
                self.scene.removeItem(self.placeholder_text)
                self.placeholder_text = None

            # 使用 PIL 載入圖片
            pil_image = Image.open(image_path)
            pil_image = pil_image.convert("RGB")
            self.current_pil_image = pil_image  # 儲存原始圖片

            # 轉換為 QImage
            data = pil_image.tobytes("raw", "RGB")
            qimage = QImage(
                data,
                pil_image.width,
                pil_image.height,
                pil_image.width * 3,
                QImage.Format.Format_RGB888
            )
            pixmap = QPixmap.fromImage(qimage)

            # 移除現有圖片
            if self.image_item:
                self.scene.removeItem(self.image_item)

            # === 動態適應: Scene 尺寸 = 圖片尺寸 ===
            # 這確保了 Scene 座標系與圖片畫素座標系完全一致
            self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())

            # 建立圖片項 (原尺寸，無縮放)
            self.image_item = QGraphicsPixmapItem(pixmap)
            self.image_item.setPos(0, 0)  # 圖片放置於原點
            self.scene.addItem(self.image_item)

            # 適應檢視 (將整個圖片縮放到視窗中，保持比例)
            self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)

            # 重置縮放因子和標誌
            self.zoom_factor = 1.0
            self.user_zoomed = False

        except Exception as e:
            # 載入失敗，顯示錯誤佔位符
            error_text = f"載入失敗\n\n{Path(image_path).name}\n\n錯誤: {e}"
            self._show_placeholder(error_text, "#d32f2f")

        # 設定原始圖片到增強管理器
        if self.current_pil_image:
            self.enhancement_manager.set_original_image(self.current_pil_image)

        # 恢復圖片的編輯狀態
        self._restore_state_from_data_manager()

        # 立即應用影象增強（確保 Canvas 顯示與 Undo 狀態一致 - 即使用 Padded Canvas）
        self.apply_enhancements(
            self.current_brightness,
            self.current_contrast,
            self.current_saturation,
            self.current_sharpness
        )

    def _save_current_state_to_data_manager(self):
        """儲存當前圖片的編輯狀態到 DataManager"""
        from core.grid4.data_manager import get_data_manager

        data_manager = get_data_manager()
        current_case = data_manager.get_current_case()

        if current_case and 0 <= self.current_image_index < len(current_case.image_states):
            image_state = current_case.image_states[self.current_image_index]

            # 儲存箭頭
            self.save_arrows_to_state(image_state)

            # 儲存子圖
            if self.current_subimage and self.current_pil_image:
                 src = self.current_subimage.source_roi 
                 
                 # 計算 Target (Scene Rect -> Normalized Image Coords)
                 scene_rect = self.current_subimage.sceneBoundingRect()
                 
                 # Scene -> Pixmap Coords
                 item_polygon = self.image_item.mapFromScene(scene_rect)
                 item_rect = item_polygon.boundingRect() 
                 
                 w, h = self.current_pil_image.size
                 t_x = item_rect.x() / w
                 t_y = item_rect.y() / h
                 t_w = item_rect.width() / w
                 t_h = item_rect.height() / h
                 
                 image_state.sub_image = {
                     "source": [src.x(), src.y(), src.width(), src.height()],
                     "target": [t_x, t_y, t_w, t_h]
                 }
            else:
                 image_state.sub_image = None

            # 儲存影象增強引數
            image_state.brightness = self.current_brightness
            image_state.contrast = self.current_contrast
            image_state.saturation = self.current_saturation
            image_state.sharpness = self.current_sharpness

    def _restore_state_from_data_manager(self):
        """從 DataManager 恢復圖片的編輯狀態"""
        from core.grid4.data_manager import get_data_manager

        data_manager = get_data_manager()
        current_case = data_manager.get_current_case()

        if current_case and 0 <= self.current_image_index < len(current_case.image_states):
            image_state = current_case.image_states[self.current_image_index]

            # 恢復箭頭
            self.restore_arrows_from_state(image_state)

            # 恢復子圖
            if self.current_subimage:
                self.scene.removeItem(self.current_subimage)
                self.current_subimage = None
                
            if image_state.sub_image and self.current_pil_image:
                 self._restore_subimage_from_data(image_state.sub_image)

            # 恢復影象增強引數（透過 ControlPanel）
            # 注意：不直接呼叫 apply_enhancements，而是讓 MainWindow 更新滑塊
            self.current_brightness = image_state.brightness
            self.current_contrast = image_state.contrast
            self.current_saturation = image_state.saturation
            self.current_sharpness = image_state.sharpness

    def apply_enhancements(self, brightness: int, contrast: int,
                           saturation: int, sharpness: int):
        """
        應用影象增強

        Args:
            brightness: 亮度調整 (-100 ~ 100)
            contrast: 對比度調整 (-100 ~ 100)
            saturation: 飽和度調整 (-100 ~ 100)
            sharpness: 銳化調整 (-100 ~ 100)
        """
        if not self.current_pil_image:
            return

        # 儲存當前引數
        self.current_brightness = brightness
        self.current_contrast = contrast
        self.current_saturation = saturation
        self.current_sharpness = sharpness

        # 請求增強（使用 0,0 表示保持原圖尺寸，不強制縮放到 Scene）
        # 這避免了 3:2 圖片被強制拉伸到 4:3 或產生白邊
        self.enhancement_manager.request_enhancement(
            brightness, contrast, saturation, sharpness,
            0, 0
        )

    def _on_enhancement_finished(self, qimage: QImage):
        """
        影象增強完成槽函式

        Args:
            qimage: 處理後的 QImage
        """
        if not self.image_item:
            return

        # 更新圖片項
        pixmap = QPixmap.fromImage(qimage)
        self.image_item.setPixmap(pixmap)

        # 同步更新子圖（畫中畫）
        if self.current_subimage and self.current_pil_image:
            self._update_subimage_from_enhanced()

    def _get_enhanced_pil_image(self) -> Image.Image:
        """
        取得套用當前增強參數後的 PIL 圖片

        Returns:
            增強後的 PIL Image
        """
        img = self.current_pil_image.copy()

        if self.current_brightness != 0:
            factor = 1.0 + (self.current_brightness / 100.0)
            img = ImageEnhance.Brightness(img).enhance(max(0.0, factor))
        if self.current_contrast != 0:
            factor = 1.0 + (self.current_contrast / 100.0)
            img = ImageEnhance.Contrast(img).enhance(max(0.0, factor))
        if self.current_saturation != 0:
            factor = 1.0 + (self.current_saturation / 100.0)
            img = ImageEnhance.Color(img).enhance(max(0.0, factor))
        if self.current_sharpness != 0:
            factor = 1.0 + (self.current_sharpness / 100.0)
            img = ImageEnhance.Sharpness(img).enhance(max(0.0, factor))

        return img

    def _update_subimage_from_enhanced(self):
        """從增強後的圖片重新裁切並更新子圖"""
        if not self.current_subimage or not self.current_subimage.source_roi:
            return

        roi = self.current_subimage.source_roi
        w, h = self.current_pil_image.size

        sx = int(roi.x() * w)
        sy = int(roi.y() * h)
        sw = int(roi.width() * w)
        sh = int(roi.height() * h)

        sx = max(0, sx)
        sy = max(0, sy)
        if sx + sw > w: sw = w - sx
        if sy + sh > h: sh = h - sy
        if sw <= 0 or sh <= 0:
            return

        enhanced = self._get_enhanced_pil_image()
        cropped = enhanced.crop((sx, sy, sx + sw, sy + sh))

        qimage = cropped.toqimage()
        if qimage.format() != QImage.Format.Format_RGB888:
            qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)

        # 縮放到當前子圖顯示大小
        current_size = self.current_subimage.pixmap().size()
        if current_size.width() > 0 and current_size.height() > 0:
            pixmap = pixmap.scaled(
                current_size,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        self.current_subimage.setPixmap(pixmap)

    def get_subimage_pil(self) -> Optional[Image.Image]:
        """
        取得當前子圖的原始裁切 PIL Image（用於 OCR）

        Returns:
            裁切後的 PIL Image，若無子圖則回傳 None
        """
        if not self.current_subimage or not self.current_pil_image:
            return None

        roi = self.current_subimage.source_roi
        if not roi:
            return None

        w, h = self.current_pil_image.size

        sx = int(roi.x() * w)
        sy = int(roi.y() * h)
        sw = int(roi.width() * w)
        sh = int(roi.height() * h)

        # 邊界檢查
        sx = max(0, sx)
        sy = max(0, sy)
        if sx + sw > w:
            sw = w - sx
        if sy + sh > h:
            sh = h - sy
        if sw <= 0 or sh <= 0:
            return None

        # 從增強後圖片裁切（與顯示一致）
        enhanced = self._get_enhanced_pil_image()
        return enhanced.crop((sx, sy, sx + sw, sy + sh))

    def clear(self):
        """清空畫布"""
        self.current_image_path = None
        self.current_pil_image = None

        if self.image_item:
            self.scene.removeItem(self.image_item)
            self.image_item = None

        # 清理子圖
        if self.current_subimage:
            self.scene.removeItem(self.current_subimage)
            self.current_subimage = None

        # 清理箭頭
        self.clear_arrows()

        self._show_placeholder("請選擇一張圖片", "#999")

        # 重置縮放
        self.resetTransform()
        self.zoom_factor = 1.0

    def keyPressEvent(self, event):
        """
        鍵盤事件 - 支援 Delete/Backspace 刪除選中項目
        """
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected_items()
            event.accept()
        else:
            super().keyPressEvent(event)

    def delete_selected_items(self):
        """刪除所有選中的箭頭"""
        changed = False

        # 刪除選中的箭頭
        for arrow in self.arrows[:]:
            if arrow.isSelected():
                self.scene.removeItem(arrow)
                self.arrows.remove(arrow)
                changed = True

        if changed:
            self._push_history()

    def set_edit_mode(self, mode: str):
        """
        設定編輯模式

        Args:
            mode: 模式字串 ("view", "arrow")
        """
        try:
            self.edit_mode = EditMode(mode)

            # 更新游標
            if self.edit_mode == EditMode.VIEW:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            elif self.edit_mode == EditMode.ARROW:
                self.setCursor(Qt.CursorShape.CrossCursor)

        except ValueError:
            # 無效模式，保持當前模式
            pass

    def clear_arrows(self):
        """清空所有箭頭"""
        for arrow in self.arrows:
            self.scene.removeItem(arrow)
        self.arrows.clear()

    def _create_snapshot(self) -> EditSnapshot:
        """
        建立當前編輯狀態的快照

        Returns:
            編輯快照
        """
        # 儲存箭頭（相對座標）
        arrows_data = []
        for arrow in self.arrows:
            line = arrow.line()
            x1, y1 = self.scene_to_relative(line.x1(), line.y1())
            x2, y2 = self.scene_to_relative(line.x2(), line.y2())
            arrows_data.append((x1, y1, x2, y2))

        # 儲存子圖
        sub_image_data = None
        if self.current_subimage and self.current_pil_image:
             src = self.current_subimage.source_roi 
             scene_rect = self.current_subimage.sceneBoundingRect()
             item_polygon = self.image_item.mapFromScene(scene_rect)
             item_rect = item_polygon.boundingRect()
             w, h = self.current_pil_image.size
             
             sub_image_data = {
                 "source": [src.x(), src.y(), src.width(), src.height()],
                 "target": [item_rect.x()/w, item_rect.y()/h, item_rect.width()/w, item_rect.height()/h]
             }

        return EditSnapshot(
            arrows=arrows_data,
            sub_image=sub_image_data,
            brightness=self.current_brightness,
            contrast=self.current_contrast,
            saturation=self.current_saturation,
            sharpness=self.current_sharpness
        )

    def _restore_from_snapshot(self, snapshot: EditSnapshot):
        """
        從快照恢復編輯狀態

        Args:
            snapshot: 編輯快照
        """
        # 清空現有內容
        self.clear_arrows()

        # 恢復箭頭
        arrow_color = self.config.get("default_arrow_color", "#FF0000")
        arrow_width = self._get_scaled_arrow_width()

        for rel_x1, rel_y1, rel_x2, rel_y2 in snapshot.arrows:
            x1, y1 = self.relative_to_scene(rel_x1, rel_y1)
            x2, y2 = self.relative_to_scene(rel_x2, rel_y2)

            arrow = ArrowItem(
                QPointF(x1, y1), QPointF(x2, y2),
                arrow_color, arrow_width
            )
            self.scene.addItem(arrow)
            self.arrows.append(arrow)

        # 恢復子圖
        if self.current_subimage:
            self.scene.removeItem(self.current_subimage)
            self.current_subimage = None
            
        if snapshot.sub_image and self.current_pil_image:
             self._restore_subimage_from_data(snapshot.sub_image)

        # 恢復影象增強引數
        self.apply_enhancements(
            snapshot.brightness,
            snapshot.contrast,
            snapshot.saturation,
            snapshot.sharpness
        )

    def _push_history(self):
        """
        將當前狀態推送到歷史棧
        """
        snapshot = self._create_snapshot()
        self.edit_history.push(snapshot)

        # 傳送歷史改變訊號
        self.history_changed.emit(
            self.edit_history.can_undo(),
            self.edit_history.can_redo()
        )

    def undo(self):
        """撤銷操作"""
        snapshot = self.edit_history.undo()
        if snapshot:
            self._restore_from_snapshot(snapshot)

            # 傳送歷史改變訊號
            self.history_changed.emit(
                self.edit_history.can_undo(),
                self.edit_history.can_redo()
            )

    def redo(self):
        """重做操作"""
        snapshot = self.edit_history.redo()
        if snapshot:
            self._restore_from_snapshot(snapshot)

            # 傳送歷史改變訊號
            self.history_changed.emit(
                self.edit_history.can_undo(),
                self.edit_history.can_redo()
            )

    def wheelEvent(self, event):
        """
        滾輪事件 - 實現縮放功能

        Ctrl+滾輪: 縮放畫布
        使用絕對畫素比例 (transform.m11()) 作為限制，而非相對倍率
        確保高解析度圖片 (6000x4000) 也能放大到原圖的 10 倍
        """
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_in_factor = 1.15
            zoom_out_factor = 1 / zoom_in_factor

            # 獲取當前實際縮放比例 (相對於原圖 1:1)
            current_scale = self.transform().m11()

            if event.angleDelta().y() > 0:
                # 放大：限制最大放大到原圖的 10 倍
                if current_scale < 10.0:
                    self.scale(zoom_in_factor, zoom_in_factor)
                    self.zoom_factor *= zoom_in_factor
                    self.user_zoomed = True
            else:
                # 縮小：限制最小縮小比例 (原圖的 1%)
                if current_scale > 0.01:
                    self.scale(zoom_out_factor, zoom_out_factor)
                    self.zoom_factor *= zoom_out_factor
                    self.user_zoomed = True

            event.accept()
        else:
            # 預設滾動行為
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """
        滑鼠按下事件

        右鍵: 開始平移 (所有模式)
        左鍵: 根據編輯模式執行不同操作
        """
        if event.button() == Qt.MouseButton.RightButton:
            # 右鍵平移（所有模式通用）
            self.is_panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()

        elif event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())

            # 檢查是否點選了現有子圖 (優先處理互動)
            item = self.scene.itemAt(scene_pos, self.transform())
            if isinstance(item, ResizablePixmapItem):
                super().mousePressEvent(event)
                return

            if self.edit_mode == EditMode.ARROW:
                # 箭頭模式：開始繪製箭頭
                self.arrow_start_pos = scene_pos

                # 建立臨時箭頭（起點和終點相同）
                arrow_color = self.config.get("default_arrow_color", "#FF0000")
                arrow_width = self._get_scaled_arrow_width()
                self.temp_arrow_item = ArrowItem(
                    scene_pos, scene_pos, arrow_color, arrow_width
                )
                self.scene.addItem(self.temp_arrow_item)
                event.accept()

            elif self.edit_mode == EditMode.VIEW:
                # 檢視模式：開始框選子圖
                self.is_selecting = True
                self.selection_start = scene_pos

                # 建立臨時選擇框
                if self.selection_rect_item:
                    self.scene.removeItem(self.selection_rect_item)
                
                pen = QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine)
                pen.setCosmetic(True)
                self.selection_rect_item = self.scene.addRect(
                    QRectF(scene_pos, scene_pos), pen
                )
                event.accept()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        滑鼠移動事件

        右鍵拖拽: 平移畫布
        左鍵拖拽 (箭頭模式): 更新箭頭終點
        """
        if self.is_panning and self.pan_start_pos:
            # 平移畫布
            delta = event.pos() - self.pan_start_pos
            self.pan_start_pos = event.pos()

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )

            event.accept()

        elif self.is_selecting and self.selection_rect_item:
            # 更新選擇框
            scene_pos = self.mapToScene(event.pos())
            rect = QRectF(self.selection_start, scene_pos).normalized()
            self.selection_rect_item.setRect(rect)
            event.accept()

        elif self.edit_mode == EditMode.ARROW and self.temp_arrow_item:
            # 更新臨時箭頭的終點
            scene_pos = self.mapToScene(event.pos())
            from PyQt6.QtCore import QLineF
            self.temp_arrow_item.setLine(
                QLineF(self.arrow_start_pos, scene_pos)
            )
            event.accept()

        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        滑鼠釋放事件

        右鍵釋放: 結束平移
        左鍵釋放 (箭頭模式): 完成箭頭繪製
        """
        if event.button() == Qt.MouseButton.RightButton:
            # 結束平移
            self.is_panning = False
            self.pan_start_pos = None

            # 恢復游標
            if self.edit_mode == EditMode.VIEW:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            elif self.edit_mode == EditMode.ARROW:
                self.setCursor(Qt.CursorShape.CrossCursor)

            event.accept()

        elif event.button() == Qt.MouseButton.LeftButton:
            if self.is_selecting:
                # 結束框選
                self.is_selecting = False
                if self.selection_rect_item:
                    rect = self.selection_rect_item.rect()
                    self.scene.removeItem(self.selection_rect_item)
                    self.selection_rect_item = None

                    if rect.width() > 10 and rect.height() > 10:
                        self._create_subimage(rect)
                event.accept()
                return

            if self.edit_mode == EditMode.ARROW and self.temp_arrow_item:
                # 完成箭頭繪製
                line = self.temp_arrow_item.line()

                # 檢查箭頭長度是否足夠（避免誤觸）
                if line.length() > 10:
                    # 儲存箭頭
                    self.arrows.append(self.temp_arrow_item)

                    # 推送歷史
                    self._push_history()
                else:
                    # 長度太短，刪除臨時箭頭
                    self.scene.removeItem(self.temp_arrow_item)

                # 清除臨時狀態
                self.temp_arrow_item = None
                self.arrow_start_pos = None
                event.accept()
            else:
                super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def _create_subimage(self, rect: QRectF):
        """
        建立子圖

        Args:
            rect: 框選矩形 (Scene 座標)
        """
        if not self.image_item or not self.current_pil_image:
            return

        # 移除現有子圖
        if self.current_subimage:
            self.scene.removeItem(self.current_subimage)
            self.current_subimage = None

        # 轉換座標 (Scene -> Image Item -> Original Pixels)
        item_polygon = self.image_item.mapFromScene(rect)
        item_rect = item_polygon.boundingRect()

        ix = int(item_rect.x())
        iy = int(item_rect.y())
        iw = int(item_rect.width())
        ih = int(item_rect.height())

        w, h = self.current_pil_image.size

        # 邊界檢查
        ix = max(0, ix)
        iy = max(0, iy)
        if ix + iw > w: iw = w - ix
        if iy + ih > h: ih = h - iy

        if iw <= 0 or ih <= 0:
            return

        # 從增強後的圖片裁剪（確保子圖與主圖亮度一致）
        enhanced = self._get_enhanced_pil_image()
        cropped_pil = enhanced.crop((ix, iy, ix + iw, iy + ih))

        # 轉換為 QPixmap
        qimage = cropped_pil.toqimage()
        if qimage.format() != QImage.Format.Format_RGB888:
            qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)

        # 縮放用於顯示的 Pixmap (避免過大)
        display_max_width = 300
        if pixmap.width() > display_max_width:
            pixmap_display = pixmap.scaledToWidth(display_max_width, Qt.TransformationMode.SmoothTransformation)
        else:
            pixmap_display = pixmap

        # 建立 Item
        self.current_subimage = ResizablePixmapItem(pixmap_display)
        self.current_subimage.setPos(rect.topLeft())
        self.current_subimage.set_scene_bounds(self.scene.sceneRect())

        # 記錄歸一化 Source ROI (用於 DataManager 儲存)
        norm_roi = QRectF(ix / w, iy / h, iw / w, ih / h)
        self.current_subimage.set_source_roi(norm_roi)

        self.scene.addItem(self.current_subimage)
        self._push_history()

    def _restore_subimage_from_data(self, sub_data: dict):
        """
        從資料恢復子圖

        Args:
            sub_data: 子圖資料 {"source": [...], "target": [...]}
        """
        if not self.current_pil_image or not sub_data:
            return

        w, h = self.current_pil_image.size
        src = sub_data.get("source")
        tgt = sub_data.get("target")

        if not src or not tgt:
            return

        # 1. 恢復 Source Crop
        sx = int(src[0] * w)
        sy = int(src[1] * h)
        sw = int(src[2] * w)
        sh = int(src[3] * h)

        # 邊界檢查
        if sw <= 0 or sh <= 0: return
        sx = max(0, sx)
        sy = max(0, sy)
        if sx + sw > w: sw = w - sx
        if sy + sh > h: sh = h - sy

        cropped_pil = self.current_pil_image.crop((sx, sy, sx + sw, sy + sh))

        # 2. 轉換為 QPixmap
        qimage = cropped_pil.toqimage()
        if qimage.format() != QImage.Format.Format_RGB888:
            qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)

        # 3. 建立 Item
        self.current_subimage = ResizablePixmapItem(pixmap)

        # 4. 恢復位置和大小
        tx = tgt[0] * w
        ty = tgt[1] * h
        tw = tgt[2] * w
        th = tgt[3] * h

        # 對映到 Scene 座標
        img_rect = QRectF(tx, ty, tw, th)
        scene_poly = self.image_item.mapToScene(img_rect)
        scene_rect = scene_poly.boundingRect()

        self.current_subimage.setPos(scene_rect.topLeft())

        # 縮放 Pixmap 以匹配之前的大小
        target_w = int(scene_rect.width())
        target_h = int(scene_rect.height())

        if target_w > 0 and target_h > 0:
            final_pixmap = pixmap.scaled(
                target_w, target_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.current_subimage.setPixmap(final_pixmap)

        self.current_subimage.set_source_roi(QRectF(*src))
        self.current_subimage.set_scene_bounds(self.scene.sceneRect())
        self.scene.addItem(self.current_subimage)

    def save_arrows_to_state(self, image_state) -> None:
        """
        儲存箭頭到 ImageState (相對座標)

        Args:
            image_state: ImageState 物件
        """
        image_state.arrows.clear()

        for arrow in self.arrows:
            line = arrow.line()
            # Scene 座標 → 相對座標
            x1, y1 = self.scene_to_relative(line.x1(), line.y1())
            x2, y2 = self.scene_to_relative(line.x2(), line.y2())
            image_state.arrows.append((x1, y1, x2, y2))

    def restore_arrows_from_state(self, image_state) -> None:
        """
        從 ImageState 恢復箭頭 (相對座標 → Scene 座標)

        Args:
            image_state: ImageState 物件
        """
        # 清空現有箭頭
        self.clear_arrows()

        # 恢復箭頭
        arrow_color = self.config.get("default_arrow_color", "#FF0000")
        arrow_width = self._get_scaled_arrow_width()

        for rel_x1, rel_y1, rel_x2, rel_y2 in image_state.arrows:
            # 相對座標 → Scene 座標
            x1, y1 = self.relative_to_scene(rel_x1, rel_y1)
            x2, y2 = self.relative_to_scene(rel_x2, rel_y2)

            arrow = ArrowItem(
                QPointF(x1, y1), QPointF(x2, y2),
                arrow_color, arrow_width
            )
            self.scene.addItem(arrow)
            self.arrows.append(arrow)

    def scene_to_relative(self, x: float, y: float) -> Tuple[float, float]:
        """
        Scene 座標 → 相對座標 (0.0~1.0)
        
        修正: 基於 Image Item 座標系，而非整個 Scene
        """
        if not self.image_item:
            return (0.0, 0.0)
            
        # Scene Point -> Image Item Local Point
        local_pt = self.image_item.mapFromScene(QPointF(x, y))
        
        pixmap = self.image_item.pixmap()
        if not pixmap or pixmap.isNull():
            return (0.0, 0.0)
            
        w = pixmap.width()
        h = pixmap.height()
        
        if w == 0 or h == 0: return (0.0, 0.0)
        
        return (local_pt.x() / w, local_pt.y() / h)

    def relative_to_scene(self, rel_x: float, rel_y: float) -> Tuple[float, float]:
        """
        相對座標 (0.0~1.0) → Scene 座標
        
        修正: 基於 Image Item 座標系還原
        """
        if not self.image_item:
            return (0.0, 0.0)

        pixmap = self.image_item.pixmap()
        if not pixmap or pixmap.isNull():
            return (0.0, 0.0)

        w = pixmap.width()
        h = pixmap.height()
        
        # Relative -> Local Point
        local_x = rel_x * w
        local_y = rel_y * h
        
        # Local Point -> Scene Point
        scene_pt = self.image_item.mapToScene(QPointF(local_x, local_y))
        
        return (scene_pt.x(), scene_pt.y())

    def resizeEvent(self, event):
        """
        視窗大小改變事件

        自動調整檢視以顯示完整 Scene
        """
        super().resizeEvent(event)

        # 如果有圖片且使用者沒有手動縮放，自動適應檢視
        # 如果使用者已經手動縮放，不要重置他們的檢視
        if self.image_item and not self.user_zoomed:
            self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    # 測試畫布檢視
    app = QApplication(sys.argv)

    widget = CanvasView()

    # 測試載入圖片
    widget.load_image("tmp/test_cases/case001/img1.jpg")
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())
