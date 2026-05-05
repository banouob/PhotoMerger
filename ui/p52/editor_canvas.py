"""
編輯畫布模組

QGraphicsView 畫布,處理:
- Scene 座標系統管理 (4096x3000)
- 框選行為
- 邊界限制
- 非同步圖像增強 (QThread Worker Pattern)
"""


from PIL import Image, ImageEnhance
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import QObject, QRectF, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QBrush, QColor, QFont, QImage, QPen, QPixmap
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QMessageBox,
)

from ui.p52.graphics_items import ResizablePixmapItem


class ImageEnhancementWorker(QObject):
    """
    圖像增強 Worker (運行在獨立執行緒)

    職責:
    - 在後台執行緒執行耗時的 PIL 圖像處理
    - 接收增強參數，返回處理後的 QImage
    - 使用 request_id 機制防止串圖

    執行緒安全要點:
    - 只使用 QImage (不使用 QPixmap)
    - QImage 必須深拷貝 (.copy())
    - PIL 圖像處理時先 copy() 原始圖像
    """

    # 信號定義
    request_processing = pyqtSignal(int, int, int, int, int, int, int)  # (brightness, contrast, saturation, sharpness, width, height, request_id)
    finished = pyqtSignal(QImage, int)  # (processed_image, request_id)

    def __init__(self, parent=None):
        """
        初始化 Worker

        Args:
            parent: 父對象
        """
        super().__init__(parent)
        self.original_pil_image = None  # 原始 PIL 圖像引用

        # 連接自己的信號到槽
        self.request_processing.connect(self.process_image)

    def set_original_image(self, pil_image: Image.Image):
        """
        設置原始圖像

        Args:
            pil_image: 原始 PIL 圖像
        """
        self.original_pil_image = pil_image

    @pyqtSlot(int, int, int, int, int, int, int)
    def process_image(self, brightness: int, contrast: int, saturation: int, sharpness: int,
                      width: int, height: int, request_id: int):
        """
        在後台執行緒執行圖像處理

        ⚠️ 關鍵點:
        1. 立即複製原始圖像引用並 copy()
        2. 使用 try-except 捕獲異常
        3. QImage 必須深拷貝
        4. 返回 request_id 用於版本檢查

        Args:
            brightness: 亮度調整 (-100 到 100)
            contrast: 對比度調整 (-100 到 100)
            saturation: 飽和度調整 (-100 到 100)
            sharpness: 銳利度調整 (-100 到 100)
            width: 目標寬度
            height: 目標高度
            request_id: 請求 ID（防止串圖）
        """
        # ⚠️ 關鍵邏輯: 立即複製引用，防止處理過程中引用發生變化
        if not self.original_pil_image:
            return

        try:
            # ⚠️ 立即 copy，確保執行緒安全
            img = self.original_pil_image.copy()

            # 轉換滑桿值到增強因子
            # 公式: factor = 1.0 + (slider_value / 100.0)
            brightness_factor = 1.0 + (brightness / 100.0)
            contrast_factor = 1.0 + (contrast / 100.0)
            saturation_factor = 1.0 + (saturation / 100.0)
            sharpness_factor = 1.0 + (sharpness / 100.0)

            # 按順序應用增強: 亮度 → 對比度 → 飽和度 → 銳利度
            if brightness != 0:
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(brightness_factor)

            if contrast != 0:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(contrast_factor)

            if saturation != 0:
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(saturation_factor)

            if sharpness != 0:
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(sharpness_factor)

            # 調整大小到場景尺寸
            img_resized = img.resize((width, height), Image.Resampling.LANCZOS)

            # 轉換 PIL 圖像到 QImage
            # 確保是 RGB 模式
            if img_resized.mode != 'RGB':
                img_resized = img_resized.convert('RGB')

            # 使用 ImageQt 轉換
            qimage = ImageQt(img_resized)

            # ⚠️ 關鍵: QImage 深拷貝，防止底層數據被 GC 回收導致崩潰
            qimage_copy = qimage.copy()

            # 發送處理完成信號，帶上 request_id
            self.finished.emit(qimage_copy, request_id)

        except Exception as e:
            # ⚠️ 異常處理: 捕獲所有異常，防止執行緒崩潰
            print(f"圖像處理異常 (request_id={request_id}): {e}")
            # 不發送 finished 信號，避免傳遞無效數據


