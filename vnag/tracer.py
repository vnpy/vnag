import sys
from pathlib import Path

from loguru import logger

from .object import Request, Delta, Message, ToolCall, ToolResult
from .utility import get_folder_path


# 配置全局日志记录器
logger.remove()

# 配置默认的 extra 值，避免其他模块使用 logger 时缺少 profile_name
logger.configure(extra={"profile_name": "General"})

logger.add(
    sys.stdout,
    level="INFO",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[profile_name]}</cyan> | "
        "<level>{message}</level>"
    )
)


class LogTracer:
    """
    使用 loguru 库记录日志信息的追踪器。
    """

    def __init__(self, session_id: str, profile_name: str) -> None:
        """初始化，配置 logger。"""
        self.session_id: str = session_id
        self.profile_name: str = profile_name

        self.logger = logger.bind(
            session_id=self.session_id,
            profile_name=self.profile_name
        )

        log_path: Path = get_folder_path("log")
        file_name: str = f"{self.session_id}.log"
        file_path: Path = log_path.joinpath(file_name)

        logger.add(
            file_path,
            level="DEBUG",
            filter=lambda record: record["extra"].get("session_id") == self.session_id,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{extra[profile_name]} | "
                "{message}"
            )
        )

    def on_llm_start(self, request: Request) -> None:
        """记录 LLM 调用开始事件。"""
        self.logger.info(f"LLM -> 请求已发送 (模型: {request.model})")
        self.logger.debug(f"LLM -> 完整请求数据: {request.model_dump_json(indent=4)}")

    def on_llm_delta(self, delta: Delta) -> None:
        """在 LLM 返回流式数据块（Delta）时运行。"""
        # 注意：频繁调用可能产生大量日志，默认设为 TRACE 级别
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
