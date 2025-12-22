import ctypes
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO

import qdarkstyle
from PySide6 import QtGui, QtWidgets, QtCore, QtWebEngineWidgets, QtWebEngineCore

from ..utility import TEMP_DIR
from .setting import load_font_family, load_font_size


# 重定向 stdout/stderr，解决 pythonw.exe 启动问题
if sys.executable.endswith("pythonw.exe"):
    pythonw_log_folder: Path = TEMP_DIR.joinpath("pythonw_log")
    pythonw_log_folder.mkdir(parents=True, exist_ok=True)

    file_name: str = datetime.now().strftime("%Y%m%d_%H%M%S.log")
    file_path: Path = pythonw_log_folder.joinpath(file_name)

    f: TextIO = open(file_path, "w", buffering=1)  # 行缓冲，便于实时查看
    sys.stdout = f
    sys.stderr = f


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
