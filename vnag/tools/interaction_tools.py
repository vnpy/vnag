"""与用户交互的本地工具。"""

from vnag.interaction import AskPayload, get_ask_handler
from vnag.local import LocalTool


def _normalize_choices(choices: list[str] | None) -> list[str] | None:
    """规范化选项列表。"""
    if choices is None:
        return None

    normalized: list[str] = []
    for item in choices:
        text: str = item.strip()
        if not text:
            raise ValueError("选项内容不能为空。")
        normalized.append(text)

    return normalized or None


def ask_user(
    question: str,
    choices: list[str] | None = None,
    allow_other: bool = False,
) -> str:
    """
    向用户提问，并返回用户输入的纯文本答案。

    `choices` 为空时表示开放式问题；有 `choices` 时表示选项式问题。
    选项式问题最终返回选中项原文，而不是编号。
    当 `allow_other=True` 时，用户也可以输入选项之外的其他内容。
    """
    text: str = question.strip()
    if not text:
        return "错误：问题内容不能为空。"

    try:
        normalized_choices: list[str] | None = _normalize_choices(choices)
    except ValueError as exc:
        return f"错误：{exc}"

    if normalized_choices is not None and len(normalized_choices) < 2:
        return "错误：选项模式至少需要 2 个选项。"

    handler = get_ask_handler()
    if handler is None:
        return "ask_user 在当前环境不可用：未配置交互处理器"

    payload: AskPayload = AskPayload(
        question=text,
        choices=normalized_choices,
        allow_other=allow_other,
    )
    return handler(payload)


# 工具注册
ask_user_tool: LocalTool = LocalTool(ask_user)
