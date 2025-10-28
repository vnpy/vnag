from abc import ABC, abstractmethod

import numpy as np
from numpy.typing import NDArray


class BaseEmbedding(ABC):
    """Embedding 模型的抽象基类"""

    @abstractmethod
    def encode(self, texts: list[str]) -> NDArray[np.float32]:
        """将文本列表编码为向量"""
        pass
