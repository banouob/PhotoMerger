"""
共用測試 fixtures

提供 session 層級的 QApplication 實例，避免多個測試模組各自建立 QApplication 造成衝突。
"""

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """
    Session 層級的 QApplication fixture

    整個測試 session 只建立一次 QApplication，
    避免 PyQt6 在多個測試模組中重複建立/銷毀 QApplication 導致 abort。
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
