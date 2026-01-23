import json
import os
import uuid
from collections import defaultdict
from collections.abc import Callable
from typing import cast, NamedTuple

from ..constant import Role
from ..engine import AgentEngine, default_profile
from ..object import ToolSchema
from ..agent import Profile, TaskAgent
from ..gateways import GATEWAY_CLASSES, get_gateway_class

from .qt import (
    QtCore,
    QtGui,
    QtWidgets,
    QtWebEngineCore,
    QtWebEngineWidgets
)
from .worker import StreamWorker
from .setting import (
    load_favorite_models,
    save_favorite_models,
    load_zoom_factor,
    save_zoom_factor,
    load_gateway_type,
    save_gateway_type,
    get_setting
)
from ..factory import (
    load_gateway_setting,
    save_gateway_setting,
    load_embedder_setting,
    save_embedder_setting,
    EMBEDDER_TYPES,
    EMBEDDER_DEFAULTS,
    load_knowledge_metadata,
    save_knowledge_metadata,
    delete_knowledge_metadata,
    list_knowledge_bases,
    create_knowledge_base,
    get_embedder_for_knowledge,
)


class QueuedMessage(NamedTuple):
    """消息队列中的消息结构"""
    role: Role
    content: str
    thinking: str
    input_tokens: int
    output_tokens: int


