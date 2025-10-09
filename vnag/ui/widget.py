import markdown

from ..constant import Role
from .qt import QtGui, QtWidgets


class HistoryWidget(QtWidgets.QTextEdit):
    """会话历史控件"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """构造函数"""
        super().__init__(parent)

        self.setReadOnly(True)
        self.setPlaceholderText("欢迎使用VeighNa Agent，有什么想聊聊的？")

        # 流式请求相关状态
        self.full_content: str = ""
        self.content_start: int = 0

    def append_message(self, role: Role, content: str) -> None:
        """在会话历史组件中添加消息"""
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)

        if role is Role.USER:
            # 用户内容不需要被渲染
            escaped_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

            html = f"""
            <p><b>💬 User</b></p>
            <div>{escaped_content}</div>
            <br><br>
            """
            self.insertHtml(html)
        elif role is Role.ASSISTANT:
            # AI返回内容以Markdown渲染
            html_content = markdown.markdown(content, extensions=["fenced_code", "codehilite"])

            html = f"""
            <p><b>✨ Assistant</b></p>
            {html_content}
            <br><br>
            """
            self.insertHtml(html)

        # 确保滚动条滚动到最新消息
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def start_stream(self) -> None:
        """开始新的流式输出"""
        self.full_content = ""

        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.insertHtml("<p><b>✨ Assistant</b></p>")
        self.content_start = self.textCursor().position()

    def update_stream(self, content_delta: str) -> None:
        """更新流式输出"""
        self.full_content += content_delta
        html_content: str = markdown.markdown(
            self.full_content,
            extensions=["fenced_code", "codehilite"]
        )

        cursor: QtGui.QTextCursor = self.textCursor()
        cursor.setPosition(self.content_start)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End, QtGui.QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

        self.setTextCursor(cursor)
        self.insertHtml(html_content)

        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def finish_stream(self) -> str:
        """结束流式输出"""
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.insertHtml("<br><br>")
        return self.full_content
