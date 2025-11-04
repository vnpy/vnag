import traceback

from ..engine import AgentEngine
from ..object import Request
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
    def __init__(self, engine: AgentEngine, request: Request) -> None:
        """构造函数"""
        super().__init__()

        self.engine: AgentEngine = engine
        self.request: Request = request
        self.signals: StreamSignals = StreamSignals()

    def run(self) -> None:
        """处理数据流"""
        try:
            for delta in self.engine.stream(
                messages=self.request.messages,
                model=self.request.model,
                temperature=self.request.temperature,
                max_tokens=self.request.max_tokens,
            ):
                if delta.content:
                    self.signals.delta.emit(delta.content)
        except Exception:
            error_msg: str = traceback.format_exc()
            self.signals.error.emit(error_msg)
        finally:
            self.signals.finished.emit()
