import json
import os
import re
import uuid
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import cast, NamedTuple

from ..constant import Role
from ..engine import AgentEngine, default_profile
from ..object import ToolSchema, Segment
from ..agent import Profile, TaskAgent
from ..utility import read_text_file
from ..gateways import GATEWAY_CLASSES, get_gateway_class
from ..embedders import get_embedder_names, get_embedder_class
from ..embedder import BaseEmbedder

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


class KnowledgeCreateDialog(QtWidgets.QDialog):
    """新建知识库对话框"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)
        self.inputs: dict[str, QtWidgets.QLineEdit] = {}
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("新建知识库")
        self.setMinimumWidth(800)

        self.name_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("请输入知识库名称（英文、数字、下划线）")

        self.desc_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.desc_edit.setPlaceholderText("可选的描述信息")

        self.type_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.type_combo.addItems(get_embedder_names())
        self.type_combo.currentTextChanged.connect(self._refresh_params)

        self.param_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        self.param_layout: QtWidgets.QFormLayout = QtWidgets.QFormLayout(self.param_widget)

        button_box: QtWidgets.QDialogButtonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow("名称", self.name_edit)
        form.addRow("描述", self.desc_edit)
        form.addRow("Embedder", self.type_combo)

        main_vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        main_vbox.addLayout(form)
        main_vbox.addWidget(self.param_widget)
        main_vbox.addStretch()
        main_vbox.addWidget(button_box)

        self._refresh_params(self.type_combo.currentText())

    def _refresh_params(self, embedder_type: str) -> None:
        """刷新参数输入框"""
        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.inputs.clear()

        embedder_cls: type[BaseEmbedder] = get_embedder_class(embedder_type)
        for key, default_value in embedder_cls.default_setting.items():
            if key == "api_key":
                text: str = "API 密钥"
            elif key == "base_url":
                text = "API 地址"
            elif key == "model_name":
                text = "模型名称"
            else:
                text = key

            edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
            edit.setPlaceholderText(str(default_value))
            self.param_layout.addRow(text, edit)
            self.inputs[key] = edit

    def _validate_and_accept(self) -> None:
        """验证并接受"""
        name: str = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "错误", "名称不能为空")
            return
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            QtWidgets.QMessageBox.warning(self, "错误", "名称只能包含英文字母、数字和下划线")
            return
        self.accept()

    def get_data(self) -> dict:
        """获取输入数据"""
        embedder_setting: dict[str, str] = {}
        for key, edit in self.inputs.items():
            val: str = edit.text().strip()
            if val:
                embedder_setting[key] = val
            elif edit.placeholderText() and key != "api_key":
                embedder_setting[key] = edit.placeholderText()

        return {
            "name": self.name_edit.text().strip(),
            "description": self.desc_edit.text().strip(),
            "embedder_type": self.type_combo.currentText(),
            "embedder_setting": embedder_setting,
        }


class KnowledgeImportDialog(QtWidgets.QDialog):
    """导入文档对话框"""

    def __init__(self, kb_name: str, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)
        self.kb_name: str = kb_name
        self.init_ui()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(f"导入到: {self.kb_name}")
        self.setMinimumWidth(800)

        self.file_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText("请选择要导入的 Markdown 文件")

        file_button: QtWidgets.QPushButton = QtWidgets.QPushButton("选择")
        file_button.clicked.connect(self.select_file)

        file_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(file_button)

        self.full_check: QtWidgets.QCheckBox = QtWidgets.QCheckBox("完整导入（不切片）")
        self.full_check.stateChanged.connect(self._on_full_changed)

        self.chunk_spin: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.chunk_spin.setRange(100, 100000)
        self.chunk_spin.setValue(2000)

        self.status: QtWidgets.QLabel = QtWidgets.QLabel("就绪")

        self.import_button: QtWidgets.QPushButton = QtWidgets.QPushButton("导入")
        self.import_button.clicked.connect(self.do_import)

        close_button: QtWidgets.QPushButton = QtWidgets.QPushButton("关闭")
        close_button.clicked.connect(self.close)

        button_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(close_button)

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow("文件", file_layout)
        form.addRow("", self.full_check)
        form.addRow("块大小", self.chunk_spin)

        main_vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        main_vbox.addLayout(form)
        main_vbox.addWidget(self.status)
        main_vbox.addStretch()
        main_vbox.addLayout(button_layout)

    def select_file(self) -> None:
        """选择文件"""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择 Markdown", "", "Markdown (*.md);;All (*)"
        )
        if path:
            self.file_edit.setText(path)

    def _on_full_changed(self, state: int) -> None:
        """完整导入复选框状态变化"""
        self.chunk_spin.setEnabled(state != QtCore.Qt.CheckState.Checked.value)

    def do_import(self) -> None:
        """执行导入"""
        from .knowledge import get_knowledge_vector
        from ..segmenters.markdown_segmenter import MarkdownSegmenter

        filepath: str = self.file_edit.text()
        if not filepath or not Path(filepath).exists():
            QtWidgets.QMessageBox.warning(self, "错误", "请选择有效文件")
            return

        self.import_button.setEnabled(False)
        self.status.setText("处理中...")
        QtWidgets.QApplication.processEvents()

        text: str = read_text_file(Path(filepath))
        source: str = Path(filepath).name

        if self.full_check.isChecked():
            segments: list[Segment] = [
                Segment(text=text, metadata={"source": source, "chunk_index": "0"})
            ]
        else:
            segmenter = MarkdownSegmenter(chunk_size=self.chunk_spin.value())
            segments = segmenter.parse(text, {"source": source})

        vector = get_knowledge_vector(self.kb_name)
        vector.add_segments(segments)

        self.status.setText("就绪")
        QtWidgets.QMessageBox.information(
            self, "成功", f"导入 {len(segments)} 个片段", QtWidgets.QMessageBox.StandardButton.Ok
        )

        self.import_button.setEnabled(True)


class KnowledgeViewDialog(QtWidgets.QDialog):
    """查看知识库片段"""

    PAGE_SIZE: int = 50  # 每页显示的条目数

    def __init__(self, kb_name: str, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)

        self.kb_name: str = kb_name
        self.current_page: int = 0
        self.total_count: int = 0

        self.init_ui()
        self.load_data()

    def init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle(f"查看: {self.kb_name}")
        self.resize(1400, 1000)

        # 搜索框
        self.search_edit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("搜索片段内容...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.on_search)

        # 树形控件，按来源分组
        self.tree_widget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget()
        self.tree_widget.setHeaderLabels(["来源 / 片段预览", "字数"])
        self.tree_widget.setColumnWidth(0, 380)
        self.tree_widget.setColumnWidth(1, 60)
        self.tree_widget.itemSelectionChanged.connect(self.on_select)
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.setRootIsDecorated(True)

        # 左侧布局
        left_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        left_layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.search_edit)
        left_layout.addWidget(self.tree_widget)

        # 右侧：元数据区域
        self.meta_label: QtWidgets.QLabel = QtWidgets.QLabel()
        self.meta_label.setWordWrap(True)
        self.meta_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.meta_label.setStyleSheet(
            "background: #f5f5f5; padding: 8px; border-radius: 4px; color: #333;"
        )
        self.meta_label.setMinimumHeight(60)

        # 右侧：内容区域
        self.text_edit: QtWidgets.QTextEdit = QtWidgets.QTextEdit()
        self.text_edit.setReadOnly(True)

        meta_title: QtWidgets.QLabel = QtWidgets.QLabel("📋 元数据")
        meta_title.setStyleSheet("font-weight: bold; margin-top: 4px;")
        content_title: QtWidgets.QLabel = QtWidgets.QLabel("📝 内容")
        content_title.setStyleSheet("font-weight: bold; margin-top: 8px;")

        right_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        right_layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(meta_title)
        right_layout.addWidget(self.meta_label)
        right_layout.addWidget(content_title)
        right_layout.addWidget(self.text_edit, 1)

        splitter: QtWidgets.QSplitter = QtWidgets.QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([450, 650])

        # 分页控件
        self.button_prev: QtWidgets.QPushButton = QtWidgets.QPushButton("◀ 上一页")
        self.button_prev.clicked.connect(self.on_prev_page)

        self.button_next: QtWidgets.QPushButton = QtWidgets.QPushButton("下一页 ▶")
        self.button_next.clicked.connect(self.on_next_page)

        self.page_label: QtWidgets.QLabel = QtWidgets.QLabel("第 1 页")

        page_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        page_layout.addWidget(self.button_prev)
        page_layout.addWidget(self.page_label)
        page_layout.addWidget(self.button_next)
        page_layout.addStretch()

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(splitter)
        layout.addLayout(page_layout)

    def load_data(self) -> None:
        """加载当前页数据"""
        from .knowledge import get_knowledge_vector

        vector = get_knowledge_vector(self.kb_name)
        self.total_count = vector.count

        # 计算分页参数
        offset: int = self.current_page * self.PAGE_SIZE
        segments = vector.list_segments(limit=self.PAGE_SIZE, offset=offset)

        # 清空并重建
        self.tree_widget.clear()
        self.meta_label.clear()
        self.text_edit.clear()

        # 按来源分组
        grouped: dict[str, list] = {}
        for seg in segments:
            src: str = seg.metadata.get("source", "未知来源")
            grouped.setdefault(src, []).append(seg)

        # 构建树形结构
        for src, segs in grouped.items():
            # 父节点：来源文件
            parent: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(
                [f"📄 {src}", f"({len(segs)})"]
            )
            parent.setExpanded(True)
            self.tree_widget.addTopLevelItem(parent)

            for seg in segs:
                preview: str = seg.text[:60].replace("\n", " ").strip()
                child: QtWidgets.QTreeWidgetItem = QtWidgets.QTreeWidgetItem(
                    [preview + "...", str(len(seg.text))]
                )
                child.setData(0, QtCore.Qt.ItemDataRole.UserRole, seg)
                parent.addChild(child)

        # 更新分页状态
        self._update_page_state()

    def _update_page_state(self) -> None:
        """更新分页状态"""
        total_pages: int = max(1, (self.total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        current_display: int = self.current_page + 1

        self.setWindowTitle(f"查看: {self.kb_name} (共 {self.total_count} 条)")
        self.page_label.setText(f"第 {current_display} / {total_pages} 页")

        # 控制按钮状态
        self.button_prev.setEnabled(self.current_page > 0)
        self.button_next.setEnabled(current_display < total_pages)

    def on_search(self, text: str) -> None:
        """搜索过滤片段"""
        text = text.lower()
        for i in range(self.tree_widget.topLevelItemCount()):
            parent: QtWidgets.QTreeWidgetItem | None = self.tree_widget.topLevelItem(i)
            if parent is None:
                continue
            parent_visible: bool = False
            for j in range(parent.childCount()):
                child: QtWidgets.QTreeWidgetItem | None = parent.child(j)
                if child is None:
                    continue
                seg = child.data(0, QtCore.Qt.ItemDataRole.UserRole)
                visible: bool = text in seg.text.lower() if seg else False
                child.setHidden(not visible)
                if visible:
                    parent_visible = True
            # 如果没有搜索词，显示所有父节点；否则只显示有匹配子项的父节点
            parent.setHidden(not parent_visible and bool(text))

    def on_prev_page(self) -> None:
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_data()

    def on_next_page(self) -> None:
        """下一页"""
        total_pages: int = (self.total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        if self.current_page + 1 < total_pages:
            self.current_page += 1
            self.load_data()

    def on_select(self) -> None:
        """选中片段时显示详情"""
        items: list[QtWidgets.QTreeWidgetItem] = self.tree_widget.selectedItems()
        if not items:
            return
        seg = items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not seg:
            # 选中的是父节点（来源），清空详情
            self.meta_label.clear()
            self.text_edit.clear()
            return
        # 显示元数据（HTML格式）
        meta_html: str = " &nbsp;|&nbsp; ".join(
            f"<b>{k}:</b> {v}" for k, v in seg.metadata.items()
        )
        self.meta_label.setText(meta_html)
        # 显示内容
        self.text_edit.setText(seg.text)


class KnowledgeDialog(QtWidgets.QDialog):
    """知识库管理对话框"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)
        self.setWindowTitle("知识库管理")
        self.setMinimumSize(700, 500)
        self.init_ui()
        self.refresh()

    def init_ui(self) -> None:
        """初始化UI"""
        self.table: QtWidgets.QTableWidget = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["名称", "描述"])
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

        button_new: QtWidgets.QPushButton = QtWidgets.QPushButton("新建")
        button_new.clicked.connect(self.create_knowledge)

        self.button_import: QtWidgets.QPushButton = QtWidgets.QPushButton("导入")
        self.button_import.clicked.connect(self.import_document)
        self.button_import.setEnabled(False)

        self.button_view: QtWidgets.QPushButton = QtWidgets.QPushButton("查看")
        self.button_view.clicked.connect(self.view_knowledge)
        self.button_view.setEnabled(False)

        self.button_del: QtWidgets.QPushButton = QtWidgets.QPushButton("删除")
        self.button_del.clicked.connect(self.delete_knowledge)
        self.button_del.setEnabled(False)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        button_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(button_new)
        button_layout.addStretch()
        button_layout.addWidget(self.button_import)
        button_layout.addWidget(self.button_view)
        button_layout.addWidget(self.button_del)

        layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(button_layout)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        """刷新列表"""
        from .knowledge import list_knowledge_bases
        kbs: list[dict[str, str]] = list_knowledge_bases()
        self.table.setRowCount(0)

        for kb in kbs:
            row: int = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(kb["name"]))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(kb["description"]))

    def _on_selection_changed(self) -> None:
        """选择变化时更新按钮状态"""
        has_selection: bool = self.table.currentRow() >= 0
        self.button_import.setEnabled(has_selection)
        self.button_view.setEnabled(has_selection)
        self.button_del.setEnabled(has_selection)

    def _selected_name(self) -> str | None:
        """获取选中的知识库名称"""
        row: int = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            if item:
                return item.text()
        return None

    def create_knowledge(self) -> None:
        """新建知识库"""
        dialog: KnowledgeCreateDialog = KnowledgeCreateDialog(self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            data: dict = dialog.get_data()
            try:
                from .knowledge import create_knowledge_base
                create_knowledge_base(**data)
                self.refresh()
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "错误", str(e))

    def import_document(self) -> None:
        """导入文档"""
        name: str | None = self._selected_name()
        if not name:
            QtWidgets.QMessageBox.warning(self, "提示", "请先选择知识库")
            return
        dialog: KnowledgeImportDialog = KnowledgeImportDialog(name, self)
        dialog.exec()

    def view_knowledge(self) -> None:
        """查看知识库"""
        name: str | None = self._selected_name()
        if not name:
            QtWidgets.QMessageBox.warning(self, "提示", "请先选择知识库")
            return
        dialog: KnowledgeViewDialog = KnowledgeViewDialog(name, self)
        dialog.exec()

    def delete_knowledge(self) -> None:
        """删除知识库"""
        name: str | None = self._selected_name()
        if not name:
            QtWidgets.QMessageBox.warning(self, "提示", "请先选择知识库")
            return
        reply = QtWidgets.QMessageBox.question(
            self, "确认", f"删除知识库 '{name}'？此操作不可恢复。"
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            from .knowledge import delete_knowledge_base
            delete_knowledge_base(name)
            self.refresh()
