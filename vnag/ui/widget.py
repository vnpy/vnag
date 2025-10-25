import json
import os
import uuid

from ..constant import Role
from .qt import QtWebEngineWidgets, QtWidgets, QtCore, QtWebEngineCore


class HistoryWidget(QtWebEngineWidgets.QWebEngineView):
    """会话历史控件"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)

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
