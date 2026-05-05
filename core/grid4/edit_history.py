"""
編輯歷史模組

實現撤銷/重做功能
"""

import logging
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EditSnapshot:
    """
    編輯快照（用於撤銷/重做）

    功能:
    - 儲存完整的編輯狀態
    - 支援深複製
    """

    arrows: list[tuple[float, float, float, float]] = field(default_factory=list)
    sub_image: dict[str, Any] | None = None  # 子圖資料
    brightness: int = 0
    contrast: int = 0
    saturation: int = 0
    sharpness: int = 0

    def copy(self) -> 'EditSnapshot':
        """
        建立快照副本

        Returns:
            快照副本
        """
        return EditSnapshot(
            arrows=deepcopy(self.arrows),
            sub_image=deepcopy(self.sub_image),
            brightness=self.brightness,
            contrast=self.contrast,
            saturation=self.saturation,
            sharpness=self.sharpness
        )


class EditHistory:
    """
    編輯歷史管理器（撤銷/重做）

    功能:
    - 管理撤銷棧和重做棧
    - 記錄編輯快照
    - 支援最大歷史記錄數
    """

    def __init__(self, max_history: int = 50):
        """
        初始化編輯歷史管理器

        Args:
            max_history: 最大歷史記錄數
        """
        self.max_history = max_history
        self.undo_stack: list[EditSnapshot] = []
        self.redo_stack: list[EditSnapshot] = []

    def push(self, snapshot: EditSnapshot):
        """
        記錄新快照

        Args:
            snapshot: 編輯快照
        """
        # 新增到撤銷棧
        self.undo_stack.append(snapshot.copy())

        # 限制棧大小
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)

        # 清空重做棧（新操作會使重做失效）
        self.redo_stack.clear()

    def undo(self) -> EditSnapshot | None:
        """
        撤銷操作

        Returns:
            上一個快照，如果無法撤銷則返回 None
        """
        if not self.can_undo():
            return None

        # 當前狀態移到重做棧
        current = self.undo_stack.pop()
        self.redo_stack.append(current)

        # 返回上一個狀態
        if self.undo_stack:
            return self.undo_stack[-1].copy()
        else:
            # 撤銷到初始狀態
            return EditSnapshot()

    def redo(self) -> EditSnapshot | None:
        """
        重做操作

        Returns:
            下一個快照，如果無法重做則返回 None
        """
        if not self.can_redo():
            return None

        # 重做棧頂移回撤銷棧
        snapshot = self.redo_stack.pop()
        self.undo_stack.append(snapshot)

        return snapshot.copy()

    def can_undo(self) -> bool:
        """
        是否可以撤銷

        Returns:
            True 如果可以撤銷
        """
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """
        是否可以重做

        Returns:
            True 如果可以重做
        """
        return len(self.redo_stack) > 0

    def clear(self):
        """清空所有歷史記錄"""
        self.undo_stack.clear()
        self.redo_stack.clear()

    def get_undo_count(self) -> int:
        """
        獲取撤銷棧大小

        Returns:
            撤銷棧大小
        """
        return len(self.undo_stack)

    def get_redo_count(self) -> int:
        """
        獲取重做棧大小

        Returns:
            重做棧大小
        """
        return len(self.redo_stack)


if __name__ == "__main__":
    # 測試編輯歷史
    history = EditHistory(max_history=5)

    # 測試記錄快照
    snapshot1 = EditSnapshot(
        arrows=[(0.1, 0.1, 0.5, 0.5)],
        brightness=10
    )
    history.push(snapshot1)
    print(f"撤銷棧大小: {history.get_undo_count()}")  # 1
    print(f"可以撤銷: {history.can_undo()}")  # True
    print(f"可以重做: {history.can_redo()}")  # False

    # 測試撤銷
    undone = history.undo()
    print(f"撤銷後: 箭頭={undone.arrows}, 亮度={undone.brightness}")  # [], 0
    print(f"可以撤銷: {history.can_undo()}")  # False
    print(f"可以重做: {history.can_redo()}")  # True

    # 測試重做
    redone = history.redo()
    print(f"重做後: 箭頭={redone.arrows}, 亮度={redone.brightness}")  # [(0.1, 0.1, 0.5, 0.5)], 10

    # 測試新操作清空重做棧
    snapshot2 = EditSnapshot(
        arrows=[(0.2, 0.2, 0.6, 0.6)],
        brightness=20
    )
    history.push(snapshot2)
    print(f"新操作後可以重做: {history.can_redo()}")  # False
