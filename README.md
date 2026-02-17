# PhotoMerger

**PhotoMerger** 是一個統一的照片合併工具，以模式切換方式支援兩種工作流程：

- **警52模式 (P52)**：警52照片 + 目標照片 -> 雙圖並排合併（8192x3000 JPG）
- **四格模式 (4Grid)**：3張違規照片 + 資訊卡 -> 四格拼圖（2400x1600 JPG）

## Quick Start

```bash
# 安裝核心依賴
pip install -r requirements.txt

# 啟動應用程式
python main.py

# （可選）安裝 OCR 車牌辨識功能
pip install -r requirements-ocr.txt
```

## Project Structure

```
PhotoMerger/
├── main.py                    # 統一入口 + 模式選擇
├── core/                      # 核心邏輯層
│   ├── image_enhancement.py   # [共用] 影像增強
│   ├── ocr_worker.py          # [共用] OCR Worker
│   ├── p52/                   # 警52模式專用
│   └── grid4/                 # 四格模式專用
├── ui/                        # 界面層
│   ├── mode_selector.py       # 模式選擇介面
│   ├── shared/                # 共用 UI 元件
│   ├── p52/                   # 警52模式 UI
│   └── grid4/                 # 四格模式 UI
├── utils/                     # 共用工具層
│   ├── validators.py          # 檔名驗證 + 日期驗證
│   ├── date_utils.py          # 民國日期工具
│   └── paths.py               # 路徑管理
├── config/                    # 外部設定
├── assets/fonts/              # 字型資源
└── tests/                     # 測試
```

## Development Guidelines

- **CLAUDE.md** 包含開發規範，開發前請先閱讀
- 所有程式碼放在 `core/`、`ui/`、`utils/` 下，不在根目錄建立 .py 檔案（main.py 除外）
- 共用邏輯放在共用層，模式專用邏輯放在各自的子目錄
- OCR 功能為按需安裝，不影響核心功能
