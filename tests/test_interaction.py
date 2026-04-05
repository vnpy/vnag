import threading
import unittest
from queue import Queue
from unittest.mock import MagicMock

from vnag.cli.bridge import StreamBridge
from vnag.constant import DeltaEvent
from vnag.cli.ask import AskCoordinator
from vnag.interaction import (
    AskPayload,
    get_ask_handler,
    set_ask_handler,
)
from vnag.tools import interaction_tools


class AskUserToolTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.old_handler = get_ask_handler()
        set_ask_handler(None)

    def tearDown(self) -> None:
        set_ask_handler(self.old_handler)

    def test_ask_user_returns_unavailable_without_handler(self) -> None:
        result = interaction_tools.ask_user("继续吗？")
        self.assertEqual(
            result,
            "ask_user 在当前环境不可用：未配置交互处理器",
        )

    def test_ask_user_normalizes_payload_before_calling_handler(self) -> None:
        captured: dict[str, AskPayload] = {}

        def handler(payload: AskPayload) -> str:
            captured["payload"] = payload
            return "继续"

        set_ask_handler(handler)

        result = interaction_tools.ask_user(
            "  请选择后续动作  ",
            [" 继续 ", " 退出 "],
            allow_other=True,
        )

        self.assertEqual(result, "继续")
        self.assertEqual(captured["payload"].question, "请选择后续动作")
        self.assertEqual(captured["payload"].choices, ["继续", "退出"])
        self.assertTrue(captured["payload"].allow_other)

    def test_ask_user_rejects_invalid_choices(self) -> None:
        result = interaction_tools.ask_user("请选择", ["  ", "继续"])
        self.assertEqual(result, "错误：选项内容不能为空。")

    def test_ask_user_treats_empty_choices_as_open_prompt(self) -> None:
        captured: dict[str, AskPayload] = {}

        def handler(payload: AskPayload) -> str:
            captured["payload"] = payload
            return "自定义输入"

        set_ask_handler(handler)

        result = interaction_tools.ask_user("请输入内容", [])

        self.assertEqual(result, "自定义输入")
        self.assertIsNone(captured["payload"].choices)


class AskCoordinatorTestCase(unittest.TestCase):
    def test_coordinator_emits_delta_and_returns_answer(self) -> None:
        out_queue: Queue = Queue()
        answer_queue: Queue = Queue()
        coordinator = AskCoordinator(out_queue, answer_queue)
        result: list[str] = []

        def worker() -> None:
            answer: str = coordinator(AskPayload("请选择", ["继续", "退出"]))
            result.append(answer)

        thread = threading.Thread(target=worker)
        thread.start()

        delta = out_queue.get(timeout=1)
        self.assertEqual(delta.event, DeltaEvent.ASK_USER)
        self.assertEqual(delta.payload["question"], "请选择")
        self.assertEqual(delta.payload["choices"], ["继续", "退出"])
        self.assertTrue(coordinator.is_waiting())

        coordinator.submit("继续")

        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, ["继续"])
        self.assertFalse(coordinator.is_waiting())

    def test_cancel_pending_only_sends_one_answer(self) -> None:
        out_queue: Queue = Queue()
        answer_queue: Queue = Queue()
        coordinator = AskCoordinator(out_queue, answer_queue)
        result: list[str] = []

        def worker() -> None:
            answer: str = coordinator(AskPayload("请选择", ["继续", "退出"]))
            result.append(answer)

        thread = threading.Thread(target=worker)
        thread.start()

        out_queue.get(timeout=1)
        coordinator.cancel()
        coordinator.submit("继续")

        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, [""])
        self.assertTrue(answer_queue.empty())


class StreamBridgeTestCase(unittest.TestCase):
    def test_resolve_choice_accepts_other_text(self) -> None:
        bridge = StreamBridge(MagicMock(), MagicMock())

        success, answer = bridge._resolve_choice(
            "稍后再说",
            ["继续", "退出"],
            True,
        )

        self.assertTrue(success)
        self.assertEqual(answer, "稍后再说")


if __name__ == "__main__":
    unittest.main()
