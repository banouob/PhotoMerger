"""
测试 core.data_manager 模块
"""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from core.grid4.data_manager import (
    CaseData,
    CaseStatus,
    DataManager,
    ImageState,
    get_data_manager,
)


@pytest.fixture
def temp_cases_dir():
    """创建临时案件目录结构"""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)

        # 创建测试案件文件夹
        # Case 1: 3张图片（有效案件）
        case1_dir = temp_path / "case1"
        case1_dir.mkdir()
        _create_test_image(case1_dir / "img1.jpg")
        _create_test_image(case1_dir / "img2.jpg")
        _create_test_image(case1_dir / "img3.jpg")

        # Case 2: 2张图片（错误案件）
        case2_dir = temp_path / "case2"
        case2_dir.mkdir()
        _create_test_image(case2_dir / "img1.jpg")
        _create_test_image(case2_dir / "img2.jpg")

        # Case 3: 5张图片（错误案件）
        case3_dir = temp_path / "case3"
        case3_dir.mkdir()
        for i in range(5):
            _create_test_image(case3_dir / f"img{i}.jpg")

        # Case 4: 空文件夹（错误案件）
        case4_dir = temp_path / "case4"
        case4_dir.mkdir()

        # Case 5: 3张图片 + 非图片文件（有效案件，应忽略非图片）
        case5_dir = temp_path / "case5"
        case5_dir.mkdir()
        _create_test_image(case5_dir / "img1.jpg")
        _create_test_image(case5_dir / "img2.jpg")
        _create_test_image(case5_dir / "img3.jpg")
        (case5_dir / "readme.txt").write_text("test")

        yield temp_path


def _create_test_image(path: Path):
    """创建测试用的图片文件"""
    img = Image.new('RGB', (100, 100), color='red')
    img.save(path)


@pytest.fixture
def data_manager():
    """创建测试用的 DataManager 实例"""
    return DataManager()


def test_case_status_enum():
    """测试 CaseStatus 枚举值"""
    assert CaseStatus.PENDING.value == "pending"
    assert CaseStatus.ERROR.value == "error"
    assert CaseStatus.DONE.value == "done"


def test_image_state_default_values():
    """测试 ImageState 默认值"""
    state = ImageState()

    assert state.arrows == []
    assert state.brightness == 0
    assert state.contrast == 0
    assert state.saturation == 0
    assert state.sharpness == 0


def test_case_data_default_values():
    """测试 CaseData 默认值"""
    case = CaseData()

    assert case.folder_path == ""
    assert case.image_paths == []
    assert len(case.image_states) == 3
    assert case.meta_data == {}
    assert case.status == CaseStatus.PENDING


def test_scan_root_folder_returns_case_count(temp_cases_dir, data_manager):
    """测试 scan_root_folder() 返回案件数量"""
    count = data_manager.scan_root_folder(str(temp_cases_dir))

    # 应该扫描到 5 个子文件夹
    assert count == 5


def test_scan_root_folder_identifies_valid_cases(temp_cases_dir, data_manager):
    """测试扫描识别有效案件（3张图片）"""
    data_manager.scan_root_folder(str(temp_cases_dir))

    # Case 1 和 Case 5 应该是 PENDING（3张图片）
    pending_cases = [c for c in data_manager.cases if c.status == CaseStatus.PENDING]
    assert len(pending_cases) == 2


def test_scan_root_folder_identifies_error_cases(temp_cases_dir, data_manager):
    """测试扫描识别错误案件（图片数量 != 3）"""
    data_manager.scan_root_folder(str(temp_cases_dir))

    # Case 2, 3, 4 应该是 ERROR
    error_cases = [c for c in data_manager.cases if c.status == CaseStatus.ERROR]
    assert len(error_cases) == 3