class HistoryWidget(QtWebEngineWidgets.QWebEngineView):
    """会话历史控件"""

    def __init__(self,  profile_name: str, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)

        self.profile_name: str = profile_name

        # 设置页面背景色为透明，避免首次加载时闪烁
        self.page().setBackgroundColor(QtGui.QColor("transparent"))

        # 流式请求相关状态
        self.full_content: str = ""
        self.full_thinking: str = ""
        self.msg_id: str = ""
        self.last_type: str = ""

        # 流式请求的 Token 使用量
        self.stream_input_tokens: int = 0
        self.stream_output_tokens: int = 0

        # 页面加载状态和消息队列
        self.page_loaded: bool = False
        self.message_queue: list[QueuedMessage] = []

        # 连接页面加载完成信号
        self.page().loadFinished.connect(self._on_load_finished)

        # 连接权限请求信号，处理剪贴板权限
        self.page().permissionRequested.connect(self._on_permission_requested)

        # 加载并应用保存的缩放倍数
        zoom_factor: float = load_zoom_factor()
        self.setZoomFactor(zoom_factor)

        # 连接缩放变化信号，自动保存缩放倍数
        self.page().zoomFactorChanged.connect(self._on_zoom_factor_changed)

        # 加载本地HTML文件
        current_path: str = os.path.dirname(os.path.abspath(__file__))
        html_path: str = os.path.join(current_path, "resources", "chat.html")
        self.load(QtCore.QUrl.fromLocalFile(html_path))

    def _on_permission_requested(self, permission: QtWebEngineCore.QWebEnginePermission) -> None:
        """处理权限请求，自动授予剪贴板权限"""
        if permission.permissionType() == QtWebEngineCore.QWebEnginePermission.PermissionType.ClipboardReadWrite:
            permission.grant()

    def _on_zoom_factor_changed(self, zoom_factor: float) -> None:
        """处理缩放倍数变化，自动保存"""
        save_zoom_factor(zoom_factor)

    def _on_load_finished(self, success: bool) -> None:
        """页面加载完成后的回调"""
        if not success:
            return

        self._show_welcome_message()

        # 设置页面加载完成标志，并处理消息队列
        self.page_loaded = True

        for msg in self.message_queue:
            self.append_message(
                msg.role,
                msg.content,
                msg.thinking,
                msg.input_tokens,
                msg.output_tokens
            )

        self.message_queue.clear()

    def _show_welcome_message(self) -> None:
        """显示助手欢迎消息"""
        js_content: str = json.dumps(f"你好，我是{self.profile_name}，有什么能帮上你的吗？")
        js_name: str = json.dumps(self.profile_name)
        self.page().runJavaScript(f"appendAssistantMessage({js_content}, {js_name})")

    def clear(self) -> None:
        """清空会话历史"""
        if self.page_loaded:
            self.page().runJavaScript("document.getElementById('history').innerHTML = '';")
            self._show_welcome_message()
        else:
            self.message_queue.clear()

    def append_message(
        self,
        role: Role,
        content: str,
        thinking: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> None:
        """在会话历史组件中添加消息"""
        # 如果页面未加载完成，则将消息添加到消息队列
        if not self.page_loaded:
            self.message_queue.append(QueuedMessage(
                role=role,
                content=content,
                thinking=thinking,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            ))
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
            js_name: str = json.dumps(self.profile_name)
            js_thinking: str = json.dumps(thinking)
            self.page().runJavaScript(
                f"appendAssistantMessage({js_content}, {js_name}, {js_thinking}, "
                f"{input_tokens}, {output_tokens})"
            )

    def start_stream(self) -> None:
        """开始新的流式输出"""
        # 清空当前流式输出内容和消息ID
        self.full_content = ""
        self.full_thinking = ""
        self.msg_id = f"msg-{uuid.uuid4().hex}"
        self.last_type = ""

        # 重置 Token 使用量统计
        self.stream_input_tokens = 0
        self.stream_output_tokens = 0

        # 调用前端函数，开始新的流式输出
        js_name: str = json.dumps(self.profile_name)
        self.page().runJavaScript(f"startAssistantMessage('{self.msg_id}', {js_name})")

    def update_stream(self, content_delta: str) -> None:
        """更新流式输出（content 内容）"""
        # 记录当前类型为 content
        self.last_type = "content"

        # 累积收到的内容
        self.full_content += content_delta

        # 将内容转换为JSON字符串
        js_content: str = json.dumps(self.full_content)

        # 调用前端函数，更新流式输出
        self.page().runJavaScript(f"updateAssistantMessage('{self.msg_id}', {js_content})")

    def update_thinking(self, thinking_delta: str) -> None:
        """更新流式输出（thinking 内容）"""
        # 如果之前输出过其他类型的内容（如content），且已有thinking内容，则换行
        if self.last_type and self.last_type != "thinking" and self.full_thinking:
            self.full_thinking += "\n\n"

        # 记录当前类型为 thinking
        self.last_type = "thinking"

        # 累积收到的 thinking 内容
        self.full_thinking += thinking_delta

        # 将内容转换为JSON字符串
        js_thinking: str = json.dumps(self.full_thinking)

        # 调用前端函数，更新 thinking 输出
        self.page().runJavaScript(f"updateThinking('{self.msg_id}', {js_thinking})")

    def update_usage(self, input_tokens: int, output_tokens: int) -> None:
        """更新流式输出的 Token 使用量"""
        self.stream_input_tokens = input_tokens
        self.stream_output_tokens = output_tokens

    def finish_stream(self) -> str:
        """结束流式输出"""
        # 调用前端函数，结束流式输出（传入 Token 使用量）
        self.page().runJavaScript(
            f"finishAssistantMessage('{self.msg_id}', "
            f"{self.stream_input_tokens}, {self.stream_output_tokens})"
        )

        # 返回完整的流式输出内容
        return self.full_content


class AgentWidget(QtWidgets.QWidget):
    """会话控件"""

    def __init__(
        self,
        engine: AgentEngine,
        agent: TaskAgent,
        update_list: Callable[[], None],
        parent: QtWidgets.QWidget | None = None
    ) -> None:
        """构造函数"""
        super().__init__(parent)

        self.engine: AgentEngine = engine
        self.agent: TaskAgent = agent
        self.worker: StreamWorker | None = None
        self.update_list: Callable[[], None] = update_list

        self.init_ui()
        self.load_favorite_models()
        self.display_history()

    def init_ui(self) -> None:
        """初始化UI"""
        desktop: QtCore.QRect = QtWidgets.QApplication.primaryScreen().availableGeometry()

        self.input_widget: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.input_widget.setMaximumHeight(desktop.height() // 4)
        self.input_widget.setPlaceholderText("在这里输入消息，按下回车或者点击按钮发送")
        self.input_widget.setAcceptRichText(False)
        self.input_widget.installEventFilter(self)

        self.history_widget: HistoryWidget = HistoryWidget(profile_name=self.agent.profile.name)

        button_width: int = 80
        button_height: int = 50

        self.send_button: QtWidgets.QPushButton = QtWidgets.QPushButton("发送")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedWidth(button_width)
        self.send_button.setFixedHeight(button_height)

        self.stop_button: QtWidgets.QPushButton = QtWidgets.QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_stream)
        self.stop_button.setFixedWidth(button_width)
        self.stop_button.setFixedHeight(button_height)
        self.stop_button.setVisible(False)

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

        self.model_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.model_combo.setFixedWidth(400)
        self.model_combo.setFixedHeight(50)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(self.model_combo)
        hbox.addWidget(self.delete_button)
        hbox.addWidget(self.resend_button)
        hbox.addWidget(self.stop_button)
        hbox.addWidget(self.send_button)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.history_widget)
        vbox.addWidget(self.input_widget)
        vbox.addLayout(hbox)

    def display_history(self) -> None:
        """显示当前会话的聊天记录"""
        self.history_widget.clear()

        assistant_content: str = ""
        assistant_thinking: str = ""
        assistant_input_tokens: int = 0
        assistant_output_tokens: int = 0
        last_type: str = ""

        for message in self.agent.messages:
            # 系统消息，不显示
            if message.role is Role.SYSTEM:
                continue
            # 用户消息
            elif message.role is Role.USER:
                # 有内容
                if message.content:
                    # 如果助手内容不为空，则先显示助手内容（包含之前的工具调用记录）
                    if assistant_content:
                        self.history_widget.append_message(
                            Role.ASSISTANT,
                            assistant_content,
                            assistant_thinking,
                            assistant_input_tokens,
                            assistant_output_tokens
                        )
                        assistant_content = ""
                        assistant_thinking = ""
                        assistant_input_tokens = 0
                        assistant_output_tokens = 0
                        last_type = ""

                    # 显示用户内容
                    self.history_widget.append_message(Role.USER, message.content)
                # 没有内容（工具调用结果返回），则跳过
                else:
                    continue
            # 助手消息
            elif message.role is Role.ASSISTANT:
                # 累积 thinking 内容
                if message.thinking:
                    # 如果之前输出过其他类型的内容（如content），且已有thinking内容，则换行
                    if last_type and last_type != "thinking" and assistant_thinking:
                        assistant_thinking += "\n\n"

                    assistant_thinking += message.thinking
                    last_type = "thinking"

                # 有内容，则添加到助手内容
                if message.content:
                    assistant_content += message.content
                    last_type = "content"

                # 有工具调用请求，则记录调用工具名称
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        assistant_content += f"\n\n[执行工具: {tool_call.name}]\n\n"
                    last_type = "tool"

                # 累积 usage 数据
                assistant_input_tokens += message.usage.input_tokens
                assistant_output_tokens += message.usage.output_tokens

        # 显示消息
        if assistant_content:
            self.history_widget.append_message(
                Role.ASSISTANT,
                assistant_content,
                assistant_thinking,
                assistant_input_tokens,
                assistant_output_tokens
            )

        self.update_buttons()

    def send_message(self) -> None:
        """发送消息"""
        # 检查是否已配置 AI Gateway
        gateway_type: str = get_setting("gateway_type")
        if not gateway_type:
            QtWidgets.QMessageBox.warning(
                self,
                "AI服务未配置",
                "请先在【菜单栏-功能-AI服务配置】配置AI服务"
            )
            return

        model: str = self.model_combo.currentText()
        if not model:
            QtWidgets.QMessageBox.warning(
                self,
                "模型未选择",
                "请先在【菜单栏-功能-模型浏览器】配置常用模型"
            )
            return

        text: str = self.input_widget.toPlainText().strip()
        if not text:
            return
        self.input_widget.clear()

        # 将用户输入添加到UI历史
        self.history_widget.append_message(Role.USER, text)
        self.history_widget.start_stream()

        self.send_button.setVisible(False)
        self.stop_button.setVisible(True)
        self.resend_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        worker: StreamWorker = StreamWorker(self.agent, text)
        worker.signals.delta.connect(self.on_stream_delta)
        worker.signals.thinking.connect(self.on_stream_thinking)
        worker.signals.usage.connect(self.on_stream_usage)
        worker.signals.finished.connect(self.on_stream_finished)
        worker.signals.error.connect(self.on_stream_error)
        worker.signals.title.connect(self.on_title_generated)

        self.worker = worker
        QtCore.QThreadPool.globalInstance().start(worker)

    def stop_stream(self) -> None:
        """停止当前流式请求"""
        if self.worker:
            self.worker.stop()

    def delete_round(self) -> None:
        """删除最后一轮对话"""
        self.agent.delete_round()
        self.display_history()

    def resend_round(self) -> None:
        """重新发送最后一轮对话"""
        prompt: str = self.agent.resend_round()

        if prompt:
            self.input_widget.setText(prompt)

        self.display_history()

    def update_buttons(self) -> None:
        """更新功能按钮状态"""
        if self.agent.messages and self.agent.messages[-1].role == Role.ASSISTANT:
            self.resend_button.setEnabled(True)
            self.delete_button.setEnabled(True)
        else:
            self.resend_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """事件过滤器"""
        if obj is self.input_widget and event.type() == QtCore.QEvent.Type.KeyPress:
            # 将 QEvent 转换为 QKeyEvent
            key_event: QtGui.QKeyEvent = cast(QtGui.QKeyEvent, event)
            if (
                key_event.key() in [QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter]
                and not key_event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier
            ):
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def on_stream_delta(self, content_delta: str) -> None:
        """处理数据流返回的 content 数据块"""
        self.history_widget.update_stream(content_delta)

    def on_stream_thinking(self, thinking_delta: str) -> None:
        """处理数据流返回的 thinking 数据块"""
        self.history_widget.update_thinking(thinking_delta)

    def on_stream_usage(self, input_tokens: int, output_tokens: int) -> None:
        """处理数据流返回的 Token 使用量"""
        self.history_widget.update_usage(input_tokens, output_tokens)

    def on_stream_finished(self) -> None:
        """处理数据流结束事件"""
        self.worker = None

        self.history_widget.finish_stream()
        self.update_buttons()

        self.send_button.setVisible(True)
        self.stop_button.setVisible(False)

    def on_stream_error(self, error_msg: str) -> None:
        """处理数据流错误事件"""
        self.worker = None

        self.history_widget.finish_stream()
        self.update_buttons()

        self.send_button.setVisible(True)
        self.stop_button.setVisible(False)

        dialog = ErrorDialog("流式请求失败：", error_msg, self)
        dialog.exec()

    def on_title_generated(self, title: str) -> None:
        """处理标题生成完成"""
        self.agent.rename(title)

        # 通知主窗口更新列表
        self.update_list()

    def on_model_changed(self, model: str) -> None:
        """处理模型变更"""
        if model:
            self.agent.set_model(model)

    def load_favorite_models(self) -> None:
        """加载常用模型"""
        current_text: str = self.model_combo.currentText()

        # 阻止信号重复触发on_model_changed
        self.model_combo.blockSignals(True)

        self.model_combo.clear()
        favorite_models: list[str] = load_favorite_models()

        # 仅显示当前网关支持的模型
        available_models: set[str] = set(self.engine.list_models())
        favorite_models = [m for m in favorite_models if m in available_models]

        self.model_combo.addItems(favorite_models)

        # 恢复之前的选项
        if current_text in favorite_models:
            self.model_combo.setCurrentText(current_text)
        elif self.agent.model in favorite_models:
            self.model_combo.setCurrentText(self.agent.model)
        elif favorite_models:
            self.model_combo.setCurrentIndex(0)

        self.model_combo.blockSignals(False)

        # 如果模型选择在刷新后发生了变化，则手动同步到Agent
        if self.model_combo.currentText() != self.agent.model:
            self.on_model_changed(self.model_combo.currentText())


class ErrorDialog(QtWidgets.QDialog):
    """可滚动、可复制的错误信息对话框"""

    def __init__(
        self,
        title: str,
        message: str,
        parent: QtWidgets.QWidget | None = None
    ) -> None:
        """构造函数"""
        super().__init__(parent)

        self.message: str = message

        self.setWindowTitle("错误")
        self.setMinimumSize(800, 600)

        layout = QtWidgets.QVBoxLayout(self)

        # 标题标签
        label = QtWidgets.QLabel(title)
        layout.addWidget(label)

        # 可滚动、可复制的文本框
        text_edit = QtWidgets.QPlainTextEdit()
        text_edit.setPlainText(message)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        # 按钮区域
        button_layout = QtWidgets.QHBoxLayout()

        copy_button = QtWidgets.QPushButton("复制")
        copy_button.clicked.connect(self.copy_message)
        button_layout.addWidget(copy_button)

        close_button = QtWidgets.QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def copy_message(self) -> None:
        """复制错误信息到剪贴板"""
        QtWidgets.QApplication.clipboard().setText(self.message)


