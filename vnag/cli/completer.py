"""CLI 输入补全器：支持斜杠命令补全和 @ 文件路径补全"""

from collections.abc import Iterable
from pathlib import Path

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document


# 支持的斜杠命令列表
COMMANDS: list[str] = [
    "/help", "/clear", "/model", "/profile",
    "/retry", "/sessions", "/title", "/stats", "/exit",
]


class CliCompleter(Completer):
    """CLI 输入补全器"""

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text: str = document.text_before_cursor

        # 斜杠命令补全
        if text.startswith("/"):
            for cmd in COMMANDS:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))
            return

        # @ 文件路径补全
        at_idx: int = text.rfind("@")
        if at_idx >= 0:
            partial: str = text[at_idx + 1:]
            yield from self._complete_path(partial)

    def _complete_path(self, partial: str) -> Iterable[Completion]:
        """补全文件路径"""
        cwd: Path = Path.cwd()

        try:
            if partial:
                parent: Path = cwd / Path(partial).parent
                prefix: str = Path(partial).name
            else:
                parent = cwd
                prefix = ""

            if not parent.is_dir():
                return

            for p in sorted(parent.iterdir()):
                if p.name.startswith("."):
                    continue
                if not p.name.startswith(prefix):
                    continue

                suffix: str = "/" if p.is_dir() else ""
                display: str = p.name + suffix
                full: str = str(p.relative_to(cwd)) + suffix
                yield Completion(
                    full,
                    start_position=-len(partial),
                    display=display,
                )
        except (OSError, ValueError):
            pass
