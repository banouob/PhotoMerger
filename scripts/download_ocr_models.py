"""
scripts/download_ocr_models.py

預先下載 PaddleOCR 中文語言模型到本機快取目錄。

用途：在無網路的部署環境中，可先在有網路的機器執行此腳本，
      將模型快取目錄複製到目標機器的相同路徑。

模型快取位置：
  Windows: %USERPROFILE%\.paddleocr\
  Linux/macOS: ~/.paddleocr/

使用方式：
  python scripts/download_ocr_models.py

注意：此腳本使用與 core/ocr_worker.py 中 OcrWorker._init_ocr_engine()
     完全相同的參數初始化 PaddleOCR，確保模型版本一致。
"""

import os
import sys


def download_models():
    print("=" * 50)
    print("PhotoMerger OCR 模型預下載工具")
    print("=" * 50)

    # 設定與 OcrWorker._init_ocr_engine() 相同的環境變數
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    os.environ["FLAGS_use_mkldnn"] = "0"

    print("\n正在匯入 PaddleOCR...")
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        print("\n[錯誤] PaddleOCR 未安裝")
        print("請執行：pip install -r requirements-ocr.txt")
        sys.exit(1)

    print("正在初始化 PaddleOCR（lang='ch'）...")
    print("首次執行將下載約 100-200MB 的模型檔案，請稍候...\n")

    try:
        # 使用與 OcrWorker._init_ocr_engine() 完全相同的參數
        _ocr = PaddleOCR(
            use_angle_cls=True,
            lang="ch",
            enable_mkldnn=False,
        )
        print("\n[成功] 模型下載並快取完成")

        # 顯示快取目錄資訊
        home = os.path.expanduser("~")
        cache_dir = os.path.join(home, ".paddleocr")
        if os.path.exists(cache_dir):
            total_size = sum(
                os.path.getsize(os.path.join(dp, f))
                for dp, _, files in os.walk(cache_dir)
                for f in files
            )
            print(f"快取位置：{cache_dir}")
            print(f"快取大小：{total_size / 1024 / 1024:.1f} MB")
        else:
            print(f"快取目錄：{cache_dir}（不存在，可能已使用自訂路徑）")

    except Exception as e:
        print(f"\n[錯誤] 模型下載失敗：{e}")
        sys.exit(1)

    print("\n完成！後續在無網路環境使用 OCR 功能時將直接使用此快取。")
    print("=" * 50)


if __name__ == "__main__":
    download_models()