class ProfileDialog(QtWidgets.QDialog):
    """智能体管理界面"""

    def __init__(self, engine: AgentEngine, parent: QtWidgets.QWidget | None = None):
        """"""
        super().__init__(parent)

        self.engine: AgentEngine = engine
        self.profiles: dict[str, Profile] = {}

        self.init_ui()
        self.load_profiles()

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle("智能体配置")
        self.setMinimumSize(1000, 600)

        # 左侧列表
        self.profile_list: QtWidgets.QListWidget = QtWidgets.QListWidget()
        self.profile_list.itemClicked.connect(self.on_profile_selected)

        # 右侧表单
        self.name_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.prompt_text: QtWidgets.QTextEdit = QtWidgets.QTextEdit()

        # 温度
        self.temperature_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        temperature_validator: QtGui.QDoubleValidator = QtGui.QDoubleValidator(0.0, 2.0, 1)
        temperature_validator.setNotation(QtGui.QDoubleValidator.Notation.StandardNotation)
        self.temperature_line.setValidator(temperature_validator)
        self.temperature_line.setPlaceholderText("可选，0.0-2.0之间，1位小数")

        # 最大Token数
        self.tokens_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        max_tokens_validator: QtGui.QIntValidator = QtGui.QIntValidator(1, 10_000_000)
        self.tokens_line.setValidator(max_tokens_validator)
        self.tokens_line.setPlaceholderText("可选，正整数")

        self.iterations_spin: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.iterations_spin.setRange(1, 200)
        self.iterations_spin.setSingleStep(1)
        self.iterations_spin.setValue(10)

        # 工具列表
        self.tool_tree: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget()
        self.tool_tree.setHeaderHidden(True)
        self.populate_tree()

        # 中间区域表单
        settings_form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        settings_form.addRow("配置名称", self.name_line)
        settings_form.addRow("系统提示词", self.prompt_text)
        settings_form.addRow("温度", self.temperature_line)
        settings_form.addRow("最大Token数", self.tokens_line)
        settings_form.addRow("最大迭代次数", self.iterations_spin)

        middle_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        middle_widget.setLayout(settings_form)

        # 三栏分割器
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.profile_list)
        splitter.addWidget(middle_widget)
        splitter.addWidget(self.tool_tree)
        splitter.setSizes([200, 500, 300])

        # 底部按钮
        self.add_button: QtWidgets.QPushButton = QtWidgets.QPushButton("新建")
        self.add_button.clicked.connect(self.new_profile)

        self.save_button: QtWidgets.QPushButton = QtWidgets.QPushButton("保存")
        self.save_button.clicked.connect(self.save_profile)

        self.delete_button: QtWidgets.QPushButton = QtWidgets.QPushButton("删除")
        self.delete_button.clicked.connect(self.delete_profile)

        buttons_hbox = QtWidgets.QHBoxLayout()
        buttons_hbox.addStretch()
        buttons_hbox.addWidget(self.add_button)
        buttons_hbox.addWidget(self.save_button)
        buttons_hbox.addWidget(self.delete_button)

        # 主布局
        main_vbox = QtWidgets.QVBoxLayout()
        main_vbox.addWidget(splitter)
        main_vbox.addLayout(buttons_hbox)
        self.setLayout(main_vbox)

    def load_profiles(self) -> None:
        """加载配置"""
        self.profile_list.clear()

        self.profiles = {p.name: p for p in self.engine.get_all_profiles()}

        for profile in self.profiles.values():
            item: QtWidgets.QListWidgetItem = QtWidgets.QListWidgetItem(profile.name, self.profile_list)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, profile.name)

    def populate_tree(self) -> None:
        """填充工具树"""
        self.tool_tree.clear()

        # 添加本地工具
        local_tools: dict[str, ToolSchema] = self.engine.get_local_schemas()
        if local_tools:
            local_root = QtWidgets.QTreeWidgetItem(self.tool_tree, ["本地工具"])

            module_tools: dict[str, list[ToolSchema]] = defaultdict(list)
            for schema in local_tools.values():
                module, _ = schema.name.split("_", 1)
                module_tools[module].append(schema)

            for module, schemas in sorted(module_tools.items()):
                module_item = QtWidgets.QTreeWidgetItem(local_root, [module])
                module_item.setFlags(
                    module_item.flags()
                    | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                    | QtCore.Qt.ItemFlag.ItemIsAutoTristate
                )
                module_item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

                for schema in sorted(schemas, key=lambda s: s.name):
                    tool_item = QtWidgets.QTreeWidgetItem(module_item, [schema.name])
                    tool_item.setFlags(tool_item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                    tool_item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
                    tool_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, schema.name)

        # 添加MCP工具
        mcp_tools: dict[str, ToolSchema] = self.engine.get_mcp_schemas()
        if mcp_tools:
            mcp_root = QtWidgets.QTreeWidgetItem(self.tool_tree, ["MCP工具"])

            server_tools: dict[str, list[ToolSchema]] = defaultdict(list)
            for schema in mcp_tools.values():
                server, _ = schema.name.split("_", 1)
                server_tools[server].append(schema)

            for server, schemas in sorted(server_tools.items()):
                server_item = QtWidgets.QTreeWidgetItem(mcp_root, [server])
                server_item.setFlags(
                    server_item.flags()
                    | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                    | QtCore.Qt.ItemFlag.ItemIsAutoTristate
                )
                server_item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

                for schema in sorted(schemas, key=lambda s: s.name):
                    tool_item = QtWidgets.QTreeWidgetItem(server_item, [schema.name])
                    tool_item.setFlags(tool_item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                    tool_item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
                    tool_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, schema.name)

        self.tool_tree.expandAll()

    def new_profile(self) -> None:
        """新建智能体配置"""
        self.profile_list.clearSelection()

        self.name_line.setReadOnly(False)
        self.name_line.clear()
        self.prompt_text.clear()

        self.temperature_line.clear()
        self.tokens_line.clear()
        self.iterations_spin.setValue(10)

        iterator = QtWidgets.QTreeWidgetItemIterator(self.tool_tree)
        while iterator.value():
            item = iterator.value()
            item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
            iterator += 1

        self.name_line.setFocus()

    def save_profile(self) -> None:
        """保存智能体配置"""
        name: str = self.name_line.text()
        if not name:
            QtWidgets.QMessageBox.warning(self, "错误", "名称不能为空！")
            return

        if name == default_profile.name:
            QtWidgets.QMessageBox.warning(self, "错误", "默认智能体配置不能修改！")
            return

        prompt: str = self.prompt_text.toPlainText()
        if not prompt:
            QtWidgets.QMessageBox.warning(self, "错误", "系统提示词不能为空！")
            return

        temp_text: str = self.temperature_line.text()
        temperature: float | None = float(temp_text) if temp_text else None

        max_tokens_text: str = self.tokens_line.text()
        max_tokens: int | None = int(max_tokens_text) if max_tokens_text else None

        max_iterations: int = self.iterations_spin.value()

        selected_tools: list[str] = []
        iterator = QtWidgets.QTreeWidgetItemIterator(self.tool_tree)
        while iterator.value():
            item: QtWidgets.QTreeWidgetItem = iterator.value()
            if item.checkState(0) == QtCore.Qt.CheckState.Checked:
                tool_name: str = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if tool_name:  # 工具项，不是分类
                    selected_tools.append(tool_name)
            iterator += 1

        # 更新现有配置
        if name in self.profiles:
            profile: Profile = self.profiles[name]

            profile.prompt = prompt
            profile.tools = selected_tools
            profile.temperature = temperature
            profile.max_tokens = max_tokens
            profile.max_iterations = max_iterations

            self.engine.update_profile(profile)
        # 创建新配置
        else:
            profile = Profile(
                name=name,
                prompt=prompt,
                tools=selected_tools,
                temperature=temperature,
                max_tokens=max_tokens,
                max_iterations=max_iterations,
            )
            self.engine.add_profile(profile)

        self.load_profiles()

        QtWidgets.QMessageBox.information(self, "成功", f"{name} 智能体配置已保存！", QtWidgets.QMessageBox.StandardButton.Ok)

    def delete_profile(self) -> None:
        """删除智能体配置"""
        item: QtWidgets.QListWidgetItem | None = self.profile_list.currentItem()
        if not item:
            return

        profile_name: str = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if profile_name == default_profile.name:
            QtWidgets.QMessageBox.warning(self, "错误", "默认智能体配置不能删除！")
            return

        # 检查智能体依赖
        agents: list[TaskAgent] = self.engine.get_all_agents()

        dependent_agents: list[str] = [a.name for a in agents if a.profile.name == profile_name]

        if dependent_agents:
            msg: str = "无法删除，以下智能体正在使用该配置: \n" + "\n".join(dependent_agents)
            QtWidgets.QMessageBox.warning(self, "删除失败", msg)
            return

        reply: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.question(
            self,
            "删除配置",
            "确定要删除该智能体配置吗？",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.engine.delete_profile(profile_name)
            self.load_profiles()
            self.new_profile()

    def on_profile_selected(self, item: QtWidgets.QListWidgetItem) -> None:
        """显示选中智能体配置"""
        self.name_line.setReadOnly(True)

        profile_name: str = item.data(QtCore.Qt.ItemDataRole.UserRole)
        profile: Profile = self.profiles[profile_name]

        self.name_line.setText(profile.name)
        self.prompt_text.setPlainText(profile.prompt)

        if profile.temperature is not None:
            self.temperature_line.setText(str(profile.temperature))
        else:
            self.temperature_line.clear()

        if profile.max_tokens is not None:
            self.tokens_line.setText(str(profile.max_tokens))
        else:
            self.tokens_line.clear()

        self.iterations_spin.setValue(profile.max_iterations)

        # 只操作叶子节点（工具项），让AutoTristate自动更新父节点
        iterator = QtWidgets.QTreeWidgetItemIterator(self.tool_tree)
        while iterator.value():
            tool_item: QtWidgets.QTreeWidgetItem = iterator.value()
            tool_name = tool_item.data(0, QtCore.Qt.ItemDataRole.UserRole)

            # 只处理有UserRole数据的叶子节点（工具项）
            if tool_name:
                if tool_name in profile.tools:
                    tool_item.setCheckState(0, QtCore.Qt.CheckState.Checked)
                else:
                    tool_item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

            iterator += 1


class ToolDialog(QtWidgets.QDialog):
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
        headers: list[str] = ["分类", "模块", "工具"]
        self.tree_widget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget()
        self.tree_widget.setColumnCount(len(headers))
        self.tree_widget.setHeaderLabels(headers)
        self.tree_widget.itemClicked.connect(self.on_item_clicked)
        self.tree_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)

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
        local_tools: dict[str, ToolSchema] = self._engine.get_local_schemas()
        if local_tools:
            local_root: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(
                self.tree_widget,
                ["本地工具", "", ""]
            )

            module_tools: dict[str, list[ToolSchema]] = defaultdict(list)
            for schema in local_tools.values():
                module, _ = schema.name.split("_", 1)
                module_tools[module].append(schema)

            for module, schemas in sorted(module_tools.items()):
                module_item: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(
                    local_root,
                    ["", module, ""]
                )
                for schema in sorted(schemas, key=lambda s: s.name):
                    _, name = schema.name.split("_", 1)
                    item: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(
                        module_item,
                        ["", "", name]
                    )
                    item.setData(0, QtCore.Qt.ItemDataRole.UserRole, schema)

            self.tree_widget.expandItem(local_root)

        # 添加MCP工具
        mcp_tools: dict[str, ToolSchema] = self._engine.get_mcp_schemas()
        if mcp_tools:
            mcp_root: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(
                self.tree_widget,
                ["MCP工具", "", ""]
            )

            server_tools: dict[str, list[ToolSchema]] = defaultdict(list)
            for schema in mcp_tools.values():
                server, _ = schema.name.split("_", 1)
                server_tools[server].append(schema)

            for server, schemas in sorted(server_tools.items()):
                server_item: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(
                    mcp_root,
                    ["", server, ""]
                )
                for schema in sorted(schemas, key=lambda s: s.name):
                    _, name = schema.name.split("_", 1)
                    item = QtWidgets.QTreeWidgetItem(
                        server_item,
                        ["", "", name]
                    )
                    item.setData(0, QtCore.Qt.ItemDataRole.UserRole, schema)

            self.tree_widget.expandItem(mcp_root)

        for i in range(self.tree_widget.columnCount()):
            self.tree_widget.resizeColumnToContents(i)

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

    def show_context_menu(self, pos: QtCore.QPoint) -> None:
        """显示右键菜单"""
        menu: QtWidgets.QMenu = QtWidgets.QMenu(self)

        expand_action: QtGui.QAction = menu.addAction("全部展开")
        expand_action.triggered.connect(self.tree_widget.expandAll)

        collapse_action: QtGui.QAction = menu.addAction("全部折叠")
        collapse_action.triggered.connect(self.tree_widget.collapseAll)

        menu.exec(self.tree_widget.viewport().mapToGlobal(pos))


