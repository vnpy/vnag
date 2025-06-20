from PySide6 import QtWidgets


from .gateway import AgentGateway
from .utility import load_json, save_json, AGENT_DIR
from . import __version__


class MainWindow(QtWidgets.QMainWindow):
    """主窗口"""

    def __init__(self) -> None:
        """构造函数"""
        super().__init__()

        self.gateway: AgentGateway = AgentGateway()

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(f"VeighNa Agent - {__version__} - [ {AGENT_DIR} ]")

        self.init_menu()
        self.init_widgets()

    def init_widgets(self) -> None:
        """初始化中央控件"""
        self.input_widget: QtWidgets.QTextEdit = QtWidgets.QTextEdit()

        self.history_widget: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.history_widget.setReadOnly(True)

        self.send_button: QtWidgets.QPushButton = QtWidgets.QPushButton("发送")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedWidth(300)
        self.send_button.setFixedHeight(50)

        hbox1 = QtWidgets.QHBoxLayout()
        hbox1.addWidget(QtWidgets.QLabel("会话历史"))
        hbox1.addStretch()

        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.addWidget(QtWidgets.QLabel("请求输入"))
        hbox2.addStretch()

        hbox3 = QtWidgets.QHBoxLayout()
        hbox3.addStretch()
        hbox3.addWidget(self.send_button)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox1)
        vbox.addWidget(self.history_widget)
        vbox.addLayout(hbox2)
        vbox.addWidget(self.input_widget)
        vbox.addLayout(hbox3)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(vbox)
        self.setCentralWidget(central_widget)

    def init_menu(self) -> None:
        """初始化菜单"""
        menu_bar: QtWidgets.QMenuBar = self.menuBar()

        sys_menu: QtWidgets.QMenu = menu_bar.addMenu("系统")
        sys_menu.addAction("连接", self.connect_gateway)

    def connect_gateway(self) -> None:
        """连接网关"""
        dialog: ConnectionDialog = ConnectionDialog()
        n: int = dialog.exec_()

        if n != dialog.Accepted:
            return

        self.gateway.init(
            base_url=dialog.base_url,
            api_key=dialog.api_key,
            model_name=dialog.model_name
        )

    def send_message(self) -> None:
        """发送消息"""
        text: str = self.input_widget.toPlainText()
        self.input_widget.clear()

        self.history_widget.append("--------------------------------")
        self.history_widget.append(text)

        messages: list[dict[str, str]] = [
            {"role": "user", "content": text}
        ]

        content: str | None = self.gateway.invoke_model(messages)
        if content:
            self.history_widget.append("--------------------------------")
            self.history_widget.append(content)


class ConnectionDialog(QtWidgets.QDialog):
    """连接对话框"""

    setting_filename: str = "gateway_setting.json"

    def __init__(self) -> None:
        """构造函数"""
        super().__init__()

        self.base_url: str = ""
        self.api_key: str = ""
        self.model_name: str = ""

        self.init_ui()
        self.load_setting()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("初始化连接")
        self.setFixedWidth(500)

        self.url_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.key_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.model_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()

        self.connect_button: QtWidgets.QPushButton = QtWidgets.QPushButton("连接")
        self.connect_button.clicked.connect(self.connect)

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow("服务地址", self.url_line)
        form.addRow("API Key", self.key_line)
        form.addRow("模型名称", self.model_line)
        form.addRow(self.connect_button)

        self.setLayout(form)

    def load_setting(self) -> None:
        """加载设置"""
        setting: dict = load_json(self.setting_filename)
        self.url_line.setText(setting.get("base_url", ""))
        self.key_line.setText(setting.get("api_key", ""))
        self.model_line.setText(setting.get("model_name", ""))

    def connect(self) -> None:
        """接受"""
        self.base_url = self.url_line.text()
        self.api_key = self.key_line.text()
        self.model_name = self.model_line.text()

        setting = {
            "base_url": self.base_url,
            "api_key": self.api_key,
            "model_name": self.model_name
        }
        save_json(self.setting_filename, setting)

        self.accept()
