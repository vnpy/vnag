import json
import os
import uuid
from pathlib import Path

from ..constant import Role
from ..engine import AgentEngine
from ..object import Message, Request, Session, ToolSchema

from .qt import (
    QtCore,
    QtGui,
    QtWidgets,
    QtWebEngineCore,
    QtWebEngineWidgets
)
from .worker import StreamWorker
from .base import SESSION_DIR


class HistoryWidget(QtWebEngineWidgets.QWebEngineView):
    """会话历史控件"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)

        # 设置页面背景色为透明，避免首次加载时闪烁
        self.page().setBackgroundColor(QtGui.QColor("transparent"))

        # 流式请求相关状态
        self.full_content: str = ""
        self.msg_id: str = ""

        # 页面加载状态和消息队列
        self.page_loaded: bool = False
        self.message_queue: list[tuple[Role, str]] = []

        # 连接页面加载完成信号
        self.page().loadFinished.connect(self._on_load_finished)

        # 加载本地HTML文件
        current_path: str = os.path.dirname(os.path.abspath(__file__))
        html_path: str = os.path.join(current_path, "resources", "chat.html")
        self.load(QtCore.QUrl.fromLocalFile(html_path))

    def _on_load_finished(self, success: bool) -> None:
        """页面加载完成后的回调"""
        if not success:
            return

        # 设置页面权限，允许复制代码块
        self.page().setFeaturePermission(
            self.page().url(),
            QtWebEngineCore.QWebEnginePage.Feature.ClipboardReadWrite,
            QtWebEngineCore.QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
        )

        # 设置页面加载完成标志，并处理消息队列
        self.page_loaded = True

        for role, content in self.message_queue:
            self.append_message(role, content)

        self.message_queue.clear()

    def clear(self) -> None:
        """清空会话历史"""
        if self.page_loaded:
            self.page().runJavaScript("document.getElementById('history').innerHTML = '';")
        else:
            self.message_queue.clear()

    def append_message(self, role: Role, content: str) -> None:
        """在会话历史组件中添加消息"""
        # 如果页面未加载完成，则将消息添加到消息队列
        if not self.page_loaded:
            self.message_queue.append((role, content))
            return

        # 用户消息，不需要被渲染
        if role is Role.USER:
            escaped_content: str = (
                content.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
            )

            js_content: str = json.dumps(escaped_content)

            self.page().runJavaScript(f"appendUserMessage({js_content})")
        # AI消息，需要被渲染
        elif role is Role.ASSISTANT:
            js_content = json.dumps(content)
            self.page().runJavaScript(f"appendAssistantMessage({js_content})")

    def start_stream(self) -> None:
        """开始新的流式输出"""
        # 清空当前流式输出内容和消息ID
        self.full_content = ""
        self.msg_id = f"msg-{uuid.uuid4().hex}"

        # 调用前端函数，开始新的流式输出
        self.page().runJavaScript(f"startAssistantMessage('{self.msg_id}')")

    def update_stream(self, content_delta: str) -> None:
        """更新流式输出"""
        # 累积收到的内容
        self.full_content += content_delta

        # 将内容转换为JSON字符串
        js_content: str = json.dumps(self.full_content)

        # 调用前端函数，更新流式输出
        self.page().runJavaScript(f"updateAssistantMessage('{self.msg_id}', {js_content})")

    def finish_stream(self) -> str:
        """结束流式输出"""
        # 调用前端函数，结束流式输出
        self.page().runJavaScript(f"finishAssistantMessage('{self.msg_id}')")

        # 返回完整的流式输出内容
        return self.full_content


class SessionWidget(QtWidgets.QWidget):
    """会话控件"""

    def __init__(
        self,
        engine: AgentEngine,
        session: Session,
        models: list[str],
        parent: QtWidgets.QWidget | None = None
    ) -> None:
        """构造函数"""
        super().__init__(parent)

        self.engine: AgentEngine = engine
        self.session: Session = session
        self.models: list[str] = models

        self.init_ui()
        self.display_history()

    def init_ui(self) -> None:
        """初始化UI"""
        desktop: QtCore.QRect = QtWidgets.QApplication.primaryScreen().availableGeometry()

        self.input_widget: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.input_widget.setMaximumHeight(desktop.height() // 4)
        self.input_widget.setPlaceholderText("在这里输入消息，按下回车或者点击按钮发送")
        self.input_widget.installEventFilter(self)

        self.history_widget: HistoryWidget = HistoryWidget()

        button_width: int = 80
        button_height: int = 50

        self.send_button: QtWidgets.QPushButton = QtWidgets.QPushButton("发送")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedWidth(button_width)
        self.send_button.setFixedHeight(button_height)

        self.resend_button: QtWidgets.QPushButton = QtWidgets.QPushButton("重发")
        self.resend_button.clicked.connect(self.resend_round)
        self.resend_button.setFixedWidth(button_width)
        self.resend_button.setFixedHeight(button_height)
        self.resend_button.setEnabled(False)

        self.delete_button: QtWidgets.QPushButton = QtWidgets.QPushButton("删除")
        self.delete_button.clicked.connect(self.delete_round)
        self.delete_button.setFixedWidth(button_width)
        self.delete_button.setFixedHeight(button_height)
        self.delete_button.setEnabled(False)

        completer: QtWidgets.QCompleter = QtWidgets.QCompleter(self.models)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

        self.model_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.model_line.setFixedWidth(300)
        self.model_line.setFixedHeight(50)
        self.model_line.setPlaceholderText("请输入要使用的模型")
        self.model_line.setCompleter(completer)
        self.model_line.setText(self.session.model)
        self.model_line.editingFinished.connect(self.on_model_changed)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(self.model_line)
        hbox.addWidget(self.delete_button)
        hbox.addWidget(self.resend_button)
        hbox.addWidget(self.send_button)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.history_widget)
        vbox.addWidget(self.input_widget)
        vbox.addLayout(hbox)

    def display_history(self) -> None:
        """显示当前会话的聊天记录"""
        self.history_widget.clear()

        for message in self.session.messages:
            self.history_widget.append_message(message.role, message.content)

        self.update_buttons()

    def send_message(self) -> None:
        """发送消息"""
        model: str = self.model_line.text()
        if model not in self.models:
            QtWidgets.QMessageBox.warning(self, "模型名称错误", f"找不到模型：{model}，请检查模型名称是否正确")
            return

        text: str = self.input_widget.toPlainText().strip()
        if not text:
            return
        self.input_widget.clear()

        user_message: Message = Message(role=Role.USER, content=text)
        self.session.messages.append(user_message)
        self.history_widget.append_message(user_message.role, user_message.content)

        self.history_widget.start_stream()

        self.send_button.setEnabled(False)
        self.resend_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        request: Request = Request(
            model=model,
            messages=self.session.messages,
            temperature=0.2
        )

        worker: StreamWorker = StreamWorker(self.engine, request)
        worker.signals.delta.connect(self.on_stream_delta)
        worker.signals.finished.connect(self.on_stream_finished)
        worker.signals.error.connect(self.on_stream_error)

        QtCore.QThreadPool.globalInstance().start(worker)

    def save_session(self) -> None:
        """保存会话"""
        data: dict = self.session.model_dump()
        file_path: Path = SESSION_DIR.joinpath(f"{self.session.id}.json")

        with open(file_path, mode="w+", encoding="UTF-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

    def delete_round(self) -> None:
        """删除最后一轮对话"""
        if not self.session.messages or self.session.messages[-1].role != Role.ASSISTANT:
            return

        self.session.messages.pop()
        self.session.messages.pop()

        self.display_history()
        self.save_session()

    def resend_round(self) -> None:
        """重新发送最后一轮对话"""
        if not self.session.messages or self.session.messages[-1].role != Role.ASSISTANT:
            return

        user_message: Message = self.session.messages[-2]
        self.input_widget.setText(user_message.content)

        self.session.messages.pop()
        self.session.messages.pop()

        self.display_history()
        self.save_session()

    def update_buttons(self) -> None:
        """更新功能按钮状态"""
        if self.session.messages and self.session.messages[-1].role == Role.ASSISTANT:
            self.resend_button.setEnabled(True)
            self.delete_button.setEnabled(True)
        else:
            self.resend_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """事件过滤器"""
        if obj is self.input_widget and event.type() == QtCore.QEvent.Type.KeyPress:
            if (
                event.key() in [QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter]
                and not event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier
            ):
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def on_stream_delta(self, content_delta: str) -> None:
        """处理数据流返回的数据块"""
        self.history_widget.update_stream(content_delta)

    def on_stream_finished(self) -> None:
        """处理数据流结束事件"""
        self.send_button.setEnabled(True)

        full_content: str = self.history_widget.finish_stream()

        if full_content:
            message: Message = Message(role=Role.ASSISTANT, content=full_content)
            self.session.messages.append(message)

        self.save_session()
        self.update_buttons()

    def on_stream_error(self, error_msg: str) -> None:
        """处理数据流错误事件"""
        self.send_button.setEnabled(True)
        QtWidgets.QMessageBox.critical(self, "错误", f"流式请求失败：\n{error_msg}")
        self.update_buttons()

    def on_model_changed(self) -> None:
        """处理模型变更"""
        model: str = self.model_line.text()
        if model in self.models:
            self.session.model = model
            self.save_session()


class ToolsDialog(QtWidgets.QDialog):
    """显示可用工具的对话框"""

    def __init__(self, engine: AgentEngine, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)

        self._engine: AgentEngine = engine

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("工具浏览器")
        self.setMinimumSize(800, 600)

        # 左侧树
        self.tree_widget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget()
        self.tree_widget.setColumnCount(1)
        self.tree_widget.setHeaderLabels(["工具列表"])
        self.tree_widget.itemClicked.connect(self.on_item_clicked)

        # 右侧详情
        self.detail_widget: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.detail_widget.setReadOnly(True)

        # 分割器
        splitter: QtWidgets.QSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self.tree_widget)
        splitter.addWidget(self.detail_widget)
        splitter.setSizes([250, 550])

        # 主布局
        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addWidget(splitter)
        self.setLayout(vbox)

        # 加载数据
        self.populate_tree()

    def populate_tree(self) -> None:
        """填充树"""
        self.tree_widget.clear()

        # 添加本地工具
        local_tools: dict[str, ToolSchema] = self._engine._local_tools
        if local_tools:
            local_root: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(
                self.tree_widget,
                ["本地工具"]
            )

            for schema in local_tools.values():
                item: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(local_root, [schema.name])
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, schema)

            self.tree_widget.expandItem(local_root)

        # 添加MCP工具
        mcp_tools: dict[str, ToolSchema] = self._engine._mcp_tools
        if mcp_tools:
            mcp_root: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(
                self.tree_widget,
                ["MCP工具"]
            )

            for schema in mcp_tools.values():
                item = QtWidgets.QTreeWidgetItem(mcp_root, [schema.name])
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, schema)

            self.tree_widget.expandItem(mcp_root)

    def on_item_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int) -> None:
        """处理项目点击事件"""
        schema: ToolSchema | None = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        if schema:
            text: str = (
                f"[名称]\n{schema.name}\n\n"
                f"[描述]\n{schema.description}\n\n"
                f"[参数]\n{json.dumps(schema.parameters, indent=4, ensure_ascii=False)}"
            )
            self.detail_widget.setText(text)
