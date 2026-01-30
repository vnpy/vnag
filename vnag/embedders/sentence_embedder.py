import numpy as np
from numpy.typing import NDArray

from sentence_transformers import SentenceTransformer

from vnag.embedder import BaseEmbedder


class SentenceEmbedder(BaseEmbedder):
    """SentenceTransformer 本地模型适配器"""

    default_name: str = "Sentence"
    default_setting: dict = {
        "model_name": "BAAI/bge-large-zh-v1.5",
    }

    def __init__(self, model_name: str = "BAAI/bge-large-zh-v1.5") -> None:
        """初始化 SentenceTransformer 模型"""
        self.model: SentenceTransformer = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> NDArray[np.float32]:
        """编码文本为向量"""
        return self.model.encode(texts)
