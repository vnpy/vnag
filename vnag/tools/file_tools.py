"""
常用的文件系统函数工具
"""
from collections.abc import Callable
import traceback
from pathlib import Path

import chardet

from vnag.utility import load_json, save_json
from vnag.local import LocalTool


# 配置文件名称
SETTING_NAME: str = "tool_filesystem.json"

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


def _detect_encoding(raw: bytes) -> str:
    """
    使用 chardet 检测字节内容编码。
    """
    if not raw:
        return "utf-8"

    result: chardet.ResultDict = chardet.detect(raw)
    encoding: str | None = result.get("encoding")
    return encoding if encoding else "utf-8"


def _get_encoding(path: Path) -> str:
    """
    使用 chardet 检测文件编码。
    如果文件不存在或为空，则默认为 utf-8。
    """
    if not path.is_file() or path.stat().st_size == 0:
        return "utf-8"

    with open(path, "rb") as f:
        raw_data: bytes = f.read()
        return _detect_encoding(raw_data)


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


def _resolve_allowed_path(
    path: str,
    allowed_checker: Callable[[Path], bool],
    action: str,
) -> Path:
    """
    解析并校验路径权限。
    """
    target_path: Path = Path(path)
    if not allowed_checker(target_path):
        raise PermissionError(f"没有权限{action}路径 '{path}'。")

    return target_path.resolve()


def _resolve_file(
    path: str,
    allowed_checker: Callable[[Path], bool],
    action: str,
) -> Path:
    """
    解析路径、校验权限，并确保目标为文件。
    """
    abs_path: Path = _resolve_allowed_path(path, allowed_checker, action)
    if not abs_path.is_file():
        raise ValueError(f"路径 '{path}' 不是一个有效的文件。")

    return abs_path


def _load_text_file(abs_path: Path) -> tuple[str, str]:
    """
    按检测到的编码读取文本文件，并返回内容与编码。
    """
    encoding: str = _get_encoding(abs_path)
    with open(abs_path, encoding=encoding) as f:
        return f.read(), encoding


def _read_text_safe(abs_path: Path) -> str:
    """
    读取文本文件，并拒绝包含空字节的明显二进制内容。
    """
    raw: bytes = abs_path.read_bytes()
    if b"\x00" in raw:
        raise ValueError("二进制文件不可读（或包含空字节）。")

    encoding: str = _detect_encoding(raw)
    return raw.decode(encoding, errors="replace")


def list_directory(path: str) -> str:
    """
    列出指定路径下的文件和目录。
    必须拥有该目录或其父目录的读权限。
    """
    try:
        abs_path: Path = _resolve_allowed_path(path, _check_read_allowed, "访问")
        if not abs_path.is_dir():
            return f"错误：路径 '{path}' 不是一个有效的目录。"

        items: list[str] = [item.name for item in abs_path.iterdir()]
        return f"目录 '{path}' 下的内容:\n" + "\n".join(items)
    except PermissionError as exc:
        return f"错误：{exc}"
    except Exception:
        return f"列出目录时发生未知错误: {traceback.format_exc()}"


def read_file(path: str) -> str:
    """
    读取指定路径的文本文件内容。
    必须拥有该文件所在目录的读权限。
    """
    try:
        abs_path: Path = _resolve_file(path, _check_read_allowed, "读取")
        content, _ = _load_text_file(abs_path)
        return content
    except ValueError as exc:
        return f"错误：{exc}"
    except PermissionError as exc:
        return f"错误：{exc}"
    except Exception:
        return f"读取文件时发生未知错误: {traceback.format_exc()}"


def read_file_snippet(path: str, offset: int = 0, limit: int = 200) -> str:
    """
    按行读取文件片段，并返回带 1-based 行号的内容。

    参数:
        path: 目标文件路径。
        offset: 起始行索引，从 0 开始。
        limit: 返回行数，最大为 2000。
    """
    try:
        if offset < 0:
            return "错误：offset 不能小于 0。"
        if limit <= 0:
            return "错误：limit 必须大于 0。"

        abs_path: Path = _resolve_file(path, _check_read_allowed, "读取")
        text: str = _read_text_safe(abs_path)
        lines: list[str] = text.splitlines()
        snippet_limit: int = min(limit, 2000)
        chunk: list[str] = lines[offset: offset + snippet_limit]

        if not chunk:
            return f"选定范围内无内容（{path}）。"

        return "\n".join(
            f"{offset + index + 1:>6}\t{line}"
            for index, line in enumerate(chunk)
        )
    except ValueError as exc:
        return f"错误：{exc}"
    except PermissionError as exc:
        return f"错误：{exc}"
    except Exception:
        return f"读取文件片段时发生未知错误: {traceback.format_exc()}"


