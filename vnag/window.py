from pathlib import Path
from typing import cast
import markdown

from PySide6 import QtWidgets, QtGui, QtCore

from .gateway import AgentGateway
from .utility import AGENT_DIR
from . import __version__


class MainWindow(QtWidgets.QMainWindow):
    """主窗口"""

    def __init__(self) -> None:
        """构造函数"""
        super().__init__()

        self.gateway: AgentGateway = AgentGateway()

        self.init_ui()
        self.refresh_display()

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

        self.file_button: QtWidgets.QPushButton = QtWidgets.QPushButton("选择文件")
        self.file_button.clicked.connect(self.select_files)
        self.file_button.setFixedWidth(150)
        self.file_button.setFixedHeight(50)

        self.rag_switch = RagSwitchButton()
        self.rag_switch.toggled.connect(self.toggle_rag_mode)
        self.rag_switch.setChecked(True)  # 默认开启

        self.clear_button: QtWidgets.QPushButton = QtWidgets.QPushButton("清空历史")
        self.clear_button.clicked.connect(self.clear_history)
        self.clear_button.setFixedWidth(300)
        self.clear_button.setFixedHeight(50)

        self.selected_files: list[str] = []
        self.file_label: QtWidgets.QLabel = QtWidgets.QLabel("未选择文件")
        self.file_label.setWordWrap(True)

        self.status_label: QtWidgets.QLabel = QtWidgets.QLabel("尚未初始化AI服务连接")
        self.status_label.setFixedWidth(300)

        hbox1 = QtWidgets.QHBoxLayout()
        hbox1.addWidget(QtWidgets.QLabel("会话历史"))
        hbox1.addStretch()

        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.addWidget(QtWidgets.QLabel("请求输入"))
        hbox2.addStretch()

        file_hbox = QtWidgets.QHBoxLayout()
        file_hbox.addWidget(self.file_button)
        file_hbox.addWidget(self.rag_switch)
        file_hbox.addWidget(self.file_label)
        file_hbox.addStretch()

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
        vbox.addLayout(file_hbox)
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

        session_menu: QtWidgets.QMenu = menu_bar.addMenu("会话")
        session_menu.addAction("新建会话", self.new_session)
        session_menu.addAction("会话列表", self.show_sessions)

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
        """发送消息（纯UI交互）"""
        text: str = self.input_widget.toPlainText().strip()
        if not text:
            return
        self.input_widget.clear()

        self.status_label.setText("AI服务正在思考中...")
        QtWidgets.QApplication.processEvents()

        # 收集UI状态参数
        use_rag = self.rag_switch.isChecked()
        user_files = self.selected_files if self.selected_files else None

        # 所有业务逻辑都交给gateway处理
        content: str | None = self.gateway.send_message(
            message=text,
            use_rag=use_rag,
            user_files=user_files
        )

        self.status_label.setText("AI服务连接已完成初始化")

        # 刷新UI显示
        self.refresh_display()

        # 清理选择的文件
        self.selected_files.clear()
        self.file_label.setText("未选择文件")

    def refresh_display(self) -> None:
        """刷新UI显示（从gateway获取数据）"""
        # 从gateway获取对话历史
        chat_history = self.gateway.get_chat_history()
        
        # 更新UI显示
        self.history_widget.clear()
        for message in chat_history:
            self.append_message(message["role"], message["content"])

    def clear_history(self) -> None:
        """清空会话历史（UI交互）"""
        i: int = QtWidgets.QMessageBox.question(
            self,
            "清空历史",
            "确定要清空历史吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if i == QtWidgets.QMessageBox.StandardButton.Yes:
            # 业务逻辑交给gateway
            self.gateway.clear_history()
            
            # 刷新UI显示
            self.refresh_display()

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

    def select_files(self) -> None:
        """选择文件"""
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "选择要分析的文件",
            "",
            "支持的文档 (*.md *.txt *.pdf *.docx);;所有文件 (*)"
        )
        
        if file_paths:
            self.selected_files = file_paths
            file_names = [Path(fp).name for fp in file_paths]
            self.file_label.setText(f"已选择 {len(file_names)} 个文件: {', '.join(file_names)}")

    def new_session(self) -> None:
        """新建会话"""
        self.session_manager.new_session()
        self.load_history()
        self.status_label.setText("已创建新会话")

    def show_sessions(self) -> None:
        """显示会话列表"""
        sessions = self.session_manager.get_all_sessions()
        
        if not sessions:
            QtWidgets.QMessageBox.information(self, "会话列表", "暂无会话记录")
            return
        
        dialog = SessionListDialog(sessions, self.session_manager, self)
        if dialog.exec_():
            self.load_history()

    def toggle_rag_mode(self, checked: bool) -> None:
        """切换RAG模式"""
        if checked:
            self.status_label.setText("RAG模式已开启")
        else:
            self.status_label.setText("RAG模式已关闭")

    def open_website(self) -> None:
        """打开官网"""
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://www.github.com/vnpy/vnag"))


