import traceback

from ..agent import TaskAgent
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
