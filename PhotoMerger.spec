# PhotoMerger.spec
# PyInstaller 打包規格檔
#
# 建置指令：pyinstaller PhotoMerger.spec --noconfirm
# 輸出位置：dist/PhotoMerger/PhotoMerger.exe
#
# OCR 模型策略：執行時下載（非打包內建）
# PaddleOCR 模型首次使用時自動下載到 %USERPROFILE%\.paddleocr\
# 應用程式已內建「首次載入 OCR 模型中，請稍候」的 UI 處理

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

# ── 專案根目錄（此 .spec 檔所在位置）────────────────────────────────────────
ROOT = Path(SPECPATH)

# ── 應用程式資訊 ──────────────────────────────────────────────────────────────
APP_NAME    = "PhotoMerger"
ENTRY_POINT = str(ROOT / "main.py")

# ============================================================================
# 資料檔案（打包進 _MEIPASS 的非 Python 資源）
# 透過 utils/paths.py 的 get_resource_path() 存取
# ============================================================================

datas = []

# 標楷體字型 → get_font_path() → get_resource_path("assets/fonts/kaiu.ttf")
datas += [
    (str(ROOT / "assets" / "fonts" / "kaiu.ttf"), "assets/fonts"),
]

# 預設設定檔 → 打包進 _MEIPASS/config/（唯讀參考用）
# 實際可寫入的設定位於 EXE 同層 config/ → get_config_dir() 自動建立
datas += [
    (str(ROOT / "config" / "config.json"), "config"),
]

# PyQt6 平台插件（Windows 必須，缺少會出現「no Qt platform plugin」錯誤）
datas += collect_data_files("PyQt6", includes=["Qt6/plugins/platforms/*"])
datas += collect_data_files("PyQt6", includes=["Qt6/plugins/imageformats/*"])
datas += collect_data_files("PyQt6", includes=["Qt6/plugins/styles/*"])

# Pillow 影像格式插件
datas += collect_data_files("PIL")

# PaddleOCR 設定 YAML（PaddleX 後端需要這些設定檔）
try:
    datas += collect_data_files("paddleocr", includes=["**/*.yaml"])
    datas += collect_data_files("paddleocr", includes=["**/*.yml"])
    datas += collect_data_files("paddleocr", includes=["**/*.json"])
except Exception:
    pass

# PaddlePaddle 資料檔案
try:
    datas += collect_data_files("paddle", includes=["**/*.yaml"])
    datas += collect_data_files("paddle", includes=["**/*.json"])
except Exception:
    pass

# ============================================================================
# 二進位檔案（DLL 等原生函式庫）
# ============================================================================

binaries = []

# PaddlePaddle 在 Windows 附帶大量原生 DLL（mkl、libwinpthread 等）
try:
    binaries += collect_dynamic_libs("paddle")
except Exception:
    pass

# ============================================================================
# 隱藏匯入
# PyInstaller 靜態分析無法追蹤以下情況：
# (a) 透過 try/except ImportError 條件匯入（如 ocr_worker.py）
# (b) PaddleOCR 的動態插件系統
# (c) PyQt6 執行時載入的模組
# ============================================================================

hiddenimports = []

# ── 本專案所有模組（確保打包完整）────────────────────────────────────────────
hiddenimports += [
    "core.ocr_worker",
    "core.image_enhancement",
    "core.p52.data_manager",
    "core.p52.image_processor",
    "core.p52.archive_manager",
    "core.grid4.data_manager",
    "core.grid4.image_processor",
    "core.grid4.archive_manager",
    "core.grid4.config_manager",
    "core.grid4.edit_history",
    "ui.mode_selector",
    "ui.p52.main_window",
    "ui.p52.editor_canvas",
    "ui.p52.graphics_items",
    "ui.grid4.main_window",
    "ui.grid4.canvas_view",
    "ui.grid4.control_panel",
    "ui.grid4.thumbnail_list",
    "ui.grid4.edit_toolbar",
    "ui.grid4.edit_items",
    "utils.paths",
    "utils.validators",
    "utils.date_utils",
]

# ── PyQt6 ─────────────────────────────────────────────────────────────────────
hiddenimports += [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.sip",
]

# ── Pillow 影像格式插件 ────────────────────────────────────────────────────────
hiddenimports += [
    "PIL",
    "PIL.Image",
    "PIL.ImageEnhance",
    "PIL.ImageFont",
    "PIL.ImageDraw",
    "PIL.JpegImagePlugin",
    "PIL.PngImagePlugin",
    "PIL.BmpImagePlugin",
    "PIL._imaging",
]

# ── PaddleOCR（動態插件系統，需整個子模組樹）────────────────────────────────
try:
    hiddenimports += collect_submodules("paddleocr")
except Exception:
    hiddenimports += ["paddleocr"]

# ── PaddlePaddle 核心 ─────────────────────────────────────────────────────────
try:
    hiddenimports += collect_submodules("paddle")
except Exception:
    hiddenimports += [
        "paddle",
        "paddle.nn",
        "paddle.tensor",
        "paddle.framework",
        "paddle.static",
        "paddle.inference",
    ]

# ── PaddleOCR 依賴的科學計算套件 ─────────────────────────────────────────────
hiddenimports += [
    "cv2",                              # opencv-python（PaddleOCR 內部使用）
    "numpy",
    "numpy.core._multiarray_umath",
    "shapely",
    "shapely.geometry",
    "pyclipper",
    "requests",
    "tqdm",
    "yaml",
]

# ============================================================================
# 排除不需要的套件（減少打包大小）
# ============================================================================

excludes = [
    "pytest",
    "pytest_qt",
    "_pytest",
    "sphinx",
    "docutils",
    "IPython",
    "jupyter",
    "notebook",
    "torch",
    "torchvision",
    "tensorflow",
    "matplotlib",
    "tkinter",
    "wx",
    "twisted",
    "tornado",
    "flask",
    "django",
]

# ============================================================================
# 分析階段
# ============================================================================

a = Analysis(
    [ENTRY_POINT],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# ============================================================================
# EXE 設定
# 使用資料夾模式（非單一 exe）：
# - PaddlePaddle 有大量 DLL，單一 exe 每次啟動需解壓，造成 10-30 秒延遲
# - 資料夾模式啟動瞬間完成
# - 整個 dist/PhotoMerger/ 壓成 ZIP 發布
# ============================================================================

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # 資料夾模式必須設為 True
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,                    # Windows 不可 strip，會損壞 DLL
    upx=False,                      # 關閉 UPX：防止防毒軟體誤判
    console=False,                  # GUI 應用程式，不顯示命令提示字元
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                      # 如有 .ico 檔可在此指定路徑
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[
        "*.dll",
        "Qt6Core.dll",
        "Qt6Gui.dll",
        "Qt6Widgets.dll",
        "qwindows.dll",
    ],
    name=APP_NAME,
)
