from vnag.gateway import BaseGateway
from vnag.engine import AgentEngine
from vnag.ui.window import MainWindow
from vnag.factory import create_gateway
from vnag.ui.qt import create_qapp, QtWidgets


def main() -> None:
    """主函数"""
    qapp: QtWidgets.QApplication = create_qapp()

    gateway: BaseGateway = create_gateway()

    engine: AgentEngine = AgentEngine(gateway)
    engine.init()

    window: MainWindow = MainWindow(engine)
    window.showMaximized()

    qapp.exec()


if __name__ == "__main__":
    main()
