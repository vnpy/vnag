import traceback
from typing import Any

from ..agent import TaskAgent
from ..constant import Role, DeltaEvent
from ..object import Attachment
from .qt import QtCore


class StreamSignals(QtCore.QObject):
    """
    定义StreamWorker可以发出的信号
    """
    # 流式响应块（content 内容）
    content: QtCore.Signal = QtCore.Signal(str)

    # 流式响应块（thinking 内容）
    thinking: QtCore.Signal = QtCore.Signal(str)

    # 流式响应结束
    finished: QtCore.Signal = QtCore.Signal()

    # 流式响应错误
    error: QtCore.Signal = QtCore.Signal(str)

    # 标题生成完成
    title: QtCore.Signal = QtCore.Signal(str)

    # Token 使用量更新 (input_tokens, output_tokens)
    usage: QtCore.Signal = QtCore.Signal(int, int)

    # 工具开始执行信号
    tool_start: QtCore.Signal = QtCore.Signal(str)

    # 工具执行完成信号
    tool_end: QtCore.Signal = QtCore.Signal(str, bool)

    # 警告信号
    warning: QtCore.Signal = QtCore.Signal(str)


class StreamWorker(QtCore.QRunnable):
    """
    在线程池中处理流式网关请求的Worker
    """
    def __init__(
        self,
        agent: TaskAgent,
        prompt: str,
        attachments: list[Attachment] | None = None,
    ) -> None:
        """构造函数"""
        super().__init__()

        self.agent: TaskAgent = agent
        self.prompt: str = prompt
        self.attachments: list[Attachment] = attachments or []
        self.signals: StreamSignals = StreamSignals()
        self.stopped: bool = False

    def stop(self) -> None:
        """停止流式请求"""
        self.stopped = True
        self.agent.aborted = True

    def _safe_emit(self, signal: QtCore.SignalInstance, *args: Any) -> None:
        """安全地发出信号，忽略对象已删除的情况"""
        try:
            signal.emit(*args)
        except RuntimeError:
            # 信号对象已被删除（窗口已关闭），忽略
            pass

    def run(self) -> None:
        """处理数据流"""
        # 累积 Token 使用量
        total_input: int = 0
        total_output: int = 0

        try:
            for delta in self.agent.stream(self.prompt, self.attachments):
                # 用户手动停止
                if self.stopped:
                    # 中止流式生成，保存已生成的部分内容
                    self.agent.abort_stream()
                    break
                # 收到 thinking 数据块
                if delta.thinking:
                    self._safe_emit(self.signals.thinking, delta.thinking)
                # 收到 content 数据块
                if delta.content:
                    self._safe_emit(self.signals.content, delta.content)
                # 累积 Token 使用量
                if delta.usage:
                    total_input += delta.usage.input_tokens
                    total_output += delta.usage.output_tokens

                # 结构化事件分发
                if delta.event == DeltaEvent.TOOL_START:
                    self._safe_emit(
                        self.signals.tool_start,
                        delta.payload["name"],
                    )
                elif delta.event == DeltaEvent.TOOL_END:
                    self._safe_emit(
                        self.signals.tool_end,
                        delta.payload["name"],
                        delta.payload["success"],
                    )
                elif delta.event == DeltaEvent.WARNING:
                    self._safe_emit(
                        self.signals.warning,
                        delta.payload["message"],
                    )

        except Exception:
            # 中止流式生成，保存已生成的部分内容
            self.agent.abort_stream()

            error_msg: str = traceback.format_exc()
            self._safe_emit(self.signals.error, error_msg)
        finally:
            # 发送最终的 Token 使用量
            self._safe_emit(self.signals.usage, total_input, total_output)
            self._safe_emit(self.signals.finished)

        # 流式响应完成后，检查是否需要自动生成标题
        if not self.stopped and self._should_generate_title():
            try:
                title: str = self.agent.generate_title(max_length=10)
                if title:
                    self._safe_emit(self.signals.title, title)
            except Exception:
                error_msg = traceback.format_exc()
                self._safe_emit(self.signals.error, error_msg)

    def _should_generate_title(self) -> bool:
        """判断是否需要自动生成标题"""
        # 检查是否还是默认名称
        if self.agent.name != "默认会话":
            return False

        # 检查是否完成了首次对话（系统消息 + 用户消息 + 助手消息 = 3条）
        if len(self.agent.messages) < 3:
            return False

        # 确保最后一条是助手消息
        if self.agent.messages[-1].role != Role.ASSISTANT:
            return False

        return True
