"""
进程内待办列表工具。
"""

from dataclasses import dataclass, field
from uuid import uuid4

from vnag.local import LocalTool


@dataclass
class TodoListState:
    """待办列表状态。"""

    steps: dict[int, str]
    done: set[int] = field(default_factory=set)


_todo_lists: dict[str, TodoListState] = {}


def _parse_steps(raw_steps: dict[str, str]) -> dict[int, str]:
    """解析并校验步骤映射。"""
    if not raw_steps:
        raise ValueError("步骤列表不能为空。")

    steps: dict[int, str] = {}

    for raw_id, content in raw_steps.items():
        try:
            step_id: int = int(raw_id)
        except ValueError as exc:
            raise ValueError(f"步骤编号 '{raw_id}' 不是有效整数。") from exc

        if step_id <= 0:
            raise ValueError(f"步骤编号 '{raw_id}' 必须大于 0。")

        text: str = content.strip()
        if not text:
            raise ValueError(f"步骤 {step_id} 的内容不能为空。")

        if step_id in steps:
            raise ValueError(f"步骤编号 {step_id} 重复。")

        steps[step_id] = text

    return steps


def _get_todos(list_id: str) -> TodoListState | None:
    """根据 list_id 获取待办列表。"""
    return _todo_lists.get(list_id)


def _render_todos(list_id: str, todo_list: TodoListState) -> str:
    """渲染待办列表为固定格式文本。"""
    lines: list[str] = [f"list_id={list_id}"]

    for step_id in sorted(todo_list.steps):
        mark: str = "x" if step_id in todo_list.done else " "
        content: str = todo_list.steps[step_id]
        lines.append(f"[{mark}] {step_id}. {content}")

    return "\n".join(lines)


def init_todos(steps: dict[str, str]) -> str:
    """
    初始化一份新的待办列表。

    Args:
        steps: 步骤映射，键为可转换为正整数的字符串编号，值为步骤内容。

    Returns:
        包含 list_id 和完整步骤状态的文本。后续调用 update_todos 和
        read_todos 时，必须传入这里返回的同一个 list_id。
    """
    try:
        parsed_steps: dict[int, str] = _parse_steps(steps)
    except ValueError as exc:
        return f"错误：{exc}"

    list_id: str = str(uuid4())
    todo_list: TodoListState = TodoListState(steps=parsed_steps)
    _todo_lists[list_id] = todo_list
    return _render_todos(list_id, todo_list)


def update_todos(list_id: str, step_id: int) -> str:
    """
    将指定步骤标记为已完成。

    Args:
        list_id: 由 init_todos 返回的待办列表编号。
        step_id: 要标记完成的步骤编号。

    Returns:
        更新后的完整待办列表文本。重复标记已完成步骤也会成功。
    """
    todo_list: TodoListState | None = _get_todos(list_id)
    if todo_list is None:
        return f"错误：未找到待办列表 '{list_id}'。"

    if step_id not in todo_list.steps:
        return f"错误：步骤 {step_id} 不存在。"

    todo_list.done.add(step_id)
    return _render_todos(list_id, todo_list)


def read_todos(list_id: str) -> str:
    """
    读取待办列表当前状态。

    Args:
        list_id: 由 init_todos 返回的待办列表编号。

    Returns:
        包含 list_id 以及各步骤完成状态的文本摘要。
    """
    todo_list: TodoListState | None = _get_todos(list_id)
    if todo_list is None:
        return f"错误：未找到待办列表 '{list_id}'。"

    return _render_todos(list_id, todo_list)


# 注册工具
init_todos_tool: LocalTool = LocalTool(init_todos)

update_todos_tool: LocalTool = LocalTool(update_todos)

read_todos_tool: LocalTool = LocalTool(read_todos)
