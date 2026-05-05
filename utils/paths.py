"""
路徑管理模組

處理開發環境與打包環境的路徑差異
提供 Config (外部) 和 Assets (內部) 的統一訪問介面
"""

import sys
from pathlib import Path


def is_frozen() -> bool:
    """
    判斷是否為 PyInstaller 打包環境

    Returns:
        True 如果是打包後的 EXE, False 如果是開發環境
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_executable_dir() -> Path:
    """
    獲取可執行檔案所在目錄

    - 打包環境: EXE 檔案所在目錄
    - 開發環境: main.py 所在目錄

    Returns:
        可執行檔案目錄的 Path 物件
    """
    if is_frozen():
        # PyInstaller 打包環境: sys.executable 指向 EXE
        return Path(sys.executable).parent
    else:
        # 開發環境: 使用專案根目錄
        # 假設 paths.py 在 utils/ 目錄下
        return Path(__file__).parent.parent


def get_config_dir() -> Path:
    """
    獲取 Config 目錄路徑 (必須在 EXE 同層)

    目錄結構:
    - 打包環境: PhotoMerger_4Grid.exe 同層 /config/
    - 開發環境: main.py 同層 /config/

    Returns:
        Config 目錄的 Path 物件

    Note:
        此函式會自動建立 config 目錄（如果不存在）
    """
    config_dir = get_executable_dir() / "config"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def get_resource_path(relative_path: str) -> Path:
    """
    獲取資原始檔的絕對路徑 (支援開發/打包環境)

    - 打包環境: 從 sys._MEIPASS 讀取 (PyInstaller 臨時目錄)
    - 開發環境: 從專案根目錄讀取

    Args:
        relative_path: 相對於專案根目錄的路徑
                      例如: "assets/fonts/kaiu.ttf"

    Returns:
        資原始檔的絕對 Path 物件

    Raises:
        FileNotFoundError: 如果資原始檔不存在

    Examples:
        >>> font_path = get_resource_path("assets/fonts/kaiu.ttf")
        >>> icon_path = get_resource_path("assets/icons/app.ico")
    """
    if is_frozen():
        # PyInstaller 打包環境: 從臨時解壓目錄讀取
        base_path = Path(sys._MEIPASS)
    else:
        # 開發環境: 從專案根目錄讀取
        base_path = get_executable_dir()

    resource_path = base_path / relative_path

    # 驗證資原始檔是否存在
    if not resource_path.exists():
        raise FileNotFoundError(
            f"Resource file not found: {resource_path}\n"
            f"Relative path: {relative_path}\n"
            f"Base path: {base_path}\n"
            f"Environment: {'Packaged' if is_frozen() else 'Development'}"
        )

    return resource_path


def get_font_path() -> Path:
    """
    獲取標楷體字型檔案路徑 (快捷方法)

    Returns:
        kaiu.ttf 的絕對 Path 物件

    Raises:
        FileNotFoundError: 如果字型檔案不存在
    """
    return get_resource_path("assets/fonts/kaiu.ttf")


def ensure_directory(path: Path) -> Path:
    """
    確保目錄存在,不存在則建立

    Args:
        path: 目錄路徑

    Returns:
        建立/確認後的目錄 Path 物件
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


# === 除錯/診斷工具 ===

def print_path_diagnostics():
    """
    列印路徑診斷資訊 (用於除錯)

    輸出內容:
    - 執行環境 (開發/打包)
    - 可執行檔案目錄
    - Config 目錄
    - 資原始檔目錄
    """
    # 設定 UTF-8 編碼輸出（Windows 相容）
    import io
    import sys
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=== Path Diagnostics ===")
    print(f"Environment: {'Packaged' if is_frozen() else 'Development'}")
    print(f"Executable Dir: {get_executable_dir()}")
    print(f"Config Dir: {get_config_dir()}")

    if is_frozen():
        print(f"PyInstaller Temp Dir: {sys._MEIPASS}")
    else:
        print(f"Project Root Dir: {get_executable_dir()}")

    # Test font path
    try:
        font_path = get_font_path()
        print(f"Font File Path: {font_path}")
        print(f"Font File Exists: {font_path.exists()}")
    except FileNotFoundError as e:
        print(f"Font File Error: {e}")

    print("=" * 40)


if __name__ == "__main__":
    # 直接執行此模組時輸出診斷資訊
    print_path_diagnostics()
