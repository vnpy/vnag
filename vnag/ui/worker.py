import traceback

from ..agent import TaskAgent
from ..constant import Role
from .qt import QtCore


class StreamSignals(QtCore.QObject):
    """
    定义StreamWorker可以发出的信号
    """
    # 流式响应块
    delta: QtCore.Signal = QtCore.Signal(str)

    # 流式响应结束
    finished: QtCore.Signal = QtCore.Signal()

    # 流式响应错误
    error: QtCore.Signal = QtCore.Signal(str)

    # 标题生成完成
    title: QtCore.Signal = QtCore.Signal(str)


class StreamWorker(QtCore.QRunnable):
    """
    在线程池中处理流式网关请求的Worker
    """
    def __init__(self, agent: TaskAgent, prompt: str) -> None:
        """构造函数"""
        super().__init__()

        self.agent: TaskAgent = agent
        self.prompt: str = prompt
        self.signals: StreamSignals = StreamSignals()
        self.stopped: bool = False

    def stop(self) -> None:
        """停止流式请求"""
        self.stopped = True

    def run(self) -> None:
        """处理数据流"""
        try:
            for delta in self.agent.stream(self.prompt):
                # 用户手动停止
                if self.stopped:
                    # 中止流式生成，保存已生成的部分内容
                    self.agent.abort_stream()
                    break
                # 收到数据块
                elif delta.content:
                    self.signals.delta.emit(delta.content)

        except Exception:
            # 中止流式生成，保存已生成的部分内容
            self.agent.abort_stream()

            error_msg: str = traceback.format_exc()
            self.signals.error.emit(error_msg)
        finally:
            self.signals.finished.emit()

        # 流式响应完成后，检查是否需要自动生成标题
        if not self.stopped and self._should_generate_title():
            try:
                title: str = self.agent.generate_title(max_length=10)
                if title:
                    self.signals.title.emit(title)
            except Exception:
                error_msg = traceback.format_exc()
                self.signals.error.emit(error_msg)

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
