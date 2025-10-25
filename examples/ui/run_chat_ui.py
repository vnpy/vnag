from vnag.utility import load_json
from vnag.gateways.openai_gateway import OpenaiGateway
from vnag.ui.window import MainWindow
from vnag.ui.qt import create_qapp, QtWidgets
from vnag.engine import AgentEngine


def main() -> None:
    """主函数"""
    qapp: QtWidgets.QApplication = create_qapp()

    setting: dict = load_json("connect_openai.json")

    gateway: OpenaiGateway = OpenaiGateway()
    gateway.init(setting)

    engine: AgentEngine = AgentEngine(gateway)
    engine.init()

    window: MainWindow = MainWindow(engine)
    window.showMaximized()

    qapp.exec()


if __name__ == "__main__":
    main()
