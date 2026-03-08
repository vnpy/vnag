import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loguru import Logger, Record
from loguru import logger

from .object import Request, Delta, Message, ToolCall, ToolResult
from .utility import get_folder_path


_CONSOLE_FORMAT: str = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[profile_name]}</cyan> | "
    "<level>{message}</level>"
)

_FILE_FORMAT: str = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{extra[profile_name]} | "
    "{message}"
)


# setup_logging() 通过 _initialized 保证全局 handler 只注册一次；
_initialized: bool = False


# 按 session_id 追踪文件 sink 的 handler ID，用于去重和移除。
_file_sink_map: dict[str, int] = {}


def _is_vnag_record(record: "Record") -> bool:
    """判断日志记录是否来自 vnag 模块。"""
    return record["extra"].get("vnag_module") is True


def _is_session_record(record: "Record", session_id: str) -> bool:
    """判断日志记录是否来自 vnag 模块的指定会话。"""
    return _is_vnag_record(record) and record["extra"].get("session_id") == session_id


def _make_session_filter(session_id: str) -> Callable[["Record"], bool]:
    """创建指定会话的日志过滤函数。"""
    def _filter(record: "Record") -> bool:
        return _is_session_record(record, session_id)
    return _filter


def setup_logging(*, enable_console: bool = True) -> None:
    """
    初始化 vnag 日志系统，应在应用入口处调用一次。

    若未显式调用，LogTracer 首次实例化时会以默认参数自动初始化。

    Args:
        enable_console: 是否将日志输出到终端（CLI 模式应设为 False）。
    """
    global _initialized

    if _initialized:
        return

    # 移除 loguru 默认 handler，避免 DEBUG 日志输出到 stderr
    try:
        logger.remove(0)
    except ValueError:
        pass

    if enable_console:
        logger.add(
            sys.stdout,
            level="INFO",
            filter=_is_vnag_record,
            format=_CONSOLE_FORMAT,
        )

    _initialized = True


def _add_file_sink(session_id: str) -> None:
    """为指定会话添加文件日志 sink（同一 session 只添加一次）。"""
    if session_id in _file_sink_map:
        return

    log_path: Path = get_folder_path("log")
    file_path: Path = log_path / f"{session_id}.log"

    handler_id: int = logger.add(
        file_path,
        level="DEBUG",
        filter=_make_session_filter(session_id),
        format=_FILE_FORMAT,
    )
    _file_sink_map[session_id] = handler_id


def remove_file_sink(session_id: str) -> None:
    """移除指定会话的文件日志 sink。"""
    handler_id: int | None = _file_sink_map.pop(session_id, None)
    if handler_id is not None:
        try:
            logger.remove(handler_id)
        except ValueError:
            pass


class LogTracer:
    """
    使用 loguru 库记录日志信息的追踪器。
    """

    def __init__(self, session_id: str, profile_name: str) -> None:
        """
        初始化追踪器，绑定会话上下文并注册对应的文件日志 sink。

        Args:
            session_id: 会话唯一标识，用于日志文件命名和 filter 隔离。
            profile_name: 智能体 Profile 名称，会出现在日志的上下文字段中。
        """
        self.session_id: str = session_id
        self.profile_name: str = profile_name

        # 确保全局日志已初始化（入口未调用时按默认参数兜底）
        setup_logging()

        # 绑定上下文字段；vnag_module=True 用于 filter，
        # 确保只有 vnag 自身的日志被 handler 捕获，不影响宿主应用的其他 loguru 日志。
        self.logger: Logger = logger.bind(
            session_id=self.session_id,
            profile_name=self.profile_name,
            vnag_module=True,
        )

        _add_file_sink(self.session_id)

    def on_llm_start(self, request: Request) -> None:
        """记录 LLM 调用开始事件。"""
        self.logger.info(f"LLM -> 请求已发送 (模型: {request.model})")
        self.logger.debug(f"LLM -> 完整请求数据: {request.model_dump_json(indent=4)}")

    def on_llm_delta(self, delta: Delta) -> None:
        """记录 LLM 返回流式数据块（Delta）事件。"""
        self.logger.trace(f"LLM -> 收到数据块: {delta.model_dump_json(indent=4)}")

    def on_llm_end(self, message: Message) -> None:
        """记录 LLM 调用结束事件。"""
        self.logger.info("LLM <- 响应已接收")
        self.logger.debug(f"LLM <- 完整响应数据: {message.model_dump_json(indent=4)}")

    def on_tool_start(self, tool_call: ToolCall) -> None:
        """记录工具调用开始事件。"""
        self.logger.info(f"工具 -> 开始执行: {tool_call.name}")
        self.logger.debug(f"工具 -> 调用参数: {tool_call.arguments}")

    def on_tool_end(self, result: ToolResult) -> None:
        """记录工具调用结束事件。"""
        self.logger.info(f"工具 <- 执行完毕: {result.name}")
        self.logger.debug(f"工具 <- 返回结果: {result.content}")