class ModelDialog(QtWidgets.QDialog):
    """显示可用模型的对话框"""

    def __init__(self, engine: AgentEngine, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)

        self._engine: AgentEngine = engine

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("模型浏览器")
        self.setMinimumSize(800, 600)

        # 左侧所有模型树
        headers: list[str] = ["厂商", "模型"]
        self.tree_widget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget()
        self.tree_widget.setColumnCount(len(headers))
        self.tree_widget.setHeaderLabels(headers)
        self.tree_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget.itemDoubleClicked.connect(self.add_model)

        # 右侧常用模型列表
        self.favorite_list: QtWidgets.QListWidget = QtWidgets.QListWidget()
        self.favorite_list.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.favorite_list.customContextMenuRequested.connect(self.show_favorite_context_menu)

        # 中间按钮
        add_button: QtWidgets.QPushButton = QtWidgets.QPushButton(">")
        add_button.clicked.connect(self.add_model)
        add_button.setFixedWidth(40)

        remove_button: QtWidgets.QPushButton = QtWidgets.QPushButton("<")
        remove_button.clicked.connect(self.remove_model)
        remove_button.setFixedWidth(40)

        up_button: QtWidgets.QPushButton = QtWidgets.QPushButton("↑")
        up_button.clicked.connect(self.move_model_up)
        up_button.setFixedWidth(40)

        down_button: QtWidgets.QPushButton = QtWidgets.QPushButton("↓")
        down_button.clicked.connect(self.move_model_down)
        down_button.setFixedWidth(40)

        button_vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        button_vbox.addStretch()
        button_vbox.addWidget(add_button)
        button_vbox.addWidget(remove_button)
        button_vbox.addSpacing(20)
        button_vbox.addWidget(up_button)
        button_vbox.addWidget(down_button)
        button_vbox.addStretch()

        # 分割器
        splitter: QtWidgets.QSplitter = QtWidgets.QSplitter()
        splitter.addWidget(self.tree_widget)

        button_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        button_widget.setLayout(button_vbox)
        button_widget.setFixedWidth(60)
        splitter.addWidget(button_widget)

        splitter.addWidget(self.favorite_list)
        splitter.setSizes([350, 50, 400])
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 4)

        # 底部按钮
        self.save_button: QtWidgets.QPushButton = QtWidgets.QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)

        buttons_hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        buttons_hbox.addStretch()
        buttons_hbox.addWidget(self.save_button)

        # 主布局
        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(splitter)
        vbox.addLayout(buttons_hbox)

        self.populate_models()
        self.load_settings()

    def populate_models(self) -> None:
        """填充所有模型树"""
        models: list[str] = self._engine.list_models()

        separator: str | None = self.detect_separator(models)
        vendor_models: dict[str, list[str]] = defaultdict(list)

        if separator:
            for name in models:
                parts: list[str] = name.split(separator, 1)
                if len(parts) == 2:
                    vendor, model = parts
                    vendor_models[vendor].append(name)
                else:
                    vendor_models["其他"].append(name)
        else:
            for name in models:
                vendor_models["其他"].append(name)

        for vendor, model_list in sorted(vendor_models.items()):
            vendor_item: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(
                self.tree_widget,
                [vendor, ""]
            )
            for model_name in sorted(model_list):
                if separator:
                    _, model_display = model_name.split(separator, 1)
                else:
                    model_display = model_name

                item: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(vendor_item, ["", model_display])
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, model_name)

        self.tree_widget.expandAll()

        for i in range(self.tree_widget.columnCount()):
            self.tree_widget.resizeColumnToContents(i)

    def load_settings(self) -> None:
        """加载配置"""
        self.favorite_list.clear()
        favorite_models: list[str] = load_favorite_models()
        self.favorite_list.addItems(favorite_models)

    def save_settings(self) -> None:
        """保存配置"""
        models: list[str] = []
        for i in range(self.favorite_list.count()):
            item: QtWidgets.QListWidgetItem = self.favorite_list.item(i)
            models.append(item.text())

        save_favorite_models(models)
        QtWidgets.QMessageBox.information(self, "成功", "常用模型配置已保存！", QtWidgets.QMessageBox.StandardButton.Ok)

        self.close()

    def add_model(self) -> None:
        """添加模型到常用列表"""
        item: QtWidgets.QTreeWidgetItem = self.tree_widget.currentItem()
        if not item:
            return

        model_name: str | None = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not model_name:
            return

        current_models: list[str] = [
            self.favorite_list.item(i).text()
            for i in range(self.favorite_list.count())
        ]
        if model_name not in current_models:
            self.favorite_list.addItem(model_name)

    def remove_model(self) -> None:
        """从常用列表移除模型"""
        item: QtWidgets.QListWidgetItem = self.favorite_list.currentItem()
        if item:
            row: int = self.favorite_list.row(item)
            self.favorite_list.takeItem(row)

    def move_model_up(self) -> None:
        """上移常用模型"""
        current_row: int = self.favorite_list.currentRow()
        if current_row > 0:
            item: QtWidgets.QListWidgetItem = self.favorite_list.takeItem(current_row)
            self.favorite_list.insertItem(current_row - 1, item)
            self.favorite_list.setCurrentRow(current_row - 1)

    def move_model_down(self) -> None:
        """下移常用模型"""
        current_row: int = self.favorite_list.currentRow()
        if 0 <= current_row < self.favorite_list.count() - 1:
            item: QtWidgets.QListWidgetItem = self.favorite_list.takeItem(current_row)
            self.favorite_list.insertItem(current_row + 1, item)
            self.favorite_list.setCurrentRow(current_row + 1)

    def show_context_menu(self, pos: QtCore.QPoint) -> None:
        """显示右键菜单"""
        menu: QtWidgets.QMenu = QtWidgets.QMenu(self)

        expand_action: QtGui.QAction = menu.addAction("全部展开")
        expand_action.triggered.connect(self.tree_widget.expandAll)

        collapse_action: QtGui.QAction = menu.addAction("全部折叠")
        collapse_action.triggered.connect(self.tree_widget.collapseAll)

        menu.exec(self.tree_widget.viewport().mapToGlobal(pos))

    def show_favorite_context_menu(self, pos: QtCore.QPoint) -> None:
        """显示常用列表右键菜单"""
        item: QtWidgets.QListWidgetItem | None = self.favorite_list.itemAt(pos)
        if not item:
            return

        menu: QtWidgets.QMenu = QtWidgets.QMenu(self)

        up_action: QtGui.QAction = menu.addAction("上移")
        up_action.triggered.connect(self.move_model_up)

        down_action: QtGui.QAction = menu.addAction("下移")
        down_action.triggered.connect(self.move_model_down)

        menu.addSeparator()

        remove_action: QtGui.QAction = menu.addAction("移除")
        remove_action.triggered.connect(self.remove_model)

        menu.exec(self.favorite_list.viewport().mapToGlobal(pos))

    def detect_separator(self, models: list[str]) -> str | None:
        """检测模型名称中的分隔符"""
        if not models:
            return None

        candidates: list[str] = ["/", ":", "\\"]
        counts: dict[str, int] = defaultdict(int)

        for name in models:
            for sep in candidates:
                if sep in name:
                    counts[sep] += 1

        if not counts:
            return None

        return max(counts, key=lambda x: counts[x])