def test_scan_root_folder_ignores_non_image_files(temp_cases_dir, data_manager):
    """测试扫描忽略非图片文件"""
    data_manager.scan_root_folder(str(temp_cases_dir))

    # Case 5 有 3张图片 + 1个txt，应该只识别图片
    case5 = [c for c in data_manager.cases if "case5" in c.folder_path][0]
    assert len(case5.image_paths) == 3


def test_scan_root_folder_sets_current_case_to_first(temp_cases_dir, data_manager):
    """测试扫描后自动选中第一个案件"""
    data_manager.scan_root_folder(str(temp_cases_dir))

    assert data_manager.current_case_index == 0


def test_scan_nonexistent_folder_returns_zero(data_manager):
    """测试扫描不存在的文件夹返回 0"""
    count = data_manager.scan_root_folder("/nonexistent/path")

    assert count == 0
    assert len(data_manager.cases) == 0


def test_get_current_case_returns_case(temp_cases_dir, data_manager):
    """测试 get_current_case() 返回当前案件"""
    data_manager.scan_root_folder(str(temp_cases_dir))

    current = data_manager.get_current_case()

    assert current is not None
    assert isinstance(current, CaseData)
    assert current == data_manager.cases[0]


def test_get_current_case_returns_none_when_empty(data_manager):
    """测试没有案件时 get_current_case() 返回 None"""
    current = data_manager.get_current_case()

    assert current is None


def test_set_current_case_switches_case(temp_cases_dir, data_manager):
    """测试 set_current_case() 切换案件"""
    data_manager.scan_root_folder(str(temp_cases_dir))

    # 切换到第 2 个案件
    success = data_manager.set_current_case(1)

    assert success is True
    assert data_manager.current_case_index == 1
    assert data_manager.get_current_case() == data_manager.cases[1]


def test_set_current_case_rejects_invalid_index(temp_cases_dir, data_manager):
    """测试 set_current_case() 拒绝无效索引"""
    data_manager.scan_root_folder(str(temp_cases_dir))

    # 尝试切换到无效索引
    success1 = data_manager.set_current_case(-1)
    success2 = data_manager.set_current_case(999)

    assert success1 is False
    assert success2 is False
    assert data_manager.current_case_index == 0  # 保持原索引


def test_swap_images_exchanges_paths_and_states():
    """测试 swap_images() 交换图片路径和编辑状态"""
    dm = DataManager()

    case = CaseData(
        folder_path="test",
        image_paths=["img1.jpg", "img2.jpg", "img3.jpg"],
    )

    # 修改编辑状态以便验证
    case.image_states[0].brightness = 10
    case.image_states[2].brightness = 30

    # 交换第 0 和第 2 张
    dm.swap_images(case, 0, 2)

    # 验证路径已交换
    assert case.image_paths == ["img3.jpg", "img2.jpg", "img1.jpg"]

    # 验证编辑状态也交换了
    assert case.image_states[0].brightness == 30
    assert case.image_states[2].brightness == 10


def test_swap_images_raises_on_invalid_index():
    """测试 swap_images() 对无效索引抛出异常"""
    dm = DataManager()

    case = CaseData(
        image_paths=["img1.jpg", "img2.jpg", "img3.jpg"]
    )

    with pytest.raises(IndexError):
        dm.swap_images(case, 0, 5)

    with pytest.raises(IndexError):
        dm.swap_images(case, -1, 1)


def test_mark_case_as_done_changes_status():
    """测试 mark_case_as_done() 修改案件状态"""
    dm = DataManager()

    case = CaseData(status=CaseStatus.PENDING)
    dm.mark_case_as_done(case)

    assert case.status == CaseStatus.DONE


def test_get_case_summary_returns_correct_counts(temp_cases_dir, data_manager):
    """测试 get_case_summary() 返回正确的统计"""
    data_manager.scan_root_folder(str(temp_cases_dir))

    # 标记一个案件为 DONE
    data_manager.mark_case_as_done(data_manager.cases[0])

    summary = data_manager.get_case_summary()

    assert summary["total"] == 5
    assert summary["pending"] == 1  # Case 5 (原本 Case 1 和 5 是 PENDING，但 Case 1 被标记为 DONE)
    assert summary["done"] == 1
    assert summary["error"] == 3