def write_file(path: str, content: str) -> str:
    """
    将文本内容写入到指定的文件。如果文件已存在，则会覆盖。
    必须拥有该文件所在目录的写权限。
    """
    try:
        abs_path: Path = _resolve_allowed_path(path, _check_write_allowed, "写入")
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        encoding: str = _get_encoding(abs_path)
        with open(abs_path, "w", encoding=encoding) as f:
            f.write(content)
        return f"成功将内容写入到文件 '{path}'。"
    except PermissionError as exc:
        return f"错误：{exc}"
    except Exception:
        return f"写入文件时发生未知错误: {traceback.format_exc()}"


def delete_file(path: str) -> str:
    """
    删除指定路径的文件。
    必须拥有该路径的写权限。
    """
    try:
        abs_path: Path = _resolve_file(path, _check_write_allowed, "访问")
        abs_path.unlink()
        return f"成功删除文件 '{path}'。"
    except ValueError as exc:
        return f"错误：{exc}"
    except PermissionError as exc:
        return f"错误：{exc}"
    except Exception:
        return f"删除文件时发生未知错误: {traceback.format_exc()}"


def check_file(path: str) -> str:
    """
    检查指定路径的文件是否存在，并返回基本信息。
    必须拥有该路径的读权限。

    参数:
        path (str): 要检查的文件路径。

    返回:
        str: 文件的存在状态和大小信息。
    """
    try:
        abs_path: Path = _resolve_allowed_path(path, _check_read_allowed, "访问")
        if abs_path.is_file():
            size: int = abs_path.stat().st_size
            return f"文件存在: '{path}' (大小: {size} 字节)"
        elif abs_path.is_dir():
            return f"路径存在但是目录: '{path}'"
        else:
            return f"文件不存在: '{path}'"
    except PermissionError as exc:
        return f"错误：{exc}"
    except Exception:
        return f"检查文件时发生未知错误: {traceback.format_exc()}"


def glob_files(path: str, pattern: str) -> str:
    """
    根据给定的模式和路径，匹配符合条件的文件。
    必须拥有该目录的读权限。
    """
    try:
        abs_path: Path = _resolve_allowed_path(path, _check_read_allowed, "访问")
        if not abs_path.is_dir():
            return f"错误：路径 '{path}' 不是一个有效的目录。"

        files: list[Path] = list(abs_path.glob(pattern))

        return f"符合模式 '{pattern}' 的文件:\n" + "\n".join([str(file.resolve()) for file in files])
    except PermissionError as exc:
        return f"错误：{exc}"
    except Exception:
        return f"匹配文件时发生未知错误: {traceback.format_exc()}"


def search_content(path: str, content: str) -> str:
    """
    在指定路径下搜索包含指定内容的文件。
    必须拥有该路径的读权限。
    """
    try:
        abs_path: Path = _resolve_allowed_path(path, _check_read_allowed, "访问")
        if abs_path.is_file():
            all_files: list[Path] = [abs_path]
        elif abs_path.is_dir():
            all_files = [file for file in abs_path.rglob("*") if file.is_file()]
        else:
            return f"错误：路径 '{path}' 不是一个有效的文件或目录。"

        files: list[Path] = []
        skipped_count: int = 0
        for file in all_files:
            encoding: str = _get_encoding(file)
            try:
                if content in file.read_text(encoding=encoding):
                    files.append(file)
            except Exception:
                skipped_count += 1

        result: str = (
            f"包含内容 '{content}' 的文件:\n"
            + "\n".join([str(file.resolve()) for file in files])
        )
        if skipped_count:
            result += f"\n已跳过 {skipped_count} 个不可读文件。"
        return result
    except PermissionError as exc:
        return f"错误：{exc}"
    except Exception:
        return f"搜索内容时发生未知错误: {traceback.format_exc()}"


