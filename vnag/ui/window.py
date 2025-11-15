from pathlib import Path
from uuid import uuid4
import json

from ..engine import AgentEngine
from ..utility import AGENT_DIR
from ..object import Session
from .. import __version__
from .widget import SessionWidget, ToolsDialog, ModelsDialog
from .qt import QtWidgets, QtGui, QtCore


SESSION_DIR = AGENT_DIR.joinpath("session")
SESSION_DIR.mkdir(parents=True, exist_ok=True)


class MainWindow(QtWidgets.QMainWindow):
    """主窗口"""

    def __init__(self, engine: AgentEngine) -> None:
        """构造函数"""
        super().__init__()

        self.engine: AgentEngine = engine

        self.sessions: dict[str, Session] = {}
        self.session_widgets: dict[str, SessionWidget] = {}
        self.current_id: str = ""
        self.models: list[str] = self.engine.list_models()

        self.init_ui()
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

        # 设置自定义样式表
        stylesheet: str = """
            QListWidget::item {
                padding-top: 10px;
                padding-bottom: 10px;
                padding-left: 10px;
                border-radius: 12px;
            }
            QListWidget::item:hover {
                background-color: rgba(42, 92, 142, 0.3);
                color: white;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
                color: white;
            }
        """
        self.session_list.setStyleSheet(stylesheet)

        self.session_list.itemClicked.connect(self.on_item_clicked)
        self.session_list.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self.on_menu_requested)
        self.session_list.installEventFilter(self)

        left_vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        left_vbox.addWidget(self.session_list)
        left_vbox.addWidget(self.new_button)

        left_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        left_widget.setLayout(left_vbox)
        left_widget.setFixedWidth(300)

        # 右侧聊天相关
        self.stacked_widget: QtWidgets.QStackedWidget = QtWidgets.QStackedWidget()

        # 主布局
        main_hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        main_hbox.addWidget(left_widget)
        main_hbox.addWidget(self.stacked_widget)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_hbox)
        self.setCentralWidget(central_widget)

    def init_menu(self) -> None:
        """初始化菜单"""
        menu_bar: QtWidgets.QMenuBar = self.menuBar()

        sys_menu: QtWidgets.QMenu = menu_bar.addMenu("系统")
        sys_menu.addAction("退出", self.close)

        function_menu: QtWidgets.QMenu = menu_bar.addMenu("功能")
        function_menu.addAction("新建会话", self.new_session)
        function_menu.addAction("查看工具", self.show_tools)
        function_menu.addAction("查看模型", self.show_models)

        help_menu: QtWidgets.QMenu = menu_bar.addMenu("帮助")
        help_menu.addAction("官网", self.open_website)
        help_menu.addAction("关于", self.show_about)

    def show_tools(self) -> None:
        """显示工具"""
        dialog: ToolsDialog = ToolsDialog(self.engine, self)
        dialog.exec()

    def show_models(self) -> None:
        """显示模型"""
        dialog: ModelsDialog = ModelsDialog(self.engine, self)
        dialog.exec()

    def load_sessions(self) -> None:
        """加载所有会话"""
        self.sessions.clear()
        self.session_widgets.clear() # Clear existing widgets

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

                widget: SessionWidget = SessionWidget(self.engine, session, self.models)
                self.stacked_widget.addWidget(widget)
                self.session_widgets[session.id] = widget

        if not self.sessions:
            self.new_session()
        else:
            self.current_id = next(iter(self.sessions.keys()))
            self.switch_session(self.current_id)

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

    def new_session(self) -> None:
        """创建新会话"""
        session: Session = Session(
            id=str(uuid4()),
            name="默认会话"
        )
        self.sessions[session.id] = session

        self.current_id = session.id

        widget: SessionWidget = SessionWidget(self.engine, session, self.models)
        widget.save_session()

        self.stacked_widget.addWidget(widget)
        self.session_widgets[session.id] = widget

        self.update_list()
        self.switch_session(session.id)

    def switch_session(self, session_id: str) -> None:
        """根据ID切换会话"""
        self.current_id = session_id

        widget: SessionWidget = self.session_widgets[session_id]
        self.stacked_widget.setCurrentWidget(widget)

    def rename_session(self, session_id: str) -> None:
        """重命名会话"""
        session: Session | None = self.sessions.get(session_id)
        if not session:
            return

        text, ok = QtWidgets.QInputDialog.getText(self, "重命名会话", "请输入新的会话名称：", text=session.name)

        if ok and text:
            session.name = text
            self.update_list()

            widget: SessionWidget = self.session_widgets[session_id]
            widget.save_session()

    def delete_session(self, session_id: str) -> None:
        """删除会话"""
        reply: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            self,
            "删除会话",
            "确定要删除该会话吗？此操作不可恢复。",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.Yes,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # 从字典中移除
            self.sessions.pop(session_id, None)

            # 移除对应的控件
            widget: SessionWidget = self.session_widgets.pop(session_id, None)
            if widget:
                self.stacked_widget.removeWidget(widget)
                widget.deleteLater()

            # 从文件系统中删除
            file_path: Path = SESSION_DIR.joinpath(f"{session_id}.json")
            if file_path.exists():
                file_path.unlink()

            # 如果删除的是当前会话，则切换到另一个会话
            if self.current_id == session_id:
                if self.sessions:
                    self.current_id = next(iter(self.sessions.keys()))
                    self.switch_session(self.current_id)
                else:
                    self.new_session()

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

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """事件过滤器"""
        if obj is self.session_list and event.type() == QtCore.QEvent.Type.KeyPress:
            if event.key() == QtCore.Qt.Key.Key_Delete:
                item: QtWidgets.QListWidgetItem = self.session_list.currentItem()
                if item:
                    self.delete_session(item.data(QtCore.Qt.ItemDataRole.UserRole))
                    return True

        return super().eventFilter(obj, event)

    def on_item_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        """处理列表项点击事件"""
        session_id: str = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.switch_session(session_id)

    def on_menu_requested(self, pos: QtCore.QPoint) -> None:
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
