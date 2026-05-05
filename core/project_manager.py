"""
專案檔讀寫模組

負責將 P52 / 4Grid 工作狀態序列化為 JSON 並從 JSON 恢復。
專案檔存放於照片所在資料夾。
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_VERSION = "1.0"


def _serialize_image_state(state) -> dict:
    """將 ImageState 序列化為純 dict（處理 tuple 轉 list）"""
    return {
        "arrows": state.arrows,
        "sub_image": state.sub_image,
        "brightness": state.brightness,
        "contrast": state.contrast,
        "saturation": state.saturation,
        "sharpness": state.sharpness,
    }


def _serialize_case(case) -> dict:
    """將 CaseData 序列化為純 dict"""
    return {
        "folder_path": case.folder_path,
        "image_paths": list(case.image_paths),
        "image_states": [_serialize_image_state(s) for s in case.image_states],
        "meta_data": dict(case.meta_data),
        "status": case.status.value,
    }


def save_p52_project(data_manager, officer: str, filepath: str) -> str:
    """
    儲存 P52 專案進度

    Args:
        data_manager: P52 DataManager 實例
        officer: 當前選擇的警員字串
        filepath: 輸出的 JSON 路徑

    Returns:
        實際寫入的檔案路徑
    """
    data = {
        "mode": "p52",
        "version": PROJECT_VERSION,
        "police_photo_path": data_manager.police_photo_path,
        "target_photo_paths": list(data_manager.target_photo_paths),
        "roc_date_str": data_manager.roc_date_str,
        "ad_date_str": data_manager.ad_date_str,
        "current_index": data_manager.current_index,
        "processing_status": dict(data_manager.processing_status),
        "output_history": dict(data_manager.output_history),
        "enhancement_params": dict(data_manager.enhancement_params),
        "selected_officer": officer,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"P52 project saved: {filepath}")
    return filepath


def save_4grid_project(data_manager, scan_root: str, filepath: str) -> str:
    """
    儲存 4Grid 專案進度

    Args:
        data_manager: 4Grid DataManager 實例
        scan_root: 掃描根目錄路徑
        filepath: 輸出的 JSON 路徑

    Returns:
        實際寫入的檔案路徑
    """
    cases_data = []
    for case in data_manager.cases:
        cases_data.append(_serialize_case(case))

    data = {
        "mode": "4grid",
        "version": PROJECT_VERSION,
        "scan_root": scan_root,
        "current_case_index": data_manager.current_case_index,
        "cases": cases_data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"4Grid project saved: {filepath}")
    return filepath


def load_project(filepath: str) -> dict:
    """
    讀取專案檔

    Args:
        filepath: JSON 檔案路徑

    Returns:
        專案資料 dict，內含 mode 欄位

    Raises:
        ValueError: 格式無效或版本不相容
        FileNotFoundError: 檔案不存在
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"專案檔不存在: {filepath}")

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    mode = data.get("mode")
    if mode not in ("p52", "4grid"):
        raise ValueError(f"無效的 mode 欄位: {mode}")

    version = data.get("version", "0.0")
    if version != PROJECT_VERSION:
        logger.warning(f"Project version mismatch: {version} vs {PROJECT_VERSION}")

    return data


def validate_paths(data: dict) -> list[str]:
    """
    驗證專案資料中的所有檔案路徑是否存在

    Args:
        data: load_project() 回傳的專案資料

    Returns:
        遺失路徑清單（空列表表示全部存在）
    """
    missing = []
    mode = data.get("mode")

    if mode == "p52":
        police = data.get("police_photo_path", "")
        if police and not os.path.exists(police):
            missing.append(police)
        for p in data.get("target_photo_paths", []):
            if p and not os.path.exists(p):
                missing.append(p)

    elif mode == "4grid":
        for case in data.get("cases", []):
            for p in case.get("image_paths", []):
                if p and not os.path.exists(p):
                    missing.append(p)

    return missing


def get_p52_project_path(working_dir: str, ad_date: str) -> str:
    """取得 P52 專案檔路徑（格式: {AD日期}超速.json）"""
    return str(Path(working_dir) / f"{ad_date}超速.json")


def get_4grid_project_path(working_dir: str, ad_date: str) -> str:
    """取得 4Grid 專案檔路徑（格式: {AD日期}闖紅燈.json）"""
    return str(Path(working_dir) / f"{ad_date}闖紅燈.json")
