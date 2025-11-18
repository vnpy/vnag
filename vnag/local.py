from collections.abc import Callable
from typing import Any, get_type_hints
from pathlib import Path
from types import ModuleType
from glob import glob
import inspect
import importlib
import traceback

from .object import ToolSchema


class LocalTool:
    """本地工具模板"""

    def __init__(
        self,
        function: Callable[..., Any],
        name: str = "",
        description: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """构造函数"""
        if name == "":
            name = function.__name__

        if description == "" and function.__doc__:
            description = function.__doc__

        if parameters is None:
            parameters = generate_function_schema(function)

        module: str = function.__module__.split(".")[-1]

        # 使用"-"替换"_"，和MCP保持一致
        name = name.replace("_", "-")
        module = module.replace("_", "-")

        self.name: str = f"{module}_{name}"
        self.description: str = description
        self.parameters: dict[str, Any] = parameters
        self.function: Callable[..., Any] = function

    def get_schema(self) -> ToolSchema:
        """获取工具的 Schema"""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.parameters
        )


class LocalManager:
    """本地工具管理器：负责本地工具的注册和执行"""

    def __init__(self) -> None:
        """构造函数"""
        self.tools: dict[str, LocalTool] = {}

        self.load_tools()

    def register_function(self, function: Callable[..., Any]) -> None:
        """注册函数"""
        tool: LocalTool = LocalTool(function)
        self.register_tool(tool)

    def register_tool(self, tool: LocalTool) -> None:
        """注册工具"""
        self.tools[tool.name] = tool

    def load_tools(self) -> None:
        """加载本地工具"""
        path_1: Path = Path(__file__).parent.joinpath("tools")
        self._load_tools_from_folder(path_1, "vnag.tools")

        path_2: Path = Path.cwd().joinpath("tools")
        self._load_tools_from_folder(path_2, "tools")

    def _load_tools_from_folder(self, folder_path: Path, module_name: str) -> None:
        """从文件夹加载本地工具"""
        pathname: str = str(folder_path.joinpath("*.py"))

        for filepath in glob(pathname):
            filename: str = Path(filepath).stem
            name: str = f"{module_name}.{filename}"
            self._load_tools_from_module(name)

    def _load_tools_from_module(self, module_name: str) -> None:
        """从模块加载本地工具"""
        try:
            module: ModuleType = importlib.import_module(module_name)

            for name in dir(module):
                value: Any = getattr(module, name)
                if isinstance(value, LocalTool):
                    self.register_tool(value)
        except Exception:
            msg: str = f"Local tool [{module_name}] load failed: {traceback.format_exc()}"
            print(msg)

    def list_tools(self) -> list[ToolSchema]:
        """列出所有已注册的本地工具"""
        return list([tool.get_schema() for tool in self.tools.values()])

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """执行本地工具"""
        tool: LocalTool | None = self.tools.get(tool_name)
        if not tool:
            return f"Error: Tool [{tool_name}] not found"

        try:
            result: Any = tool.function(**arguments)
            return str(result)
        except Exception as e:
            return f"Error executing tool [{tool_name}]: {str(e)}"


def convert_python_type(python_type: type[Any]) -> str:
    """将Python类型转换为JSON Schema类型"""
    type_mapping: dict[type[Any], str] = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    # 处理泛型类型（如 list[str]）
    origin: type[Any] | None = getattr(python_type, "__origin__", None)
    if origin is not None:
        python_type = origin

    return type_mapping.get(python_type, "string")


def generate_function_schema(func: Callable[..., Any]) -> dict[str, Any]:
    """从函数签名生成参数schema"""
    sig: inspect.Signature = inspect.signature(func)
    type_hints: dict[str, Any] = get_type_hints(func) if func.__annotations__ else {}

    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        # 获取类型
        param_type: type[Any] = type_hints.get(param_name, Any)
        json_type: str = convert_python_type(param_type)

        # 构建属性定义
        prop: dict[str, Any] = {"type": json_type}

        # 从默认值判断是否必需
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

        properties[param_name] = prop

    return {
        "type": "object",
        "properties": properties,
        "required": required
    }
