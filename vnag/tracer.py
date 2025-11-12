import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

from .object import Request, Delta, Message, ToolCall, ToolResult
from .utility import get_folder_path


class LogTracer:
    """
    使用 loguru 库记录日志信息的追踪器。
    """

    def __init__(self) -> None:
        """初始化，配置 logger。"""
        # 删除所有日志记录器
        logger.remove()

        # 添加 stdout 日志记录器，级别为 DEBUG
        logger.add(sys.stdout, level="DEBUG")

        # 将 DEBUG 级别的详细日志写入文件，不进行滚动和删除
        log_path: Path = get_folder_path("log")
        file_name: str = datetime.now().strftime("%Y%m%d_%H%M%S.log")
        file_path: Path = log_path.joinpath(file_name)
        logger.add(file_path, level="DEBUG")

    def on_llm_start(self, request: Request) -> None:
        """记录 LLM 调用开始事件。"""
        logger.info(f"LLM -> 请求已发送 (模型: {request.model})")
        logger.debug(f"LLM -> 完整请求数据: {request.model_dump_json(indent=4)}")

    def on_llm_delta(self, delta: Delta) -> None:
        """在 LLM 返回流式数据块（Delta）时运行。"""
        # 注意：频繁调用可能产生大量日志，默认设为 TRACE 级别
        logger.trace(f"LLM -> 收到数据块: {delta.model_dump_json(indent=4)}")

    def on_llm_end(self, message: Message) -> None:
        """记录 LLM 调用结束事件。"""
        logger.info("LLM <- 响应已接收")
        logger.debug(f"LLM <- 完整响应数据: {message.model_dump_json(indent=4)}")

    def on_tool_start(self, tool_call: ToolCall) -> None:
        """记录工具调用开始事件。"""
        logger.info(f"工具 -> 开始执行: {tool_call.name}")
        logger.debug(f"工具 -> 调用参数: {tool_call.arguments}")

    def on_tool_end(self, result: ToolResult) -> None:
        """记录工具调用结束事件。"""
        logger.info(f"工具 <- 执行完毕: {result.name}")
        logger.debug(f"工具 <- 返回结果: {result.content}")
