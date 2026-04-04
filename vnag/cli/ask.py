"""CLI ask_user 协调器。"""

from queue import Queue
import threading
from uuid import uuid4

from ..constant import DeltaEvent
from ..interaction import AskPayload
from ..object import Delta


class AskCoordinator:
    """CLI 主线程与工具线程之间的 ask_user 协调器。"""

    def __init__(
        self,
        out_queue: Queue[Delta | None],
        answer_queue: Queue[str],
    ) -> None:
        """构造函数。"""
        self.out_queue: Queue[Delta | None] = out_queue
        self.answer_queue: Queue[str] = answer_queue

        self._lock: threading.Lock = threading.Lock()
        self._waiting: bool = False
        self._answered: bool = False

    def __call__(self, payload: AskPayload) -> str:
        """投递 ASK_USER 事件，并阻塞等待答案。"""
        with self._lock:
            self._waiting = True
            self._answered = False

        self.out_queue.put(
            Delta(
                id=str(uuid4()),
                event=DeltaEvent.ASK_USER,
                payload=payload.to_dict(),
            )
        )

        try:
            return self.answer_queue.get()
        finally:
            with self._lock:
                self._waiting = False
                self._answered = False

    def submit(self, text: str) -> None:
        """提交答案，若当前无挂起问题则忽略。"""
        if self._claim_answer():
            self.answer_queue.put(text)

    def cancel(self) -> None:
        """取消挂起提问，使用空字符串唤醒等待方。"""
        if self._claim_answer():
            self.answer_queue.put("")

    def is_waiting(self) -> bool:
        """检查当前是否存在挂起提问。"""
        with self._lock:
            return self._waiting and not self._answered

    def _claim_answer(self) -> bool:
        """原子地标记答案已发送。"""
        with self._lock:
            if not self._waiting or self._answered:
                return False

            self._answered = True
            return True
