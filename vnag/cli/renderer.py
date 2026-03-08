"""CLI 渲染器：将结构化 Delta 渲染为终端输出"""

from rich.console import Console
from rich.rule import Rule

from ..constant import DeltaEvent
from ..object import Delta
from ..agent import TaskAgent


class Renderer:
    """CLI 渲染器"""

    def __init__(self) -> None:
        """构造函数"""
        self.console: Console = Console()

        # 流式内容缓冲区
        self._content_buffer: str = ""
        self._thinking_buffer: str = ""

    def show_welcome(self, agent: TaskAgent) -> None:
        """显示欢迎信息"""
        self.console.print()
        self.console.print("  ✻ VeighNa Agent", style="bold blue")
        self.console.print(f"  Profile: {agent.profile.name}", style="dim")
        self.console.print(f"  Model:   {agent.model or '未设置'}", style="dim")
        self.console.print(f"  Session: {agent.name}", style="dim")
        self.console.print("  输入 /help 查看命令", style="dim")
        self.console.print()

    def start_stream(self) -> None:
        """流式输出开始"""
        self._content_buffer = ""
        self._thinking_buffer = ""

    def render_delta(self, delta: Delta) -> None:
        """渲染单个 Delta"""
        # 思考内容：标题 + dim 样式流式输出
        if delta.thinking:
            if not self._thinking_buffer:
                self.console.print("  ⏵ Thinking…", style="dim italic")
            self._thinking_buffer += delta.thinking
            self.console.print(
                delta.thinking, style="dim", end="",
                highlight=False, markup=False,
            )

        # 正文内容
        if delta.content:
            if self._thinking_buffer and not self._content_buffer:
                self.console.print()
                self.console.print()
            self._content_buffer += delta.content
            self.console.print(
                delta.content, end="",
                highlight=False, markup=False,
            )

        # 结构化事件
        if delta.event == DeltaEvent.TOOL_START:
            name: str = delta.payload["name"]
            self.console.print(f"\n  ⟡ 执行工具: {name}", style="yellow")

        elif delta.event == DeltaEvent.TOOL_END:
            name = delta.payload["name"]
            success: bool = delta.payload["success"]
            style: str = "green" if success else "red"
            mark: str = "✓" if success else "✗"
            self.console.print(f"    {mark} {name}", style=style)

        elif delta.event == DeltaEvent.WARNING:
            msg: str = delta.payload["message"]
            self.console.print(f"\n  ⚠ {msg}", style="bold yellow")

        elif delta.event == DeltaEvent.ERROR:
            msg = delta.payload["message"]
            self.console.print(f"\n  ✗ {msg}", style="bold red")

    def finish_stream(self) -> None:
        """流式输出结束"""
        self.console.print()
        self.console.print(Rule(style="dim"))

    def show_info(self, text: str) -> None:
        """显示提示信息"""
        self.console.print(text, style="dim")

    def show_error(self, text: str) -> None:
        """显示错误信息"""
        self.console.print(text, style="bold red")

    def show_goodbye(self) -> None:
        """显示退出信息"""
        self.console.print("\n再见。", style="dim")
