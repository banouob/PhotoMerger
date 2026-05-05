---
name: build-exe
description: 使用 PyInstaller 建置 Windows 獨立執行檔。當使用者要求建置 EXE、打包、或驗證建置時使用。
---

## 建置 Windows 執行檔

執行 PyInstaller 打包，對應 `.github/workflows/build.yml` 的 CI 流程。

### 步驟

1. 確認 PyInstaller 已安裝：`pip show pyinstaller`，若無則 `pip install pyinstaller>=6.0.0 pyinstaller-hooks-contrib`
2. 執行建置：`pyinstaller PhotoMerger.spec --noconfirm`
3. 驗證結果：確認 `dist\PhotoMerger\PhotoMerger.exe` 存在並回報檔案大小

### 注意

- 建置時間約 3-8 分鐘，請耐心等候
- 若含 PaddleOCR，輸出資料夾約 1-2 GB
- 首次 OCR 使用時需網路連線下載模型（約 100-200MB），模型快取於 `%USERPROFILE%\.paddleocr\`
