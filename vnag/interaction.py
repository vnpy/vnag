"""交互工具共享模块。"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class AskPayload:
    """ask_user 工具的交互载荷。"""

    question: str
    choices: list[str] | None = None
    allow_other: bool = False

    def to_dict(self) -> dict[str, Any]:
        """转换为可放入 Delta 的字典。"""
        return {
            "question": self.question,
            "choices": list(self.choices) if self.choices else None,
            "allow_other": self.allow_other,
        }


AskHandler = Callable[[AskPayload], str]


_ask_handler: AskHandler | None = None


def set_ask_handler(handler: AskHandler | None) -> None:
    """设置 ask_user 处理函数。"""
    global _ask_handler
    _ask_handler = handler


def get_ask_handler() -> AskHandler | None:
    """获取当前 ask_user 处理函数。"""
    return _ask_handler
