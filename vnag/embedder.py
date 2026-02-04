from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from numpy.typing import NDArray


class BaseEmbedder(ABC):
    """嵌入器（Embedding）的抽象基类"""

    default_name: str = ""
    default_setting: dict[str, Any] = {}

    @abstractmethod
    def encode(self, texts: list[str]) -> NDArray[np.float32]:
        """将文本列表编码为向量"""
        pass
