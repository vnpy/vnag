"""UI 专属工具模块"""
from pathlib import Path
from importlib import import_module
from glob import glob
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vnag.engine import AgentEngine


def register_all(engine: "AgentEngine") -> None:
    """注册所有 UI 专属工具到引擎

    自动扫描当前目录下的所有 .py 文件，查找 LocalTool 实例并注册。

    Args:
        engine: AgentEngine 实例
    """
    from vnag.local import LocalTool

    folder: Path = Path(__file__).parent

    for filepath in glob(str(folder / "*.py")):
        filename: str = Path(filepath).stem

        # 跳过 __init__.py 等特殊文件
        if filename.startswith("_"):
            continue

        module_name: str = f"vnag.ui.tools.{filename}"

        try:
            module = import_module(module_name)

            for name in dir(module):
                value = getattr(module, name)
                if isinstance(value, LocalTool):
                    engine.register_tool(value)
        except Exception:
            pass