def test_get_next_pending_case_index_finds_next_pending(temp_cases_dir, data_manager):
    """测试 get_next_pending_case_index() 找到下一个待处理案件"""
    data_manager.scan_root_folder(str(temp_cases_dir))

    # 标记第一个 PENDING 案件为 DONE
    for case in data_manager.cases:
        if case.status == CaseStatus.PENDING:
            data_manager.mark_case_as_done(case)
            break

    # 应该还有一个 PENDING 案件
    next_index = data_manager.get_next_pending_case_index()

    assert next_index is not None
    assert data_manager.cases[next_index].status == CaseStatus.PENDING


def test_get_next_pending_case_index_returns_none_when_all_done(data_manager):
    """测试所有案件完成后 get_next_pending_case_index() 返回 None"""
    # 创建已完成的案件
    data_manager.cases = [
        CaseData(status=CaseStatus.DONE),
        CaseData(status=CaseStatus.ERROR),
    ]

    next_index = data_manager.get_next_pending_case_index()

    assert next_index is None


def test_sort_images_by_filename_when_no_exif(temp_cases_dir, data_manager):
    """测试无 EXIF 时按文件名排序"""
    # 创建文件名乱序的案件
    case_dir = temp_cases_dir / "test_sort"
    case_dir.mkdir()

    # 创建乱序文件名
    _create_test_image(case_dir / "c.jpg")
    _create_test_image(case_dir / "a.jpg")
    _create_test_image(case_dir / "b.jpg")

    data_manager.scan_root_folder(str(temp_cases_dir))

    # 找到测试案件
    test_case = [c for c in data_manager.cases if "test_sort" in c.folder_path][0]

    # 验证文件名已按字典序排序
    filenames = [Path(p).name for p in test_case.image_paths]
    assert filenames == ["a.jpg", "b.jpg", "c.jpg"]


def test_extract_exif_datetime_returns_none_for_no_exif(temp_cases_dir, data_manager):
    """测试无 EXIF 数据的图片返回 None"""
    # 创建无 EXIF 的测试图片
    test_img_path = temp_cases_dir / "test.jpg"
    _create_test_image(test_img_path)

    exif_time = data_manager._extract_exif_datetime(str(test_img_path))

    assert exif_time is None


def test_get_data_manager_singleton():
    """测试 get_data_manager() 单例模式"""
    # 重置全局实例
    import core.grid4.data_manager
    core.grid4.data_manager._data_manager = None

    # 获取两次实例
    dm1 = get_data_manager()
    dm2 = get_data_manager()

    # 验证是同一个实例
    assert dm1 is dm2


def test_image_states_initialized_with_three_empty_states():
    """测试 CaseData 初始化时包含 3 个空的 ImageState"""
    case = CaseData()

    assert len(case.image_states) == 3
    assert all(isinstance(state, ImageState) for state in case.image_states)
    assert all(state.brightness == 0 for state in case.image_states)


def test_scan_images_supports_multiple_formats(temp_cases_dir, data_manager):
    """测试支持多种图片格式"""
    # 创建包含多种格式的案件
    case_dir = temp_cases_dir / "multi_format"
    case_dir.mkdir()

    _create_test_image(case_dir / "img1.jpg")
    _create_test_image(case_dir / "img2.png")
    _create_test_image(case_dir / "img3.bmp")

    data_manager.scan_root_folder(str(temp_cases_dir))

    # 找到测试案件
    test_case = [c for c in data_manager.cases if "multi_format" in c.folder_path][0]

    # 应该识别所有格式
    assert len(test_case.image_paths) == 3
    assert test_case.status == CaseStatus.PENDING
