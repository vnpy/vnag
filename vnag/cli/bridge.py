"""后台线程桥接：在子线程中消费 TaskAgent.stream()，通过队列向主线程投递事件"""

import queue
import threading
from uuid import uuid4
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML

from ..agent import TaskAgent
from ..constant import DeltaEvent
from ..interaction import get_ask_handler, set_ask_handler
from ..object import Delta
from .ask import AskCoordinator
from .renderer import Renderer


class StreamBridge:
    """桥接 TaskAgent.stream() 与 CLI 渲染"""

    def __init__(self, agent: TaskAgent, renderer: Renderer) -> None:
        """构造函数"""
        self.agent: TaskAgent = agent
        self.renderer: Renderer = renderer

    def run(self, prompt: str, session: PromptSession) -> None:
        """
        阻塞式运行一轮对话

        在子线程中消费 stream()，主线程从队列取出 Delta 并渲染。
        Ctrl+C 时调用 agent.abort_stream() 中止。
        """
        event_queue: queue.Queue[Delta | None] = queue.Queue()
        answer_queue: queue.Queue[str] = queue.Queue()
        coordinator: AskCoordinator = AskCoordinator(event_queue, answer_queue)
        old_handler = get_ask_handler()
        set_ask_handler(coordinator)

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
                if delta.event == DeltaEvent.ASK_USER:
                    self.renderer.render_ask_prompt(delta.payload)
                    try:
                        answer: str = self._prompt_ask(session, delta.payload)
                    except KeyboardInterrupt:
                        self._abort_run(coordinator, event_queue)
                        break

                    coordinator.submit(answer)
                    continue

                self.renderer.render_delta(delta)
        except KeyboardInterrupt:
            self._abort_run(coordinator, event_queue)
        finally:
            set_ask_handler(old_handler)
            self.renderer.finish_stream()

    def _abort_run(
        self,
        coordinator: AskCoordinator,
        event_queue: queue.Queue[Delta | None],
    ) -> None:
        """中止当前轮次，并清理等待中的 ask 状态。"""
        self.agent.abort_stream()
        if coordinator.is_waiting():
            coordinator.cancel()
        self._drain_queue(event_queue)
        self.renderer.show_info("\n[已中止]")

    def _drain_queue(self, event_queue: queue.Queue[Delta | None]) -> None:
        """排空事件队列，等待工作线程结束。"""
        while True:
            delta: Delta | None = event_queue.get()
            if delta is None:
                break

    def _prompt_ask(
        self,
        session: PromptSession,
        payload: dict[str, Any],
    ) -> str:
        """读取并校验 ask_user 的用户输入。"""
        choices: list[str] | None = payload.get("choices")
        allow_other: bool = bool(payload.get("allow_other", False))

        while True:
            raw: str = session.prompt(
                HTML("<ansicyan><b>回答 › </b></ansicyan>")
            ).strip()

            if not choices:
                return raw

            success: bool
            answer: str
            success, answer = self._resolve_choice(raw, choices, allow_other)
            if success:
                return answer

            self.renderer.show_info("请输入有效选项编号或选项原文。")

    def _resolve_choice(
        self,
        raw: str,
        choices: list[str],
        allow_other: bool,
    ) -> tuple[bool, str]:
        """将用户输入解析为最终答案。"""
        if raw.isdigit():
            index: int = int(raw) - 1
            if 0 <= index < len(choices):
                return True, choices[index]

        for choice in choices:
            if raw == choice:
                return True, choice

        if allow_other and raw:
            return True, raw

        return False, ""