class RagSwitchButton(QtWidgets.QWidget):
    """RAG开关按钮"""
    
    toggled = QtCore.Signal(bool)
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(120, 50)
        self._checked = False
        
    def setChecked(self, checked: bool) -> None:
        """设置选中状态"""
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(checked)
    
    def isChecked(self) -> bool:
        """获取选中状态"""
        return self._checked
    
    def mousePressEvent(self, event) -> None:
        """鼠标点击事件"""
        if event.button() == QtCore.Qt.LeftButton:
            self.setChecked(not self._checked)
    
    def paintEvent(self, event) -> None:
        """绘制开关"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # 开关背景
        rect = self.rect().adjusted(2, 10, -2, -10)
        radius = rect.height() // 2
        
        if self._checked:
            # 开启状态：绿色背景
            painter.setBrush(QtGui.QBrush(QtGui.QColor(76, 175, 80)))
        else:
            # 关闭状态：灰色背景
            painter.setBrush(QtGui.QBrush(QtGui.QColor(117, 117, 117)))
        
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect, radius, radius)
        
        # 开关圆形按钮
        button_rect = QtCore.QRect()
        button_rect.setSize(QtCore.QSize(rect.height() - 4, rect.height() - 4))
        
        if self._checked:
            # 开启状态：按钮在右侧
            button_rect.moveCenter(QtCore.QPoint(rect.right() - radius, rect.center().y()))
        else:
            # 关闭状态：按钮在左侧
            button_rect.moveCenter(QtCore.QPoint(rect.left() + radius, rect.center().y()))
        
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
        painter.drawEllipse(button_rect)
        
        # 文字标签
        painter.setPen(QtGui.QColor(0, 0, 0))
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        
        text_rect = QtCore.QRect(0, rect.bottom() + 5, self.width(), 15)
        
        if self._checked:
            painter.drawText(text_rect, QtCore.Qt.AlignCenter, "RAG ON")
        else:
            painter.drawText(text_rect, QtCore.Qt.AlignCenter, "RAG OFF")


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


class SessionListDialog(QtWidgets.QDialog):
    """会话列表对话框"""

    def __init__(self, sessions: list[dict], session_manager: SessionManager, parent=None) -> None:
        """构造函数"""
        super().__init__(parent)
        
        self.sessions = sessions
        self.session_manager = session_manager
        
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("会话列表")
        self.setFixedSize(600, 400)
        
        # 会话列表
        self.session_list = QtWidgets.QListWidget()
        
        for session in self.sessions:
            title = session.get('title', '未命名会话')
            created_at = session.get('created_at', '')[:16].replace('T', ' ')
            item_text = f"{title} ({created_at})"
            
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, session['id'])
            self.session_list.addItem(item)
        
        # 按钮
        button_layout = QtWidgets.QHBoxLayout()
        
        switch_button = QtWidgets.QPushButton("切换")
        switch_button.clicked.connect(self.switch_session)
        
        delete_button = QtWidgets.QPushButton("删除")
        delete_button.clicked.connect(self.delete_session)
        
        close_button = QtWidgets.QPushButton("关闭")
        close_button.clicked.connect(self.reject)
        
        button_layout.addWidget(switch_button)
        button_layout.addWidget(delete_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        # 主布局
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(QtWidgets.QLabel("选择要切换的会话："))
        main_layout.addWidget(self.session_list)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)

    def switch_session(self) -> None:
        """切换会话"""
        current_item = self.session_list.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.warning(self, "警告", "请选择一个会话")
            return
        
        session_id = current_item.data(QtCore.Qt.UserRole)
        if self.session_manager.switch_session(session_id):
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(self, "错误", "切换会话失败")

    def delete_session(self) -> None:
        """删除会话"""
        current_item = self.session_list.currentItem()
        if not current_item:
            QtWidgets.QMessageBox.warning(self, "警告", "请选择一个会话")
            return
        
        reply = QtWidgets.QMessageBox.question(
            self, "确认删除", "确定要删除这个会话吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            session_id = current_item.data(QtCore.Qt.UserRole)
            if self.session_manager.delete_session(session_id):
                row = self.session_list.row(current_item)
                self.session_list.takeItem(row)
                QtWidgets.QMessageBox.information(self, "成功", "会话已删除")