def replace_content(
    path: str,
    old_content: str,
    new_content: str,
    *,
    replace_all: bool = True,
    expected_occurrences: int | None = None,
) -> str:
    """
    替换指定文件中的内容。

    必须拥有该文件所在目录的写权限。

    推荐用法:
        - 唯一替换: replace_all=True, expected_occurrences=1
        - 恰好 k 处全部替换: replace_all=True, expected_occurrences=k
        - 只替换第一处且必须唯一: replace_all=False, expected_occurrences=1
    """
    try:
        if old_content == "":
            return "错误：old_content 不能为空。"
        if expected_occurrences is not None and expected_occurrences < 0:
            return "错误：expected_occurrences 不能小于 0。"

        abs_path: Path = _resolve_file(path, _check_write_allowed, "访问")
        content, encoding = _load_text_file(abs_path)
        match_count: int = content.count(old_content)

        if (
            expected_occurrences is not None
            and match_count != expected_occurrences
        ):
            return (
                f"错误：文件 '{path}' 中共匹配 {match_count} 处，"
                f"预期为 {expected_occurrences} 处。"
            )

        if expected_occurrences == 0:
            return f"匹配次数为 0，文件 '{path}' 未修改。"

        if replace_all:
            updated_content: str = content.replace(old_content, new_content)
            replace_summary: str = "已全部替换"
        else:
            updated_content = content.replace(old_content, new_content, 1)
            replace_summary = "仅替换第一处"

        with open(abs_path, "w", encoding=encoding) as f:
            f.write(updated_content)

        return (
            f"成功替换文件 '{path}' 中的内容"
            f"（写前匹配 {match_count} 处，{replace_summary}）。"
        )
    except ValueError as exc:
        return f"错误：{exc}"
    except PermissionError as exc:
        return f"错误：{exc}"
    except Exception:
        return f"替换内容时发生未知错误: {traceback.format_exc()}"


def replace_line_block(
    path: str,
    start_line: int,
    end_line: int,
    new_content: str,
) -> str:
    """
    按 1-based 闭区间替换文件行块。

    会删除第 start_line 到 end_line 行，并在原位置插入 new_content。
    该工具会按统一换行重组内容，写回后可能改变原文件的换行风格。
    """
    try:
        if start_line < 1:
            return "错误：start_line 必须大于等于 1。"
        if end_line < start_line:
            return "错误：end_line 不能小于 start_line。"

        abs_path: Path = _resolve_file(path, _check_write_allowed, "访问")
        content, encoding = _load_text_file(abs_path)
        lines: list[str] = content.splitlines()

        if end_line > len(lines):
            return (
                f"错误：行号范围无效，文件 '{path}' "
                f"只有 {len(lines)} 行。"
            )

        insert_lines: list[str] = new_content.splitlines()
        updated_lines: list[str] = (
            lines[:start_line - 1] + insert_lines + lines[end_line:]
        )
        updated_content: str = "\n".join(updated_lines)

        with open(abs_path, "w", encoding=encoding) as f:
            f.write(updated_content)

        return f"成功替换文件 '{path}' 的第 {start_line} 到 {end_line} 行。"
    except ValueError as exc:
        return f"错误：{exc}"
    except PermissionError as exc:
        return f"错误：{exc}"
    except Exception:
        return f"按行替换内容时发生未知错误: {traceback.format_exc()}"


# 注册工具
list_directory_tool: LocalTool = LocalTool(list_directory)

read_file_tool: LocalTool = LocalTool(read_file)

read_file_snippet_tool: LocalTool = LocalTool(read_file_snippet)

write_file_tool: LocalTool = LocalTool(write_file)

delete_file_tool: LocalTool = LocalTool(delete_file)

check_file_tool: LocalTool = LocalTool(check_file)

glob_files_tool: LocalTool = LocalTool(glob_files)

search_content_tool: LocalTool = LocalTool(search_content)

replace_content_tool: LocalTool = LocalTool(replace_content)

replace_line_block_tool: LocalTool = LocalTool(replace_line_block)
