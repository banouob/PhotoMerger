# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 溝通語言

與使用者的所有溝通一律使用**繁體中文**，包含說明、問題、建議與錯誤訊息。

## 專案簡介

PhotoMerger 將兩個工具統一為單一應用程式，以模式切換方式支援：P52（警52雙圖合併）與 4Grid（批次四格拼圖合成）。UI 框架為 PyQt6；影像處理使用 Pillow；OCR（PaddleOCR）為可選功能，依需求安裝。

## 常用指令

```bash
python main.py                       # 啟動應用程式（顯示模式選擇器）
pytest tests/                        # 執行所有測試
pytest tests/test_validators.py      # 執行單一測試檔
pip install -r requirements.txt
pip install -r requirements-ocr.txt  # 可選：安裝 PaddleOCR 支援
```

## 架構

```
core/
  image_enhancement.py      # 共用：apply_enhancements() + QThread worker
  ocr_worker.py             # 共用：OcrWorker + OcrManager（非同步、signal 驅動）
  p52/                      # P52 專用：DataManager、ImageProcessor、ArchiveManager
  grid4/                    # 4Grid 專用：DataManager、ImageProcessor、ArchiveManager、
                            #   ConfigManager、EditHistory
ui/
  mode_selector.py          # 啟動模式選擇對話框
  p52/                      # P52 UI：MainWindow、EditorCanvas、GraphicsItems
  grid4/                    # 4Grid UI：MainWindow、CanvasView、ControlPanel、
                            #   ThumbnailList、EditToolbar、EditItems
utils/
  validators.py             # 檔名清洗 + ROC/AD 日期格式驗證
  date_utils.py             # ROC ↔ AD 日期轉換
  paths.py                  # 字型路徑解析
config/config.json           # 共用執行期設定（p52_officers 警員名單、4Grid 承辦人/地點/尺寸/輸出品質）
```

### 匯入慣例
- 共用層：`from core.image_enhancement import ...` / `from utils.validators import ...`
- P52 專用：`from core.p52.image_processor import ...`
- 4Grid 專用：`from core.grid4.data_manager import ...`

### 4Grid 資料模型
掃描根目錄下每個子資料夾為一個 `CaseData`（固定 3 張圖片）。圖片依 EXIF DateTime 排序，若無 EXIF 則退回檔名排序。每張圖片對應一個 `ImageState`（箭頭、子圖疊加、亮度／對比度／飽和度／銳化）。`EditHistory` 為每個案件維護 `EditSnapshot` 堆疊以支援撤銷／重做。

### 4Grid 渲染流程
**禁止使用 `canvas.grab()` 或 `QWidget.grab()`。** 輸出影像一律由 `core/grid4/image_processor.py` 建立：
1. 從磁碟讀取原始檔案
2. 套用 `ImageState`（繪製箭頭、貼上子圖疊加、執行 `apply_enhancements()`）
3. 縮放至儲存格尺寸（1200×800）
4. 將三個儲存格 + 資訊卡合成至 2400×1600 畫布 → 儲存為 JPG

拖曳重排圖片時，`image_paths` 與 `image_states` 兩個列表必須同步交換，不可只改其中一個。

### OCR 使用模式
`OcrManager` 持有一個移至 `QThread` 的 `OcrWorker`。從主執行緒呼叫 `ocr_manager.request_ocr(pil_image)`；連接 `ocr_manager.finished` / `ocr_manager.error` signal 取得結果。PaddleOCR 模型在第一次請求時才延遲載入。顯示 OCR UI 前請先以 `is_ocr_available()` 確認是否已安裝。

### P52 座標系統
- 每側場景尺寸：4096×3000；輸出：8192×3000 JPG（左側 = 警52照片，右側 = 目標照片）
- ROC 日期格式：YYYMMDD（7 位數）；封存路徑依日期 + 速度類別組織

### P52 警員文字疊加
- 警員名單由 `config/config.json` 的 `p52_officers` 陣列定義（格式："姓名編號"）
- 輸出時透過 `ImageProcessor` 將選定警員文字疊加至左側照片
- 字體大小在預覽（EditorCanvas）與輸出（ImageProcessor）中需保持一致

## 重要限制

- 新檔案必須放入對應模組（`core/`、`ui/`、`utils/`），禁止放置於根目錄
- 擴充現有檔案，禁止建立 `*_v2.py` / `enhanced_*.py` 等重複實作
- `config/config.json` 是 P52 與 4Grid 共用設定的唯一來源，不得將這些值寫死於程式碼
- 4Grid 所有座標使用正規化範圍（0.0–1.0），僅在渲染時才轉換為像素座標
- 每完成一個任務後提交；推送至 `origin main` 以維持 GitHub 備份
