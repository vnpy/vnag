from typing import Any
from pathlib import Path
from uuid import uuid4
import json

from ..gateway import BaseGateway
from ..utility import AGENT_DIR, save_json, load_json
from ..object import Request, Message, Session
from ..constant import Role
from .. import __version__
from .widget import HistoryWidget
from .worker import StreamWorker
from .qt import QtWidgets, QtGui, QtCore


SESSION_DIR = AGENT_DIR.joinpath("session")
SESSION_DIR.mkdir(parents=True, exist_ok=True)


class MainWindow(QtWidgets.QMainWindow):
    """主窗口"""

    setting_filename: str = "chat_setting.json"

    def __init__(self, gateway: BaseGateway) -> None:
        """构造函数"""
        super().__init__()

        self.gateway: BaseGateway = gateway

        self.setting: dict[str, Any] = {}
        self.sessions: dict[str, Session] = {}
        self.current_id: str = ""
        self.models: list[str] = self.gateway.list_models()

        self.init_ui()
        self.load_setting()
        self.load_sessions()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(f"VeighNa Agent - {__version__} - [ {AGENT_DIR} ]")

        self.init_menu()
        self.init_widgets()

        self.status_label: QtWidgets.QLabel = QtWidgets.QLabel()
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.statusBar().addWidget(self.status_label, 1)

    def init_widgets(self) -> None:
        """初始化中央控件"""
        # 左侧会话相关
        self.new_button: QtWidgets.QPushButton = QtWidgets.QPushButton("新建会话")
        self.new_button.setFixedHeight(50)
        self.new_button.clicked.connect(self.new_session)

        self.session_list: QtWidgets.QListWidget = QtWidgets.QListWidget()
        self.session_list.itemClicked.connect(self.switch_session)
        self.session_list.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self.show_menu)
        self.session_list.setFixedWidth(300)

        left_vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        left_vbox.addWidget(self.session_list)
        left_vbox.addWidget(self.new_button)

        # 右侧聊天相关
        desktop: QtCore.QRect = QtWidgets.QApplication.primaryScreen().availableGeometry()

        self.input_widget: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.input_widget.setMaximumHeight(desktop.height() // 4)
        self.input_widget.setPlaceholderText("在这里输入消息，点击下方按钮发送")

        self.history_widget: HistoryWidget = HistoryWidget()

        self.send_button: QtWidgets.QPushButton = QtWidgets.QPushButton("发送请求")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedWidth(300)
        self.send_button.setFixedHeight(50)

        completer: QtWidgets.QCompleter = QtWidgets.QCompleter(self.models)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

        self.model_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.model_line.setFixedWidth(300)
        self.model_line.setFixedHeight(50)
        self.model_line.setPlaceholderText("请输入要使用的模型")
        self.model_line.setCompleter(completer)

        hbox3 = QtWidgets.QHBoxLayout()
        hbox3.addStretch()
        hbox3.addWidget(self.model_line)
        hbox3.addWidget(self.send_button)

        right_vbox = QtWidgets.QVBoxLayout()
        right_vbox.addWidget(self.history_widget)
        right_vbox.addWidget(self.input_widget)
        right_vbox.addLayout(hbox3)

        # 主布局
        main_hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        main_hbox.addLayout(left_vbox)
        main_hbox.addLayout(right_vbox)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_hbox)
        self.setCentralWidget(central_widget)

    def init_menu(self) -> None:
        """初始化菜单"""
        menu_bar: QtWidgets.QMenuBar = self.menuBar()

        sys_menu: QtWidgets.QMenu = menu_bar.addMenu("系统")
        sys_menu.addAction("退出", self.close)

        help_menu: QtWidgets.QMenu = menu_bar.addMenu("帮助")
        help_menu.addAction("官网", self.open_website)
        help_menu.addAction("关于", self.show_about)

    def save_setting(self) -> None:
        """保存设置"""
        save_json(self.setting_filename, self.setting)

    def load_setting(self) -> None:
        """加载设置"""
        self.setting = load_json(self.setting_filename)

        self.model_line.setText(self.setting.get("model", ""))

    def send_message(self) -> None:
        """发送消息"""
        # 检查模型名称
        model: str = self.model_line.text()
        if model not in self.models:
            QtWidgets.QMessageBox.warning(self, "模型名称错误", f"找不到模型：{model}，请检查模型名称是否正确")
            return

        # 保存模型设置
        self.setting["model"] = model
        self.save_setting()

        # 检查输入内容
        text: str = self.input_widget.toPlainText().strip()
        if not text:
            return
        self.input_widget.clear()

        # 保存用户消息
        session: Session = self.sessions[self.current_id]

        user_message: Message = Message(role=Role.USER, content=text)
        session.messages.append(user_message)
        self.history_widget.append_message(user_message.role, user_message.content)

        # 准备流式请求
        self.history_widget.start_stream()

        self.send_button.setEnabled(False)
        self.status_label.setText("正在等待AI服务返回数据...")

        request: Request = Request(
            model=model,
            messages=session.messages,
            temperature=0.2
        )

        # 设置并启动Worker
        worker: StreamWorker = StreamWorker(self.gateway, request)
        worker.signals.delta.connect(self.on_stream_delta)
        worker.signals.finished.connect(self.on_stream_finished)
        worker.signals.error.connect(self.on_stream_error)

        QtCore.QThreadPool.globalInstance().start(worker)

    def append_message(self, role: Role, content: str) -> None:
        """在会话历史组件中添加消息"""
        self.history_widget.append_message(role, content)

    def on_stream_delta(self, content_delta: str) -> None:
        """
        处理数据流返回的数据块
        """
        self.history_widget.update_stream(content_delta)

    def on_stream_finished(self) -> None:
        """
        处理数据流结束事件
        """
        self.send_button.setEnabled(True)
        self.status_label.clear()

        full_content: str = self.history_widget.finish_stream()

        if full_content:
            message: Message = Message(role=Role.ASSISTANT, content=full_content)
            session: Session = self.sessions[self.current_id]
            session.messages.append(message)

        self.save_current()

    def on_stream_error(self, error_msg: str) -> None:
        """
        处理数据流错误事件
        """
        self.send_button.setEnabled(True)
        self.status_label.setText("发生错误")
        QtWidgets.QMessageBox.critical(self, "错误", f"流式请求失败：\n{error_msg}")

    def save_current(self) -> None:
        """保存当前会话"""
        session: Session = self.sessions[self.current_id]
        self.save_session(session)

    def save_session(self, session: Session) -> None:
        """保存单个会话到文件"""
        data: dict = session.model_dump()
        file_path: Path = SESSION_DIR.joinpath(f"{session.id}.json")

        with open(file_path, mode="w+", encoding="UTF-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

    def load_sessions(self) -> None:
        """加载所有会话"""
        self.sessions.clear()

        session_files: list[Path] = sorted(
            SESSION_DIR.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        for file_path in session_files:
            with open(file_path, encoding="UTF-8") as f:
                data: dict = json.load(f)
                session: Session = Session.model_validate(data)
                self.sessions[session.id] = session

        if not self.sessions:
            self.new_session()
        else:
            self.current_id = next(iter(self.sessions.keys()))
            self.display_session()

        self.update_list()

    def update_list(self) -> None:
        """更新会话列表UI"""
        self.session_list.clear()

        for session_id, session in self.sessions.items():
            item: QtWidgets.QListWidgetItem = QtWidgets.QListWidgetItem(session.name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, session_id)
            self.session_list.addItem(item)

            if session_id == self.current_id:
                self.session_list.setCurrentItem(item)

    def display_session(self) -> None:
        """显示当前会话的聊天记录"""
        self.history_widget.clear()

        session: Session | None = self.sessions.get(self.current_id)
        if not session:
            return

        for message in session.messages:
            self.history_widget.append_message(message.role, message.content)

    def new_session(self) -> None:
        """创建新会话"""
        session: Session = Session(
            id=str(uuid4()),
            name="默认会话"
        )
        self.sessions[session.id] = session

        self.current_id = session.id

        self.display_session()
        self.update_list()
        self.save_session(session)

    def switch_session(self, item: QtWidgets.QListWidgetItem) -> None:
        """切换会话"""
        session_id: str = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.current_id = session_id
        self.display_session()

    def show_menu(self, pos: QtCore.QPoint) -> None:
        """显示会话的右键菜单"""
        item: QtWidgets.QListWidgetItem | None = self.session_list.itemAt(pos)
        if not item:
            return

        session_id: str = item.data(QtCore.Qt.ItemDataRole.UserRole)

        menu: QtWidgets.QMenu = QtWidgets.QMenu(self)

        rename_action: QtGui.QAction = menu.addAction("重命名")
        rename_action.triggered.connect(lambda: self.rename_session(session_id))

        delete_action: QtGui.QAction = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.delete_session(session_id))

        menu.exec(self.session_list.mapToGlobal(pos))

    def rename_session(self, session_id: str) -> None:
        """重命名会话"""
        session: Session | None = self.sessions.get(session_id)
        if not session:
            return

        text, ok = QtWidgets.QInputDialog.getText(self, "重命名会话", "请输入新的会话名称：", text=session.name)

        if ok and text:
            session.name = text
            self.update_list()
            self.save_session(session)

    def delete_session(self, session_id: str) -> None:
        """删除会话"""
        reply: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            self,
            "删除会话",
            "确定要删除该会话吗？此操作不可恢复。",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # 从字典中移除
            self.sessions.pop(session_id, None)

            # 从文件系统中删除
            file_path: Path = SESSION_DIR.joinpath(f"{session_id}.json")
            if file_path.exists():
                file_path.unlink()

            # 如果删除的是当前会话，则切换到另一个会话
            if self.current_id == session_id:
                if self.sessions:
                    self.current_id = next(iter(self.sessions.keys()))
                else:
                    self.new_session()
                self.display_session()

            self.update_list()

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
            ),
            QtWidgets.QMessageBox.StandardButton.Ok
        )

    def open_website(self) -> None:
        """打开官网"""
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://www.github.com/vnpy/vnag"))
