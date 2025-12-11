import ctypes
import platform
import sys
from pathlib import Path

import qdarkstyle
from PySide6 import QtGui, QtWidgets, QtCore, QtWebEngineWidgets, QtWebEngineCore

from .setting import load_font_family, load_font_size


def create_qapp() -> QtWidgets.QApplication:
    """创建Qt应用"""
    # 设置样式
    qapp: QtWidgets.QApplication = QtWidgets.QApplication(sys.argv)
    qapp.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyside6"))

    # 设置字体
    font_family: str = load_font_family()
    font_size: int = load_font_size()
    font: QtGui.QFont = QtGui.QFont(font_family, font_size)
    qapp.setFont(font)

    # 设置图标
    icon_path: Path = Path(__file__).parent / "logo.ico"
    icon: QtGui.QIcon = QtGui.QIcon(str(icon_path))
    qapp.setWindowIcon(icon)

    # 设置进程ID
    if "Windows" in platform.uname():
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("vnag")

    return qapp


__all__ = [
    "create_qapp",
    "QtCore",
    "QtGui",
    "QtWidgets",
    "QtWebEngineWidgets",
    "QtWebEngineCore",
]
