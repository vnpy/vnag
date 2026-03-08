from vnag.gateway import BaseGateway
from vnag.engine import AgentEngine
from vnag.tracer import setup_logging
from vnag.ui.window import MainWindow
from vnag.ui.factory import create_gateway
from vnag.ui.qt import create_qapp, QtWidgets
from vnag.ui.tools import register_all


def main() -> None:
    """主函数（启动 Qt GUI 界面）"""
    setup_logging(enable_console=True)

    qapp: QtWidgets.QApplication = create_qapp()

    gateway: BaseGateway = create_gateway()

    engine: AgentEngine = AgentEngine(gateway)
    engine.init()

    register_all(engine)

    window: MainWindow = MainWindow(engine)
    window.showMaximized()

    qapp.exec()


if __name__ == "__main__":
    main()
