from typing import cast
import markdown

from PySide6 import QtWidgets, QtGui, QtCore

from .gateway import AgentGateway
from .utility import load_json, save_json, AGENT_DIR
from . import __version__


class MainWindow(QtWidgets.QMainWindow):
    """主窗口"""

    def __init__(self) -> None:
        """构造函数"""
        super().__init__()

        self.gateway: AgentGateway = AgentGateway()

        self.chat_history: list[dict[str, str]] = []

        self.init_ui()
        self.load_history()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(f"VeighNa Agent - {__version__} - [ {AGENT_DIR} ]")

        self.init_menu()
        self.init_widgets()

    def init_widgets(self) -> None:
        """初始化中央控件"""
        desktop: QtCore.QRect = QtWidgets.QApplication.primaryScreen().availableGeometry()

        self.input_widget: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.input_widget.setMaximumHeight(desktop.height() // 4)

        self.history_widget: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.history_widget.setReadOnly(True)

        self.send_button: QtWidgets.QPushButton = QtWidgets.QPushButton("发送请求")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedWidth(300)
        self.send_button.setFixedHeight(50)

        self.clear_button: QtWidgets.QPushButton = QtWidgets.QPushButton("清空历史")
        self.clear_button.clicked.connect(self.clear_history)
        self.clear_button.setFixedWidth(300)
        self.clear_button.setFixedHeight(50)

        self.status_label: QtWidgets.QLabel = QtWidgets.QLabel("尚未初始化AI服务连接")
        self.status_label.setFixedWidth(300)

        hbox1 = QtWidgets.QHBoxLayout()
        hbox1.addWidget(QtWidgets.QLabel("会话历史"))
        hbox1.addStretch()

        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.addWidget(QtWidgets.QLabel("请求输入"))
        hbox2.addStretch()

        hbox3 = QtWidgets.QHBoxLayout()
        hbox3.addWidget(self.clear_button)
        hbox3.addStretch()
        hbox3.addWidget(self.status_label)
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

    def append_message(self, role: str, content: str) -> None:
        """在会话历史组件中添加消息"""
        self.history_widget.moveCursor(QtGui.QTextCursor.MoveOperation.End)

        if role == "user":
            # 用户内容不需要被渲染
            escaped_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

            html = f"""
            <p><b>💬 User</b></p>
            <div>{escaped_content}</div>
            <br><br>
            """
            self.history_widget.insertHtml(html)
        elif role == "assistant":
            # AI返回内容以Markdown渲染
            html_content = markdown.markdown(content, extensions=['fenced_code', 'codehilite'])

            html = f"""
            <p><b>✨ Assistant</b></p>
            {html_content}
            <br><br>
            """
            self.history_widget.insertHtml(html)

        # 确保滚动条滚动到最新消息
        self.history_widget.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def init_menu(self) -> None:
        """初始化菜单"""
        menu_bar: QtWidgets.QMenuBar = self.menuBar()

        sys_menu: QtWidgets.QMenu = menu_bar.addMenu("系统")
        sys_menu.addAction("连接", self.connect_gateway)
        sys_menu.addSeparator()
        sys_menu.addAction("退出", self.close)

        help_menu: QtWidgets.QMenu = menu_bar.addMenu("帮助")
        help_menu.addAction("官网", self.open_website)
        help_menu.addAction("关于", self.show_about)

    def connect_gateway(self) -> None:
        """连接网关"""
        dialog: ConnectionDialog = ConnectionDialog()
        n: int = dialog.exec_()

        if n != dialog.DialogCode.Accepted:
            return

        self.gateway.init(
            base_url=dialog.base_url,
            api_key=dialog.api_key,
            model_name=dialog.model_name
        )

        self.status_label.setText("AI服务连接已完成初始化")

    def send_message(self) -> None:
        """发送消息"""
        text: str = self.input_widget.toPlainText().strip()
        if not text:
            return
        self.input_widget.clear()

        user_message: dict[str, str] = {"role": "user", "content": text}
        self.chat_history.append(user_message)
        self.append_message("user", text)

        self.status_label.setText("AI服务正在思考中...")
        QtWidgets.QApplication.processEvents()

        content: str | None = self.gateway.invoke_model(self.chat_history)

        self.status_label.setText("AI服务连接已完成初始化")

        if content:
            self.chat_history.append({"role": "assistant", "content": content})
            self.append_message("assistant", content)

        self.save_history()

    def save_history(self) -> None:
        """保存会话历史"""
        save_json("chat_history.json", self.chat_history)

    def load_history(self) -> None:
        """加载会话历史"""
        chat_history: list[dict[str, str]] | None = cast(list[dict[str, str]], load_json("chat_history.json"))

        if chat_history:
            self.chat_history = chat_history

        self.history_widget.clear()
        for message in self.chat_history:
            self.append_message(message["role"], message["content"])

    def clear_history(self) -> None:
        """清空会话历史"""
        i: int = QtWidgets.QMessageBox.question(
            self,
            "清空历史",
            "确定要清空历史吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if i == QtWidgets.QMessageBox.StandardButton.Yes:
            self.history_widget.clear()

            self.chat_history.clear()
            self.save_history()

    def show_about(self) -> None:
        """显示关于"""
        QtWidgets.QMessageBox.information(
            self,
            "关于",
            (
                "VeighNa Agent\n"
                "\n"
                f"版本号：{__version__}\n"
                "\n"
                f"运行目录：{AGENT_DIR}"
            )
        )

    def open_website(self) -> None:
        """打开官网"""
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://www.github.com/vnpy/vnag"))


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
