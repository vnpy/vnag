"""后台线程桥接：在子线程中消费 TaskAgent.stream()，通过队列向主线程投递事件"""

import queue
import threading
from uuid import uuid4

from ..agent import TaskAgent
from ..constant import DeltaEvent
from ..object import Delta
from .renderer import Renderer


class StreamBridge:
    """桥接 TaskAgent.stream() 与 CLI 渲染"""

    def __init__(self, agent: TaskAgent, renderer: Renderer) -> None:
        """构造函数"""
        self.agent: TaskAgent = agent
        self.renderer: Renderer = renderer

    def run(self, prompt: str) -> None:
        """
        阻塞式运行一轮对话

        在子线程中消费 stream()，主线程从队列取出 Delta 并渲染。
        Ctrl+C 时调用 agent.abort_stream() 中止。
        """
        event_queue: queue.Queue[Delta | None] = queue.Queue()

        def worker() -> None:
            try:
                for delta in self.agent.stream(prompt):
                    event_queue.put(delta)
            except Exception as e:
                event_queue.put(Delta(
                    id=str(uuid4()),
                    event=DeltaEvent.ERROR,
                    payload={"message": str(e)},
                ))
            finally:
                event_queue.put(None)

        thread: threading.Thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        self.renderer.start_stream()

        try:
            while True:
                delta: Delta | None = event_queue.get()
                if delta is None:
                    break
                self.renderer.render_delta(delta)
        except KeyboardInterrupt:
            self.agent.abort_stream()
            # 排空队列，等待子线程结束
            while True:
                delta = event_queue.get()
                if delta is None:
                    break
            self.renderer.show_info("\n[已中止]")

        self.renderer.finish_stream()
