from abc import ABC, abstractmethod
from typing import Any
from collections.abc import Generator

from .object import Request, Response, Delta


class BaseGateway(ABC):
    """网关基类：仅负责将已准备好的 messages 发给模型并返回流式结果。"""

    default_name: str = ""

    default_setting: dict = {}

    @abstractmethod
    def init(self, setting: dict[str, Any]) -> bool:
        """初始化客户端"""
        pass

    @abstractmethod
    def invoke(self, request: Request) -> Response:
        """阻塞式调用接口"""
        pass

    @abstractmethod
    def stream(self, request: Request) -> Generator[Delta, None, None]:
        """流式调用接口，返回一个StreamChunk的生成器"""
        pass

    @abstractmethod
    def list_models(self) -> list[str]:
        """查询可用模型列表"""
        pass

    def write_log(self, text: str) -> None:
        """写入日志"""
        print(text)
