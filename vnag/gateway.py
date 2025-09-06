from abc import ABC, abstractmethod
from collections.abc import Generator


class BaseGateway(ABC):
    """网关基类：仅负责将已准备好的 messages 发给模型并返回流式结果。"""

    @abstractmethod
    def init(self, base_url: str, api_key: str) -> bool:
        """初始化连接或客户端，返回是否成功。"""
        pass

    @abstractmethod
    def invoke_streaming(
        self,
        messages: list[dict[str, str]],
        model_name: str,
        **kwargs: object,
    ) -> Generator:
        """流式调用接口：将已准备好的消息发送给模型并逐步产出文本。"""
        pass
