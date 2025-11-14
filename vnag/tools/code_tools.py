import subprocess
import sys
from pathlib import Path

from vnag.local import LocalTool


def execute_file(path: str, timeout: int = 30) -> str:
    """
    在独立的进程中执行指定路径的Python文件。

    安全警告:
        此函数执行文件中的代码，并未提供一个安全的沙箱环境。
        请仅对可信文件使用此功能。被执行的代码将拥有与主进程相同的权限，
        包括文件系统和网络访问权限。

    参数:
        path (str): 需要执行的Python文件的路径。
        timeout (int): 执行超时时间，单位为秒，默认为30秒。

    返回:
        str: 执行过程中产生的标准输出（stdout）和标准错误（stderr）的合并结果，或一条错误信息。
    """
    file_path: Path = Path(path)
    if not file_path.is_file():
        return f"错误: 在路径 {path} 未找到文件"

    try:
        process: subprocess.CompletedProcess = subprocess.run(
            [sys.executable, str(file_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            encoding="utf-8"
        )

        output: str = ""

        if process.stdout:
            output += f"--- STDOUT ---\n{process.stdout}\n"

        if process.stderr:
            output += f"--- STDERR ---\n{process.stderr}\n"

        if not output:
            return "执行完成，无输出。"

        return output.strip()
    except subprocess.TimeoutExpired:
        return f"错误: 执行超过{timeout}秒，已超时。"
    except Exception as e:
        return f"发生未知错误: {e}"


def execute_code(code: str, timeout: int = 30) -> str:
    """
    在独立的进程中执行Python代码字符串。

    安全警告:
        此函数执行任意代码，并未提供一个安全的沙箱环境。
        请仅对可信代码使用此功能。被执行的代码将拥有与主进程相同的权限，
        包括文件系统和网络访问权限。

    参数:
        code (str): 需要执行的Python代码字符串。
        timeout (int): 执行超时时间，单位为秒，默认为30秒。

    返回:
        str: 执行过程中产生的标准输出（stdout）和标准错误（stderr）的合并结果，或一条错误信息。
    """
    try:
        process: subprocess.CompletedProcess = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            encoding="utf-8"
        )

        output: str = ""

        if process.stdout:
            output += f"--- STDOUT ---\n{process.stdout}\n"

        if process.stderr:
            output += f"--- STDERR ---\n{process.stderr}\n"

        if not output:
            return "执行完成，无输出。"

        return output.strip()
    except subprocess.TimeoutExpired:
        return f"错误: 执行超过{timeout}秒，已超时。"
    except Exception as e:
        return f"发生未知错误: {e}"


# 注册工具
execute_file_tool: LocalTool = LocalTool(execute_file)

execute_code_tool: LocalTool = LocalTool(execute_code)
