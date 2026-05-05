"""
PhotoMerger - 統一入口

支援兩種工作模式:
1. P52 模式 (雙照片合併)
2. 4Grid 模式 (四格拼圖)
"""

import io
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

# 確保 UTF-8 輸出（Windows 相容）
if sys.stdout and sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def launch_p52_mode(app: QApplication):
    """
    啟動 P52 模式

    流程:
    1. 輸入民國日期
    2. 選擇警52照片
    3. 選擇目標照片
    4. 啟動主視窗
    """
    from core.p52.data_manager import DataManager
    from core.p52.image_processor import ImageProcessor
    from ui.p52.main_window import MainWindow
    from utils.date_utils import roc_to_ad
    from utils.validators import validate_date_format

    # 1. 輸入民國日期
    date_str, ok = QInputDialog.getText(
        None,
        "輸入日期",
        "請輸入民國日期 (7位數字, 格式: YYYMMDD):\n例如: 1140217",
    )

    if not ok or not date_str:
        print("使用者取消輸入")
        return

    if not validate_date_format(date_str.strip()):
        QMessageBox.warning(
            None,
            "日期格式錯誤",
            f"'{date_str}' 不是有效的民國日期格式\n請輸入7位數字 (YYYMMDD)",
        )
        return

    roc_date = date_str.strip()
    ad_date = roc_to_ad(roc_date)

    # 2. 選擇警52照片
    police_photo, _ = QFileDialog.getOpenFileName(
        None,
        "選擇警52照片",
        str(Path.home() / "Desktop"),
        "圖片檔案 (*.jpg *.jpeg *.png *.bmp)",
    )

    if not police_photo:
        print("使用者取消選擇警52照片")
        return

    # 3. 選擇目標照片（多選）
    target_photos, _ = QFileDialog.getOpenFileNames(
        None,
        "選擇目標照片（可多選）",
        str(Path(police_photo).parent),
        "圖片檔案 (*.jpg *.jpeg *.png *.bmp)",
    )

    if not target_photos:
        print("使用者取消選擇目標照片")
        return

    # 4. 初始化元件
    data_manager = DataManager(police_photo, target_photos, roc_date, ad_date)
    image_processor = ImageProcessor(police_photo)

    # 5. 啟動主視窗
    window = MainWindow(data_manager, image_processor)
    window.show()

    sys.exit(app.exec())


def launch_4grid_mode(app: QApplication):
    """
    啟動 4Grid 模式

    直接顯示主視窗，使用者透過視窗內掃描資料夾
    """
    from ui.grid4.main_window import MainWindow

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def main():
    """主程式入口"""
    # 建立應用
    app = QApplication(sys.argv)

    # 設定應用資訊
    app.setApplicationName("PhotoMerger")
    app.setOrganizationName("PhotoMerger")
    app.setApplicationVersion("2.0.0")

    # 顯示模式選擇器
    from ui.mode_selector import ModeSelector

    selector = ModeSelector()
    result = selector.exec()

    if result != ModeSelector.DialogCode.Accepted:
        print("使用者取消選擇")
        sys.exit(0)

    mode = selector.get_selected_mode()

    if mode == ModeSelector.MODE_P52:
        launch_p52_mode(app)
    elif mode == ModeSelector.MODE_4GRID:
        launch_4grid_mode(app)
    else:
        print(f"未知模式: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
