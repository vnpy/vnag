"""
常用的文件系统函数工具
"""
from pathlib import Path

from vnag.utility import load_json, save_json
from vnag.local import LocalTool


# 配置文件名称
SETTING_NAME: str = "file_system_tool.json"

# 默认配置
setting: dict[str, list[str]] = {
    "read_allowed": [],
    "write_allowed": []
}

# 从文件加载配置
_setting: dict[str, list[str]] = load_json(SETTING_NAME)
if _setting:
    setting.update(_setting)
else:
    save_json(SETTING_NAME, setting)

# 将配置中的路径字符串转换为绝对路径对象，以便进行可靠的比较
WRITE_ALLOWED_PATHS: set[Path] = {Path(p).resolve() for p in setting["write_allowed"]}

# 读取权限路径包含 "read_allowed" 和 "write_allowed" 中的所有路径
# 这样，用户只需将路径配置在 "write_allowed" 中，即可同时获得读写权限
ALL_READ_PATHS: set[Path] = {Path(p).resolve() for p in setting["read_allowed"]}.union(WRITE_ALLOWED_PATHS)


def _is_path_allowed(path_to_check: Path, allowed_paths: set[Path]) -> bool:
    """
    检查目标路径是否在任何一个允许的基准路径之下。
    """
    resolved_path: Path = path_to_check.resolve()

    for allowed_path in allowed_paths:
        # 检查目标路径是否是允许路径本身，或者是其子路径
        if (
            allowed_path == resolved_path
            or allowed_path in resolved_path.parents
        ):
            return True

    return False


def _check_read_allowed(path: Path) -> bool:
    """
    检查给定路径是否在任何允许读取的目录或其子目录中。
    """
    return _is_path_allowed(path, ALL_READ_PATHS)


def _check_write_allowed(path: Path) -> bool:
    """
    检查给定路径是否在任何允许写入的目录或其子目录中。
    """
    return _is_path_allowed(path, WRITE_ALLOWED_PATHS)


def list_directory(path: str) -> str:
    """
    列出指定路径下的文件和目录。
    必须拥有该目录或其父目录的读权限。
    """
    try:
        target_path: Path = Path(path)
        if not _check_read_allowed(target_path):
            return f"错误：没有权限访问路径 '{path}'。"

        abs_path: Path = target_path.resolve()
        if not abs_path.is_dir():
            return f"错误：路径 '{path}' 不是一个有效的目录。"

        items: list[str] = [item.name for item in abs_path.iterdir()]
        return f"目录 '{path}' 下的内容:\n" + "\n".join(items)
    except Exception as e:
        return f"列出目录时发生未知错误: {e}"


def read_file(path: str) -> str:
    """
    读取指定路径的文本文件内容。
    必须拥有该文件所在目录的读权限。
    """
    try:
        target_path: Path = Path(path)
        if not _check_read_allowed(target_path):
            return f"错误：没有权限读取路径 '{path}'。"

        abs_path: Path = target_path.resolve()
        if not abs_path.is_file():
            return f"错误：路径 '{path}' 不是一个有效的文件。"

        with open(abs_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取文件时发生未知错误: {e}"


def write_file(path: str, content: str) -> str:
    """
    将文本内容写入到指定的文件。如果文件已存在，则会覆盖。
    必须拥有该文件所在目录的写权限。
    """
    try:
        target_path: Path = Path(path)
        if not _check_write_allowed(target_path):
            return f"错误：没有权限写入路径 '{path}'。"

        abs_path: Path = target_path.resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"成功将内容写入到文件 '{path}'。"
    except Exception as e:
        return f"写入文件时发生未知错误: {e}"


# 注册工具
list_directory_tool: LocalTool = LocalTool(list_directory)

read_file_tool: LocalTool = LocalTool(read_file)

write_file_tool: LocalTool = LocalTool(write_file)