class GatewayDialog(QtWidgets.QDialog):
    """AI服务配置对话框"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)

        self.setting_modified: bool = False

        # 嵌套字典: {gateway_type: {key: QLineEdit | QComboBox}}
        self.setting_widgets: dict[str, dict[str, QtWidgets.QWidget]] = {}

        self.page_indices: dict[str, int] = {}      # Gateway类型到页面索引的映射

        self.init_ui()
        self.init_gateway_pages()
        self.load_current_setting()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("AI服务配置")
        self.setMinimumSize(600, 300)

        # Gateway 类型选择
        self.type_label: QtWidgets.QLabel = QtWidgets.QLabel("AI服务")

        self.type_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.type_combo.setFixedWidth(300)
        self.type_combo.addItems(sorted(GATEWAY_CLASSES.keys()))
        self.type_combo.currentTextChanged.connect(self.on_type_changed)

        type_hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        type_hbox.addWidget(self.type_label)
        type_hbox.addWidget(self.type_combo)
        type_hbox.addStretch()

        # 配置字段容器 - 使用 QStackedWidget 预加载所有页面
        self.setting_label: QtWidgets.QLabel = QtWidgets.QLabel("配置参数")
        self.stack_widget: QtWidgets.QStackedWidget = QtWidgets.QStackedWidget()

        # 底部按钮
        self.save_button: QtWidgets.QPushButton = QtWidgets.QPushButton("保存")
        self.save_button.clicked.connect(self.save_setting)

        self.cancel_button: QtWidgets.QPushButton = QtWidgets.QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)

        button_hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        button_hbox.addStretch()
        button_hbox.addWidget(self.save_button)
        button_hbox.addWidget(self.cancel_button)

        # 主布局
        main_vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        main_vbox.addLayout(type_hbox)
        main_vbox.addWidget(QtWidgets.QLabel("   "))
        main_vbox.addWidget(self.setting_label)
        main_vbox.addWidget(self.stack_widget)
        main_vbox.addLayout(button_hbox)
        self.setLayout(main_vbox)

    def init_gateway_pages(self) -> None:
        """预先创建所有 Gateway 的配置页面"""
        for gateway_type in sorted(GATEWAY_CLASSES.keys()):
            gateway_cls = get_gateway_class(gateway_type)
            if not gateway_cls:
                continue

            # 创建该 Gateway 的页面
            page_widget: QtWidgets.QWidget = QtWidgets.QWidget()
            page_layout: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
            page_widget.setLayout(page_layout)

            # 获取默认配置和已保存配置
            default_setting: dict = gateway_cls.default_setting
            saved_setting: dict = load_gateway_setting(gateway_type)

            # 创建配置字段
            widgets: dict[str, QtWidgets.QWidget] = {}
            for key, default_value in default_setting.items():
                label: str = self.get_field_label(key)

                # 列表类型使用 QComboBox
                if isinstance(default_value, list):
                    combo_box: QtWidgets.QComboBox = QtWidgets.QComboBox()
                    combo_box.addItems(default_value)

                    # 使用已保存的值设置当前选项
                    saved_value: str = saved_setting.get(key, "")
                    if saved_value and saved_value in default_value:
                        combo_box.setCurrentText(saved_value)

                    page_layout.addRow(label, combo_box)
                    widgets[key] = combo_box
                # 其他类型使用 QLineEdit
                else:
                    line_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()

                    # 使用已保存的值，否则使用默认值
                    value: str = saved_setting.get(key, default_value)
                    line_edit.setText(str(value) if value else "")

                    page_layout.addRow(label, line_edit)
                    widgets[key] = line_edit

            # 保存控件引用和页面索引
            self.setting_widgets[gateway_type] = widgets
            index: int = self.stack_widget.addWidget(page_widget)
            self.page_indices[gateway_type] = index

    def load_current_setting(self) -> None:
        """加载当前配置"""
        gateway_type: str = load_gateway_type()

        if gateway_type and gateway_type in GATEWAY_CLASSES:
            self.type_combo.setCurrentText(gateway_type)
        else:
            # 默认选择第一个
            self.type_combo.setCurrentIndex(0)

        self.on_type_changed(self.type_combo.currentText())

    def on_type_changed(self, gateway_type: str) -> None:
        """Gateway 类型变更时切换显示页面"""
        if gateway_type in self.page_indices:
            self.stack_widget.setCurrentIndex(self.page_indices[gateway_type])

    def get_field_label(self, key: str) -> str:
        """获取字段显示标签"""
        labels: dict[str, str] = {
            "base_url": "API 地址",
            "api_key": "API 密钥",
            "reasoning_effort": "推理强度",
        }
        return labels.get(key, key)

    def save_setting(self) -> None:
        """保存配置"""
        gateway_type: str = self.type_combo.currentText()

        # 获取当前 Gateway 的控件
        widgets: dict[str, QtWidgets.QWidget] | None = self.setting_widgets.get(
            gateway_type
        )
        if not widgets:
            return

        # 收集配置值
        setting: dict[str, str] = {}
        for key, widget in widgets.items():
            if isinstance(widget, QtWidgets.QComboBox):
                setting[key] = widget.currentText()
            elif isinstance(widget, QtWidgets.QLineEdit):
                setting[key] = widget.text().strip()

        # 验证必填字段
        gateway_cls = get_gateway_class(gateway_type)
        if gateway_cls:
            default_setting: dict = gateway_cls.default_setting
            for key in default_setting:
                # api_key 是必填项
                if key == "api_key" and not setting.get(key):
                    QtWidgets.QMessageBox.warning(
                        self,
                        "配置错误",
                        "API 密钥不能为空"
                    )
                    return

        # 保存配置
        save_gateway_type(gateway_type)
        save_gateway_setting(gateway_type, setting)

        self.setting_modified = True
        self.accept()

    def was_modified(self) -> bool:
        """返回配置是否被修改"""
        return self.setting_modified


class CreateKnowledgeDialog(QtWidgets.QDialog):
    """新建知识库对话框"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)

        self.created_kb_name: str = ""

        # Embedder 类型到页面索引的映射
        self.page_indices: dict[str, int] = {}

        self.init_ui()
        self.load_existing_kbs()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("新建知识库")
        self.setMinimumSize(550, 400)

        # 知识库名称
        self.name_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.name_line.setPlaceholderText("请输入知识库名称（英文、数字、下划线）")

        # 从已有知识库复制配置
        self.copy_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.copy_combo.addItem("（不复制，使用默认配置）")
        self.copy_combo.currentIndexChanged.connect(self.on_copy_changed)

        # 嵌入模型配置
        self.type_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.type_combo.addItems(EMBEDDER_TYPES)
        self.type_combo.currentTextChanged.connect(self.on_type_changed)

        # 配置字段容器
        self.stack_widget: QtWidgets.QStackedWidget = QtWidgets.QStackedWidget()
        self._init_embedder_pages()

        # 底部按钮
        self.create_button: QtWidgets.QPushButton = QtWidgets.QPushButton("创建")
        self.create_button.clicked.connect(self.create_knowledge_base)

        self.cancel_button: QtWidgets.QPushButton = QtWidgets.QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)

        button_hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        button_hbox.addStretch()
        button_hbox.addWidget(self.create_button)
        button_hbox.addWidget(self.cancel_button)

        # 主布局
        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow("知识库名称", self.name_line)
        form.addRow("复制配置自", self.copy_combo)
        form.addRow("", QtWidgets.QLabel(""))  # 分隔行
        form.addRow("─── 嵌入模型配置（创建后不可修改）───", QtWidgets.QLabel(""))
        form.addRow("模型服务", self.type_combo)

        main_vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        main_vbox.addLayout(form)
        main_vbox.addWidget(self.stack_widget)
        main_vbox.addStretch()
        main_vbox.addLayout(button_hbox)
        self.setLayout(main_vbox)

    def _init_embedder_pages(self) -> None:
        """初始化 Embedder 配置页面"""
        # OpenAI 页面
        openai_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        openai_layout: QtWidgets.QFormLayout = QtWidgets.QFormLayout()

        self.openai_base_url: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        defaults = EMBEDDER_DEFAULTS.get("OpenAI", {})
        self.openai_base_url.setText(defaults.get("base_url", "https://api.openai.com/v1"))

        self.openai_model: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.openai_model.setText(defaults.get("model_name", "text-embedding-3-small"))

        openai_layout.addRow("API 地址", self.openai_base_url)
        openai_layout.addRow("模型名称", self.openai_model)
        openai_widget.setLayout(openai_layout)

        # DashScope 页面
        dashscope_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        dashscope_layout: QtWidgets.QFormLayout = QtWidgets.QFormLayout()

        self.dashscope_model: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        defaults = EMBEDDER_DEFAULTS.get("DashScope", {})
        self.dashscope_model.setText(defaults.get("model_name", "text-embedding-v3"))

        dashscope_layout.addRow("模型名称", self.dashscope_model)
        dashscope_widget.setLayout(dashscope_layout)

        # 添加到 StackedWidget
        self.page_indices["OpenAI"] = self.stack_widget.addWidget(openai_widget)
        self.page_indices["DashScope"] = self.stack_widget.addWidget(dashscope_widget)

    def load_existing_kbs(self) -> None:
        """加载已有知识库列表"""
        kb_names: list[str] = list_knowledge_bases()
        for name in kb_names:
            metadata = load_knowledge_metadata(name)
            if metadata:
                self.copy_combo.addItem(name)

    def on_copy_changed(self, index: int) -> None:
        """复制配置下拉框变化"""
        if index == 0:
            # 恢复默认配置
            defaults = EMBEDDER_DEFAULTS.get("OpenAI", {})
            self.openai_base_url.setText(defaults.get("base_url", "https://api.openai.com/v1"))
            self.openai_model.setText(defaults.get("model_name", "text-embedding-3-small"))

            defaults = EMBEDDER_DEFAULTS.get("DashScope", {})
            self.dashscope_model.setText(defaults.get("model_name", "text-embedding-v3"))

            self.type_combo.setCurrentIndex(0)
            return

        # 复制选中知识库的配置
        kb_name: str = self.copy_combo.currentText()
        metadata = load_knowledge_metadata(kb_name)
        if not metadata:
            return

        embedder_type: str = metadata.get("embedder_type", "OpenAI")
        self.type_combo.setCurrentText(embedder_type)

        if embedder_type == "OpenAI":
            self.openai_base_url.setText(metadata.get("base_url", ""))
            self.openai_model.setText(metadata.get("model_name", ""))
        elif embedder_type == "DashScope":
            self.dashscope_model.setText(metadata.get("model_name", ""))

    def on_type_changed(self, embedder_type: str) -> None:
        """Embedder 类型变更时切换显示页面"""
        if embedder_type in self.page_indices:
            self.stack_widget.setCurrentIndex(self.page_indices[embedder_type])

    def create_knowledge_base(self) -> None:
        """创建知识库"""
        import re

        # 验证名称
        kb_name: str = self.name_line.text().strip()
        if not kb_name:
            QtWidgets.QMessageBox.warning(self, "错误", "请输入知识库名称")
            return

        if not re.match(r'^[a-zA-Z0-9_]+$', kb_name):
            QtWidgets.QMessageBox.warning(
                self, "错误", "知识库名称只能包含英文字母、数字和下划线"
            )
            return

        # 检查是否已存在
        if kb_name in list_knowledge_bases():
            QtWidgets.QMessageBox.warning(self, "错误", f"知识库 '{kb_name}' 已存在")
            return

        # 获取配置
        embedder_type: str = self.type_combo.currentText()
        base_url: str = ""
        model_name: str = ""

        if embedder_type == "OpenAI":
            base_url = self.openai_base_url.text().strip()
            model_name = self.openai_model.text().strip()
        elif embedder_type == "DashScope":
            model_name = self.dashscope_model.text().strip()

        if not model_name:
            QtWidgets.QMessageBox.warning(self, "错误", "请输入模型名称")
            return

        # 检查 API 密钥是否已配置
        embedder_setting = load_embedder_setting(embedder_type)
        if not embedder_setting.get("api_key"):
            reply = QtWidgets.QMessageBox.question(
                self,
                "API 密钥未配置",
                f"{embedder_type} 的 API 密钥尚未配置。\n\n"
                "是否现在配置？（配置后才能正常使用知识库）",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self._configure_api_key(embedder_type)
                return
            # 用户选择稍后配置，继续创建

        # 创建知识库
        create_knowledge_base(
            kb_name=kb_name,
            embedder_type=embedder_type,
            base_url=base_url,
            model_name=model_name
        )

        self.created_kb_name = kb_name
        QtWidgets.QMessageBox.information(
            self, "创建成功", f"知识库 '{kb_name}' 创建成功"
        )
        self.accept()

    def _configure_api_key(self, embedder_type: str) -> None:
        """配置 API 密钥"""
        api_key, ok = QtWidgets.QInputDialog.getText(
            self,
            f"配置 {embedder_type} API 密钥",
            "请输入 API 密钥：",
            QtWidgets.QLineEdit.EchoMode.Password
        )

        if ok and api_key:
            setting = load_embedder_setting(embedder_type)
            setting["api_key"] = api_key
            save_embedder_setting(embedder_type, setting)
            QtWidgets.QMessageBox.information(
                self, "保存成功", "API 密钥已保存，请继续创建知识库"
            )

    def get_created_kb_name(self) -> str:
        """获取创建的知识库名称"""
        return self.created_kb_name


class ImportWorkerSignals(QtCore.QObject):
    """文档导入 Worker 信号"""
    progress: QtCore.Signal = QtCore.Signal(int, str)  # (进度百分比, 状态文本)
    finished: QtCore.Signal = QtCore.Signal(bool, str)  # (成功, 消息)


class ImportWorker(QtCore.QRunnable):
    """文档导入后台 Worker"""

    def __init__(
        self,
        filepath: str,
        db_name: str,
        chunk_size: int | None
    ) -> None:
        """构造函数"""
        super().__init__()
        self.filepath: str = filepath
        self.db_name: str = db_name
        self.chunk_size: int | None = chunk_size
        self.signals: ImportWorkerSignals = ImportWorkerSignals()

    def run(self) -> None:
        """执行导入"""
        import traceback
        from pathlib import Path

        from ..utility import read_text_file
        from ..segmenters.markdown_segmenter import MarkdownSegmenter
        from ..factory import get_embedder_for_knowledge
        from ..vectors.duckdb_vector import DuckVector
        from ..object import Segment

        try:
            # 读取文件
            self.signals.progress.emit(10, "正在读取文件...")
            filepath = Path(self.filepath)
            text: str = read_text_file(filepath)

            # 切片
            self.signals.progress.emit(20, "正在切片...")
            if self.chunk_size is None or self.chunk_size <= 0:
                # 完整导入：将整个文件作为一个片段
                metadata: dict[str, str] = {
                    "source": filepath.name,
                    "chunk_index": "0"
                }
                segments: list[Segment] = [Segment(text=text, metadata=metadata)]
            else:
                segmenter = MarkdownSegmenter(chunk_size=self.chunk_size)
                segments = segmenter.parse(text, {"source": filepath.name})

            if not segments:
                self.signals.finished.emit(False, "未生成任何片段")
                return

            # 向量化并存储
            self.signals.progress.emit(40, f"正在向量化 {len(segments)} 个片段...")

            embedder = get_embedder_for_knowledge(self.db_name)
            vector = DuckVector(name=self.db_name, embedder=embedder)

            # 分批添加并更新进度
            batch_size: int = 10
            total: int = len(segments)
            for i in range(0, total, batch_size):
                batch = segments[i:i + batch_size]
                vector.add_segments(batch)

                progress: int = 40 + int(55 * (i + len(batch)) / total)
                self.signals.progress.emit(progress, f"已处理 {min(i + len(batch), total)}/{total} 个片段")

            self.signals.progress.emit(100, "导入完成")
            self.signals.finished.emit(True, f"成功导入 {total} 个片段到知识库 '{self.db_name}'")

        except Exception:
            error_msg: str = traceback.format_exc()
            self.signals.finished.emit(False, f"导入失败：{error_msg}")


class DocumentImportDialog(QtWidgets.QDialog):
    """文档导入对话框"""

    def __init__(self, kb_name: str, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数

        Args:
            kb_name: 目标知识库名称
            parent: 父窗口
        """
        super().__init__(parent)

        self.kb_name: str = kb_name
        self.worker: ImportWorker | None = None

        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(f"导入文档到知识库: {self.kb_name}")
        self.setMinimumSize(550, 300)

        # 文件选择
        self.file_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.file_line.setPlaceholderText("请选择要导入的 Markdown 文件")
        self.file_line.setReadOnly(True)

        self.file_button: QtWidgets.QPushButton = QtWidgets.QPushButton("选择")
        self.file_button.clicked.connect(self.select_file)
        self.file_button.setFixedWidth(60)

        file_hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        file_hbox.addWidget(self.file_line)
        file_hbox.addWidget(self.file_button)

        # 切片参数
        self.full_import_check: QtWidgets.QCheckBox = QtWidgets.QCheckBox("完整导入（不切片）")
        self.full_import_check.stateChanged.connect(self.on_full_import_changed)

        self.chunk_size_label: QtWidgets.QLabel = QtWidgets.QLabel("块大小（字符数）")
        self.chunk_size_spin: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.chunk_size_spin.setRange(100, 100000)
        self.chunk_size_spin.setValue(2000)
        self.chunk_size_spin.setSingleStep(100)

        chunk_hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        chunk_hbox.addWidget(self.chunk_size_label)
        chunk_hbox.addWidget(self.chunk_size_spin)
        chunk_hbox.addStretch()

        # 进度显示
        self.status_label: QtWidgets.QLabel = QtWidgets.QLabel("就绪")
        self.progress_bar: QtWidgets.QProgressBar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # 底部按钮
        self.import_button: QtWidgets.QPushButton = QtWidgets.QPushButton("导入")
        self.import_button.clicked.connect(self.start_import)

        self.close_button: QtWidgets.QPushButton = QtWidgets.QPushButton("关闭")
        self.close_button.clicked.connect(self.close)

        button_hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        button_hbox.addStretch()
        button_hbox.addWidget(self.import_button)
        button_hbox.addWidget(self.close_button)

        # 主布局
        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow("文件路径", file_hbox)
        form.addRow("", self.full_import_check)
        form.addRow("", chunk_hbox)

        main_vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        main_vbox.addLayout(form)
        main_vbox.addSpacing(20)
        main_vbox.addWidget(self.status_label)
        main_vbox.addWidget(self.progress_bar)
        main_vbox.addStretch()
        main_vbox.addLayout(button_hbox)

        self.setLayout(main_vbox)

    def select_file(self) -> None:
        """选择文件"""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择 Markdown 文件",
            "",
            "Markdown 文件 (*.md);;所有文件 (*.*)"
        )
        if filepath:
            self.file_line.setText(filepath)

    def on_full_import_changed(self, state: int) -> None:
        """完整导入复选框状态变化"""
        enabled: bool = state != QtCore.Qt.CheckState.Checked.value
        self.chunk_size_label.setEnabled(enabled)
        self.chunk_size_spin.setEnabled(enabled)

    def start_import(self) -> None:
        """开始导入"""
        # 验证输入
        filepath: str = self.file_line.text().strip()
        if not filepath:
            QtWidgets.QMessageBox.warning(self, "错误", "请先选择要导入的文件")
            return

        from pathlib import Path
        if not Path(filepath).exists():
            QtWidgets.QMessageBox.warning(self, "错误", "所选文件不存在")
            return

        # 获取切片参数
        chunk_size: int | None = None
        if not self.full_import_check.isChecked():
            chunk_size = self.chunk_size_spin.value()

        # 禁用控件
        self.set_controls_enabled(False)

        # 启动后台任务
        self.worker = ImportWorker(filepath, self.kb_name, chunk_size)
        self.worker.signals.progress.connect(self.on_progress)
        self.worker.signals.finished.connect(self.on_finished)

        QtCore.QThreadPool.globalInstance().start(self.worker)

    def set_controls_enabled(self, enabled: bool) -> None:
        """设置控件启用状态"""
        self.file_button.setEnabled(enabled)
        self.full_import_check.setEnabled(enabled)
        self.chunk_size_spin.setEnabled(enabled and not self.full_import_check.isChecked())
        self.import_button.setEnabled(enabled)

    def on_progress(self, progress: int, status: str) -> None:
        """进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)

    def on_finished(self, success: bool, message: str) -> None:
        """导入完成"""
        self.set_controls_enabled(True)

        if success:
            QtWidgets.QMessageBox.information(self, "导入成功", message)
        else:
            QtWidgets.QMessageBox.warning(self, "导入失败", message)


class KnowledgeManagerDialog(QtWidgets.QDialog):
    """知识库管理对话框"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)

        self.current_db: str = ""

        self.init_ui()
        self.load_databases()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("知识库管理")
        self.setMinimumSize(900, 600)

        # 左侧知识库列表
        self.db_list: QtWidgets.QListWidget = QtWidgets.QListWidget()
        self.db_list.itemClicked.connect(self.on_db_selected)
        self.db_list.setMinimumWidth(200)
        self.db_list.setMaximumWidth(250)

        left_label: QtWidgets.QLabel = QtWidgets.QLabel("知识库列表")
        left_vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        left_vbox.addWidget(left_label)
        left_vbox.addWidget(self.db_list)

        left_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        left_widget.setLayout(left_vbox)

        # 右侧详情区域
        self.name_label: QtWidgets.QLabel = QtWidgets.QLabel("名称: -")
        self.count_label: QtWidgets.QLabel = QtWidgets.QLabel("片段数量: -")
        self.size_label: QtWidgets.QLabel = QtWidgets.QLabel("文件大小: -")
        self.created_label: QtWidgets.QLabel = QtWidgets.QLabel("创建时间: -")

        # 嵌入模型信息
        self.embedder_type_label: QtWidgets.QLabel = QtWidgets.QLabel("模型服务: -")
        self.embedder_url_label: QtWidgets.QLabel = QtWidgets.QLabel("API 地址: -")
        self.embedder_url_label.setWordWrap(True)
        self.embedder_model_label: QtWidgets.QLabel = QtWidgets.QLabel("模型名称: -")

        info_form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        info_form.addRow(self.name_label)
        info_form.addRow(self.count_label)
        info_form.addRow(self.size_label)
        info_form.addRow(self.created_label)
        info_form.addRow(QtWidgets.QLabel(""))  # 分隔行
        info_form.addRow(QtWidgets.QLabel("─── 嵌入模型（不可修改）───"))
        info_form.addRow(self.embedder_type_label)
        info_form.addRow(self.embedder_url_label)
        info_form.addRow(self.embedder_model_label)

        # 片段预览
        preview_label: QtWidgets.QLabel = QtWidgets.QLabel("片段预览")
        self.preview_list: QtWidgets.QListWidget = QtWidgets.QListWidget()
        self.preview_list.setWordWrap(True)

        right_vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        right_vbox.addLayout(info_form)
        right_vbox.addSpacing(10)
        right_vbox.addWidget(preview_label)
        right_vbox.addWidget(self.preview_list)

        right_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        right_widget.setLayout(right_vbox)

        # 分割器
        splitter: QtWidgets.QSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([250, 650])

        # 底部按钮
        self.create_button: QtWidgets.QPushButton = QtWidgets.QPushButton("新建知识库")
        self.create_button.clicked.connect(self.show_create_dialog)

        self.import_button: QtWidgets.QPushButton = QtWidgets.QPushButton("导入文档")
        self.import_button.clicked.connect(self.show_import_dialog)
        self.import_button.setEnabled(False)

        self.delete_button: QtWidgets.QPushButton = QtWidgets.QPushButton("删除知识库")
        self.delete_button.clicked.connect(self.delete_database)
        self.delete_button.setEnabled(False)

        self.close_button: QtWidgets.QPushButton = QtWidgets.QPushButton("关闭")
        self.close_button.clicked.connect(self.close)

        button_hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        button_hbox.addWidget(self.create_button)
        button_hbox.addWidget(self.import_button)
        button_hbox.addWidget(self.delete_button)
        button_hbox.addStretch()
        button_hbox.addWidget(self.close_button)

        # 主布局
        main_vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        main_vbox.addWidget(splitter)
        main_vbox.addLayout(button_hbox)
        self.setLayout(main_vbox)

    def load_databases(self) -> None:
        """加载知识库列表"""
        kb_names: list[str] = list_knowledge_bases()

        self.db_list.clear()
        for name in sorted(kb_names):
            self.db_list.addItem(name)

        # 清空详情
        if not kb_names:
            self.clear_details()

    def clear_details(self) -> None:
        """清空详情显示"""
        self.current_db = ""
        self.name_label.setText("名称: -")
        self.count_label.setText("片段数量: -")
        self.size_label.setText("文件大小: -")
        self.created_label.setText("创建时间: -")
        self.embedder_type_label.setText("模型服务: -")
        self.embedder_url_label.setText("API 地址: -")
        self.embedder_model_label.setText("模型名称: -")
        self.preview_list.clear()
        self.import_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def on_db_selected(self, item: QtWidgets.QListWidgetItem) -> None:
        """选中知识库时显示详情"""
        from pathlib import Path
        from ..utility import get_folder_path
        from ..vectors.duckdb_vector import DuckVector

        db_name: str = item.text()
        self.current_db = db_name

        db_folder: Path = get_folder_path("duckdb_vector")
        db_path: Path = db_folder.joinpath(f"{db_name}.duckdb")

        # 基本信息
        self.name_label.setText(f"名称: {db_name}")

        # 文件大小
        if db_path.exists():
            size_bytes: int = db_path.stat().st_size
            if size_bytes < 1024:
                size_str: str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / 1024 / 1024:.1f} MB"
            self.size_label.setText(f"文件大小: {size_str}")
        else:
            self.size_label.setText("文件大小: -")

        # 加载元数据
        metadata = load_knowledge_metadata(db_name)
        if metadata:
            created_at: str = metadata.get("created_at", "-")
            if "T" in created_at:
                created_at = created_at.replace("T", " ").split(".")[0]
            self.created_label.setText(f"创建时间: {created_at}")

            self.embedder_type_label.setText(f"模型服务: {metadata.get('embedder_type', '-')}")
            self.embedder_url_label.setText(f"API 地址: {metadata.get('base_url', '（默认）')}")
            self.embedder_model_label.setText(f"模型名称: {metadata.get('model_name', '-')}")
        else:
            self.created_label.setText("创建时间: -（旧版知识库）")
            self.embedder_type_label.setText("模型服务: -（未配置）")
            self.embedder_url_label.setText("API 地址: -")
            self.embedder_model_label.setText("模型名称: -")

        # 片段数量和预览
        try:
            embedder = get_embedder_for_knowledge(db_name)
            vector = DuckVector(name=db_name, embedder=embedder)

            count: int = vector.count
            self.count_label.setText(f"片段数量: {count}")

            # 预览前几条
            self.preview_list.clear()
            if count > 0:
                # 使用一个简单查询获取一些片段
                segments = vector.retrieve("", k=min(10, count))
                for seg in segments:
                    source: str = seg.metadata.get("source", "未知")
                    preview_text: str = seg.text[:100].replace("\n", " ")
                    if len(seg.text) > 100:
                        preview_text += "..."
                    item_text: str = f"[{source}] {preview_text}"
                    self.preview_list.addItem(item_text)

        except Exception as e:
            self.count_label.setText("片段数量: 读取失败")
            self.preview_list.clear()
            self.preview_list.addItem(f"错误: {str(e)}")

        self.import_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def show_create_dialog(self) -> None:
        """显示新建知识库对话框"""
        dialog = CreateKnowledgeDialog(self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            # 刷新列表
            self.load_databases()
            # 选中新创建的知识库
            kb_name: str = dialog.get_created_kb_name()
            if kb_name:
                items = self.db_list.findItems(kb_name, QtCore.Qt.MatchFlag.MatchExactly)
                if items:
                    self.db_list.setCurrentItem(items[0])
                    self.on_db_selected(items[0])

    def show_import_dialog(self) -> None:
        """显示导入对话框"""
        if not self.current_db:
            QtWidgets.QMessageBox.warning(self, "提示", "请先选择一个知识库")
            return

        dialog = DocumentImportDialog(self.current_db, self)
        dialog.exec()
        # 刷新当前知识库详情
        if self.current_db:
            items = self.db_list.findItems(self.current_db, QtCore.Qt.MatchFlag.MatchExactly)
            if items:
                self.on_db_selected(items[0])

    def delete_database(self) -> None:
        """删除知识库"""
        if not self.current_db:
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除知识库 '{self.current_db}' 吗？\n\n此操作不可恢复！",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            from pathlib import Path
            from ..utility import get_folder_path

            db_folder: Path = get_folder_path("duckdb_vector")
            db_path: Path = db_folder.joinpath(f"{self.current_db}.duckdb")

            try:
                if db_path.exists():
                    db_path.unlink()

                # 同时删除可能存在的 .wal 文件
                wal_path: Path = db_folder.joinpath(f"{self.current_db}.duckdb.wal")
                if wal_path.exists():
                    wal_path.unlink()

                # 删除元数据文件
                delete_knowledge_metadata(self.current_db)

                QtWidgets.QMessageBox.information(
                    self,
                    "删除成功",
                    f"知识库 '{self.current_db}' 已删除"
                )

                # 刷新列表
                self.clear_details()
                self.load_databases()

            except Exception as e:
                QtWidgets.QMessageBox.warning(
                    self,
                    "删除失败",
                    f"删除失败: {str(e)}"
                )
