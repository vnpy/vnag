import ctypes
import platform
import sys
from pathlib import Path

import qdarkstyle
from PySide6 import QtGui, QtWidgets

from .window import MainWindow


def create_qapp() -> QtWidgets.QApplication:
    """创建Qt应用"""
    # 设置样式
    qapp: QtWidgets.QApplication = QtWidgets.QApplication(sys.argv)
    qapp.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyside6"))

    # 设置字体
    font: QtGui.QFont = QtGui.QFont("微软雅黑", 12)
    qapp.setFont(font)

    # 设置图标
    icon_path: Path = Path(__file__).parent / "logo.ico"
    icon: QtGui.QIcon = QtGui.QIcon(str(icon_path))
    qapp.setWindowIcon(icon)

    # 设置进程ID
    if "Windows" in platform.uname():
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("vnag")

    return qapp


if __name__ == "__main__":
    app: QtWidgets.QApplication = create_qapp()

    window: MainWindow = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())