class EditorCanvas(QGraphicsView):
    """
    編輯畫布

    使用 QGraphicsView + QGraphicsScene 實現高性能圖像編輯

    特性:
    - Scene 座標系統: 4096x3000 (確保精度)
    - 框選創建子图 (畫布上永遠只有一個子图)
    - 自動刪除舊子图
    - 邊界限制
    - 非同步圖像增強 (QThread Worker Pattern)
    """

    # Scene 尺寸 (與目標照片尺寸一致)
    SCENE_WIDTH = 4096
    SCENE_HEIGHT = 3000

    # 子图標準尺寸
    SUBIMAGE_WIDTH = 1026
    SUBIMAGE_HEIGHT = 1000

    def __init__(self, parent=None):
        """
        初始化編輯畫布

        Args:
            parent: 父部件
        """
        super().__init__(parent)

        # 創建 Scene
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, self.SCENE_WIDTH, self.SCENE_HEIGHT)
        self.setScene(self.scene)

        # 設置視圖屬性
        self.setRenderHint(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # 框選狀態
        self.is_selecting = False
        self.selection_start = None  # QPointF in scene coordinates
        self.selection_rect_item = None  # 臨時選擇框

        # 當前顯示的照片
        self.current_photo_item = None  # QGraphicsPixmapItem

        # 當前的子图
        self.current_subimage = None  # ResizablePixmapItem

        # 縮放狀態追蹤
        self.has_manually_zoomed = False  # 追蹤用戶是否手動縮放過

        # 縮放限制
        self.min_zoom_factor = 1.0  # 將在照片加載時計算
        self.max_zoom_factor = 5.0  # 500% 最大縮放
        self.current_zoom_factor = 1.0

        # 平移狀態
        self.is_panning = False
        self.pan_start_pos = None

        # 圖像增強
        self.original_pil_image = None  # 原始PIL圖像用於增強基準

        # 警員資訊預覽
        self._officer_text = ""
        self.officer_preview_item = None

        # ============ 新增: 圖像增強執行緒 (QThread Worker Pattern) ============

        # Request ID 機制（防止串圖）
        # ⚠️ 關鍵: 用於防止舊的處理結果覆蓋新的請求
        self.current_request_id = 0  # 當前請求的 ID

        # 創建 Worker 和執行緒
        self.enhancement_worker = ImageEnhancementWorker()
        self.enhancement_thread = QThread()

        # 將 Worker 移動到執行緒
        self.enhancement_worker.moveToThread(self.enhancement_thread)

        # 連接信號
        self.enhancement_worker.finished.connect(self._on_enhancement_finished)

        # 啟動執行緒
        self.enhancement_thread.start()

    def resizeEvent(self, event):
        """
        處理視口調整大小事件

        只在用戶未手動縮放時自動適配視圖
        """
        super().resizeEvent(event)

        # 只在用戶未手動縮放且有照片時自動適配
        if not self.has_manually_zoomed and self.current_photo_item:
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event):
        """
        處理滑鼠滾輪事件

        Ctrl + 滾輪: 縮放畫布
        """
        # 只在按住 Ctrl 鍵時縮放
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # 計算縮放因子
            delta = event.angleDelta().y()
            zoom_factor = 1.1 if delta > 0 else 0.9

            # 計算新縮放級別
            new_zoom = self.current_zoom_factor * zoom_factor

            # 應用縮放限制
            if new_zoom < self.min_zoom_factor:
                new_zoom = self.min_zoom_factor
            elif new_zoom > self.max_zoom_factor:
                new_zoom = self.max_zoom_factor
            else:
                # 應用縮放
                self.scale(zoom_factor, zoom_factor)
                self.current_zoom_factor = new_zoom
                self.has_manually_zoomed = True  # 標記為手動縮放

            event.accept()
        else:
            super().wheelEvent(event)

    def load_photo(self, photo_path: str):
        """
        加載照片到畫布

        ⚠️ 關鍵邏輯 2: 切換照片時遞增 request_id，使舊照片的所有掛起請求失效

        Args:
            photo_path: 照片路徑
        """
        # 清空 scene
        self.scene.clear()
        self.current_photo_item = None
        self.current_subimage = None
        self.officer_preview_item = None  # scene.clear() 已移除，重置參考

        # 加載照片
        pixmap = QPixmap(photo_path)
        if pixmap.isNull():
            return

        # ✅ 存儲原始PIL圖像用於圖像增強
        self.original_pil_image = Image.open(photo_path)

        # ⚠️ 關鍵邏輯 2: 切換照片時遞增 request_id，使舊照片的請求失效
        self.current_request_id += 1

        # ✅ 更新 Worker 的原始圖像
        self.enhancement_worker.set_original_image(self.original_pil_image)

        # 縮放到 Scene 尺寸
        scaled_pixmap = pixmap.scaled(
            self.SCENE_WIDTH,
            self.SCENE_HEIGHT,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 添加到 scene
        self.current_photo_item = self.scene.addPixmap(scaled_pixmap)
        self.current_photo_item.setPos(0, 0)

        # 重置縮放狀態(加載新照片時)
        self.has_manually_zoomed = False

        # 適應視圖
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        # 重新套用警員預覽文字（scene.clear() 已清除，需重建）
        self._apply_officer_preview()

        # 計算最小縮放級別(當前 fit-to-view 的縮放級別)
        # ✅ 關鍵: 獲取 fitInView 後的實際縮放值
        current_scale = self.transform().m11()
        self.min_zoom_factor = current_scale
        # ✅ 同步當前縮放因子到實際值
        self.current_zoom_factor = current_scale

    def mousePressEvent(self, event):
        """
        滑鼠按下事件

        左鍵: 開始框選
        右鍵: 開始平移

        Args:
            event: 滑鼠事件
        """
        if event.button() == Qt.MouseButton.RightButton:
            # 開始平移
            self.is_panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # 轉換到 Scene 座標
            scene_pos = self.mapToScene(event.pos())

            # 檢查是否點擊了現有子圖
            item = self.scene.itemAt(scene_pos, self.transform())
            if isinstance(item, ResizablePixmapItem):
                # 點擊了子圖,繼續傳遞事件
                super().mousePressEvent(event)
                return

            # 開始框選
            self.is_selecting = True
            self.selection_start = scene_pos

            # 創建臨時選擇框
            # ✅ 使用 cosmetic pen 保持縮放時線寬不變
            pen = QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)  # 保持 2px 寬度,不受縮放影響
            self.selection_rect_item = self.scene.addRect(
                QRectF(scene_pos, scene_pos), pen
            )

            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        滑鼠移動事件

        更新框選矩形或處理平移

        Args:
            event: 滑鼠事件
        """
        if self.is_panning:
            # 處理平移
            delta = event.pos() - self.pan_start_pos
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            self.pan_start_pos = event.pos()
            event.accept()
            return

        if self.is_selecting and self.selection_rect_item:
            # 轉換到 Scene 座標
            scene_pos = self.mapToScene(event.pos())

            # 更新選擇框
            rect = QRectF(self.selection_start, scene_pos).normalized()
            self.selection_rect_item.setRect(rect)

            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        滑鼠釋放事件

        完成框選或平移

        Args:
            event: 滑鼠事件
        """
        if event.button() == Qt.MouseButton.RightButton and self.is_panning:
            # 結束平移
            self.is_panning = False
            self.unsetCursor()
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            # 結束框選
            self.is_selecting = False

            if self.selection_rect_item:
                rect = self.selection_rect_item.rect()
                self.scene.removeItem(self.selection_rect_item)
                self.selection_rect_item = None

                # 如果矩形足夠大,創建子图
                if rect.width() > 10 and rect.height() > 10:
                    self._create_subimage(rect)

            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _create_subimage(self, rect: QRectF):
        """
        創建子图 (從框選區域)

        工作流程:
        1. 裁剪框選區域
        2. 等比縮放至寬度 1000px
        3. 驗證高度不超過 80% 畫布高度 (2400px)
        4. 創建 ResizablePixmapItem
        5. 記錄原始裁切區域 (source_roi)

        Args:
            rect: 框選矩形 (Scene 座標)
        """
        if not self.current_photo_item:
            return

        # 刪除舊子图
        if self.current_subimage:
            self.scene.removeItem(self.current_subimage)
            self.current_subimage = None

        # 1. 從原始照片裁剪區域
        pixmap = self.current_photo_item.pixmap()
        cropped = pixmap.copy(rect.toRect())

        # 2. 等比縮放至寬度 1000px (保持長寬比)
        scaled_cropped = cropped.scaledToWidth(
            1000,
            Qt.TransformationMode.SmoothTransformation
        )

        # 3. 驗證高度限制 (不超過畫布高度的 80%)
        MAX_HEIGHT = int(self.SCENE_HEIGHT * 0.8)  # 2400px
        if scaled_cropped.height() > MAX_HEIGHT:
            # 彈出警告對話框
            QMessageBox.warning(
                self,
                "選取範圍錯誤",
                f"選取範圍過於細長(高度 {scaled_cropped.height()}px 超過限制 {MAX_HEIGHT}px),請重新選取。",
                QMessageBox.StandardButton.Ok
            )
            return  # 取消創建子图

        # 4. 創建可縮放的子图元件
        self.current_subimage = ResizablePixmapItem(scaled_cropped)
        self.current_subimage.setPos(rect.topLeft())
        self.current_subimage.set_scene_bounds(self.sceneRect())

        # 5. 記錄原始裁切區域 (source_roi)
        self.current_subimage.set_source_roi(rect)

        self.scene.addItem(self.current_subimage)

    def get_current_roi(self) -> tuple | None:
        """
        獲取當前 ROI (Region of Interest)

        注意: 此方法僅返回當前位置，不包含源座標。
        建議使用 get_subimage_info() 獲取完整信息。

        Returns:
            (x, y, width, height) 如果存在子图,否則 None
            座標基於 Scene 座標系 (4096x3000)
        """
        if self.current_subimage:
            rect = self.current_subimage.sceneBoundingRect()
            return (rect.x(), rect.y(), rect.width(), rect.height())
        return None

    def get_subimage_info(self) -> dict | None:
        """
        獲取子图的完整信息

        Returns:
            包含以下鍵的字典，如果沒有子图則返回 None:
            - source_roi: (x, y, w, h) - 原始裁切區域 (Scene 座標)
            - final_geometry: (x, y, w, h) - 最終子图位置和尺寸 (Scene 座標)
            - source_roi_rect: QRectF - 原始裁切矩形
        """
        if not self.current_subimage:
            return None

        source_roi = self.current_subimage.source_roi
        if not source_roi:
            return None

        final_geo = self.current_subimage.get_final_geometry()

        return {
            "source_roi": (
                source_roi.x(),
                source_roi.y(),
                source_roi.width(),
                source_roi.height(),
            ),
            "final_geometry": final_geo,
            "source_roi_rect": source_roi,
        }

    def get_subimage_pil(self) -> Image.Image | None:
        """
        取得當前子圖的原始裁切 PIL Image（用於 OCR）

        將 Scene 座標 (4096x3000) 映射回原始圖片像素座標後裁切。

        Returns:
            裁切後的 PIL Image，若無子圖則回傳 None
        """
        if not self.current_subimage or not self.original_pil_image:
            return None

        source_roi = self.current_subimage.source_roi
        if not source_roi:
            return None

        # Scene 座標 → 原始圖片像素座標
        orig_w, orig_h = self.original_pil_image.size
        scale_x = orig_w / self.SCENE_WIDTH
        scale_y = orig_h / self.SCENE_HEIGHT

        sx = int(source_roi.x() * scale_x)
        sy = int(source_roi.y() * scale_y)
        sw = int(source_roi.width() * scale_x)
        sh = int(source_roi.height() * scale_y)

        # 邊界檢查
        sx = max(0, sx)
        sy = max(0, sy)
        if sx + sw > orig_w:
            sw = orig_w - sx
        if sy + sh > orig_h:
            sh = orig_h - sy
        if sw <= 0 or sh <= 0:
            return None

        return self.original_pil_image.crop((sx, sy, sx + sw, sy + sh))

    def clear(self):
        """
        清空畫布
        """
        self.scene.clear()
        self.current_photo_item = None
        self.current_subimage = None
        self.officer_preview_item = None
        self.is_selecting = False
        self.selection_rect_item = None

    def set_officer_preview(self, text: str):
        """設定警員資訊預覽文字，即時更新畫布右上角顯示"""
        self._officer_text = text
        self._apply_officer_preview()

    def _apply_officer_preview(self):
        """在 Scene 右上角繪製警員文字預覽（黃色粗體標楷體）"""
        if self.officer_preview_item:
            self.scene.removeItem(self.officer_preview_item)
            self.officer_preview_item = None

        if not self._officer_text or not self.current_photo_item:
            return

        item = QGraphicsSimpleTextItem(self._officer_text)

        font_size = max(10, int(self.SCENE_WIDTH * 0.015))
        font = QFont("標楷體", font_size, QFont.Weight.Bold)
        item.setFont(font)
        item.setBrush(QBrush(QColor("#FFFF00")))
        item.setZValue(20)

        self.scene.addItem(item)
        bw = item.boundingRect().width()
        margin = int(self.SCENE_WIDTH * 0.01)
        item.setPos(self.SCENE_WIDTH - bw - margin, margin)

        self.officer_preview_item = item

    def apply_enhancements(self, brightness: int, contrast: int, saturation: int, sharpness: int):
        """
        應用圖像增強到背景照片並更新子图 (非同步)

        ⚠️ 關鍵邏輯 1: 每次調用時遞增 request_id，防止串圖

        Args:
            brightness: -100 到 100
            contrast: -100 到 100
            saturation: -100 到 100
            sharpness: -100 到 100
        """
        if not self.original_pil_image:
            return

        # ⚠️ 關鍵邏輯 1: 遞增 request ID
        self.current_request_id += 1

        # 發送處理請求到 Worker 執行緒 (通過信號)
        # 不阻塞主執行緒，立即返回
        self.enhancement_worker.request_processing.emit(
            brightness,
            contrast,
            saturation,
            sharpness,
            self.SCENE_WIDTH,
            self.SCENE_HEIGHT,
            self.current_request_id
        )

    @pyqtSlot(QImage, int)
    def _on_enhancement_finished(self, qimage: QImage, request_id: int):
        """
        接收 Worker 處理完成的結果

        ⚠️ 關鍵邏輯 3: 檢查 request_id 防止串圖

        Args:
            qimage: 處理後的 QImage
            request_id: 請求 ID
        """
        # ⚠️ 關鍵邏輯 3: 檢查是否是最新的請求
        if request_id != self.current_request_id:
            # 過期結果，丟棄
            return

        # 轉換 QImage → QPixmap (主執行緒)
        enhanced_pixmap = QPixmap.fromImage(qimage)

        # 更新背景照片 (不調用fitInView - 保持當前縮放/平移)
        if self.current_photo_item:
            self.current_photo_item.setPixmap(enhanced_pixmap)

        # 更新子图(如果存在)
        if self.current_subimage and self.current_subimage.source_roi:
            self._update_subimage_from_enhanced(enhanced_pixmap)

    def _update_subimage_from_enhanced(self, enhanced_pixmap: QPixmap):
        """
        從增強後的背景重新裁剪子图

        Args:
            enhanced_pixmap: 增強後的背景圖像 (4096x3000)
        """
        if not self.current_subimage or not self.current_subimage.source_roi:
            return

        # 獲取原始裁剪區域
        source_roi = self.current_subimage.source_roi

        # 從增強後的圖像裁剪
        cropped = enhanced_pixmap.copy(source_roi.toRect())

        # 縮放到寬度1000 (保持長寬比)
        scaled_cropped = cropped.scaledToWidth(
            1000,
            Qt.TransformationMode.SmoothTransformation
        )

        # 更新子图pixmap
        self.current_subimage.setPixmap(scaled_cropped)

    def cleanup(self):
        """
        顯式清理執行緒（Robust Cleanup）

        可以在以下時機調用：
        - 視窗關閉時 (closeEvent)
        - 對象析構時 (__del__)
        - 手動清理資源時
        """
        if hasattr(self, 'enhancement_thread') and self.enhancement_thread.isRunning():
            # 清理 Worker
            if hasattr(self, 'enhancement_worker'):
                self.enhancement_worker.deleteLater()

            # 停止執行緒
            self.enhancement_thread.quit()
            if not self.enhancement_thread.wait(2000):  # 等待最多 2 秒
                # 如果等待超時，強制終止（不推薦，但作為最後手段）
                self.enhancement_thread.terminate()
                self.enhancement_thread.wait()

    def __del__(self):
        """
        析構時調用 cleanup 作為保險
        """
        self.cleanup()
