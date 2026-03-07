"""
终端与系统级工具函数
"""
import locale
import os
import platform
import re
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

from vnag.local import LocalTool


_SENSITIVE_PATTERN: re.Pattern[str] = re.compile(
    r"(KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|PRIVATE)",
    re.IGNORECASE,
)


_MAX_OUTPUT_DEFAULT: int = 50000


def _get_shell_encoding() -> str:
    """根据平台返回 shell 输出最可能的编码。"""
    if platform.system() == "Windows":
        return locale.getpreferredencoding(False)
    return "utf-8"


def _truncate(text: str, max_length: int) -> str:
    """截断过长文本并附加提示。"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + f"\n... (输出已截断，原始长度 {len(text)} 字符)"


def _mask_value(value: str) -> str:
    """对敏感变量值脱敏：保留前 4 后 4 字符，中间用 **** 替代。"""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def run_shell(
    command: str,
    cwd: str = "",
    timeout: int = 300,
    max_output: int = _MAX_OUTPUT_DEFAULT,
) -> str:
    """
    通过系统默认 shell 执行命令并返回结果。

    Windows 下默认使用 cmd.exe，Linux/macOS 下默认使用 /bin/sh。

    安全警告:
        此函数执行任意命令，未提供沙箱环境。
        请仅对可信命令使用此功能。

    参数:
        command (str): 要执行的命令行命令。
        cwd (str): 工作目录路径。为空时使用当前目录。
        timeout (int): 超时时间（秒），默认300秒。
        max_output (int): 最大输出字符数，默认50000。超出部分将被截断。

    返回:
        str: 命令的标准输出、标准错误及退出码的合并结果。
    """
    if cwd:
        cwd_path: Path = Path(cwd)
        if not cwd_path.exists():
            return f"错误：工作目录 '{cwd}' 不存在。"
        if not cwd_path.is_dir():
            return f"错误：路径 '{cwd}' 不是一个目录。"

    try:
        work_dir: str | None = cwd if cwd else None
        encoding: str = _get_shell_encoding()

        process: subprocess.CompletedProcess = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True,
            check=False,
            cwd=work_dir,
            encoding=encoding,
            errors="replace",
        )

        output: str = ""
        if process.stdout:
            output += f"--- STDOUT ---\n{process.stdout}\n"
        if process.stderr:
            output += f"--- STDERR ---\n{process.stderr}\n"

        exit_line: str = f"--- EXIT CODE: {process.returncode} ---"

        if not output:
            return f"执行完成，无输出。\n{exit_line}"

        output = _truncate(output.strip(), max_output)
        return f"{output}\n{exit_line}"

    except subprocess.TimeoutExpired:
        return f"错误: 执行超过 {timeout} 秒，已超时。"
    except Exception:
        return f"发生未知错误: {traceback.format_exc()}"


def get_system_info() -> str:
    """
    获取当前操作系统的基础信息。

    返回 OS 类型及版本、CPU 架构、Python 版本和当前工作目录。
    Agent 可据此判断应使用 Windows 还是 Linux/macOS 风格的命令。

    返回:
        str: 系统环境信息的多行文本。
    """
    info_lines: list[str] = [
        f"OS: {platform.system()} {platform.release()} ({platform.version()})",
        f"Architecture: {platform.machine()}",
        f"Python: {sys.version}",
        f"Python executable: {sys.executable}",
        f"Current working directory: {os.getcwd()}",
    ]
    return "\n".join(info_lines)


def get_env_variable(name: str) -> str:
    """
    读取指定的系统环境变量的值。

    比 run_shell("echo %VAR%") 更可靠，无跨平台差异。
    对名称中包含 KEY、SECRET、TOKEN、PASSWORD 等敏感词的变量，
    将自动脱敏显示（仅保留前 4 和后 4 字符）。

    参数:
        name (str): 环境变量名称，例如 "PATH"、"PYTHONPATH"。

    返回:
        str: 环境变量的值（敏感变量已脱敏），若未设置则返回提示信息。
    """
    value: str | None = os.environ.get(name)
    if value is None:
        return f"环境变量 '{name}' 未设置。"

    if _SENSITIVE_PATTERN.search(name):
        return f"{name}={_mask_value(value)}"

    return f"{name}={value}"


def which_command(command: str) -> str:
    """
    查找可执行程序的完整路径。

    跨平台兼容，无需区分 where (Windows) 和 which (Linux/macOS)。
    可用于在执行命令前确认工具是否已安装。

    参数:
        command (str): 要查找的可执行程序名称，例如 "python"、"git"。

    返回:
        str: 可执行程序的完整路径，若未找到则返回提示信息。
    """
    path: str | None = shutil.which(command)
    if path is None:
        return f"未找到可执行程序: '{command}'"
    return f"{command}: {path}"


# 注册工具
run_shell_tool: LocalTool = LocalTool(run_shell)

get_system_info_tool: LocalTool = LocalTool(get_system_info)

get_env_variable_tool: LocalTool = LocalTool(get_env_variable)

which_command_tool: LocalTool = LocalTool(which_command)
