from abc import ABC, abstractmethod
from collections.abc import Generator


class BaseEngine(ABC):
    """引擎基类：负责业务编排（历史、RAG、附件等），对外提供 send_message。"""

    @abstractmethod
    def send_message(
        self,
        message: str,
        model_name: str,
        use_rag: bool = True,
        user_files: list[str] | None = None,
        **kwargs: object,
    ) -> Generator:
        """对外统一接口：完成消息准备后调用网关流式输出。"""
        pass
