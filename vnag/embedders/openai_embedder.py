import numpy as np
from numpy.typing import NDArray

from openai import OpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse

from vnag.embedder import BaseEmbedder


class OpenaiEmbedder(BaseEmbedder):
    """OpenAI Embedding API 适配器"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str = "qwen/qwen3-embedding-8b",
        batch_size: int = 100,
    ) -> None:
        """初始化 OpenAI Embedding

        参数:
            api_key: OpenAI API Key
            base_url: API 基础 URL
            model_name: 模型名称（默认 qwen/qwen3-embedding-8b）
            batch_size: 批量大小（建议不超过 100）
        """
        # 设置模型名称
        self.model_name: str = model_name
        # 设置批量大小
        self.batch_size: int = batch_size

        # 创建 OpenAI 客户端（由 SDK 自动处理重试）
        self.client: OpenAI = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def encode(self, texts: list[str]) -> NDArray[np.float32]:
        """编码文本为向量"""
        embeddings: list[list[float]] = []

        # 分批编码
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self._encode_batch(batch)
            embeddings.extend(batch_embeddings)

        return np.array(embeddings, dtype=np.float32)

    def _encode_batch(self, batch: list[str]) -> list[list[float]]:
        """批量编码（由 OpenAI SDK 自动重试）"""
        # 使用 OpenAI SDK 调用 embeddings API
        response: CreateEmbeddingResponse = self.client.embeddings.create(
            model=self.model_name,
            input=batch
        )

        # 提取 embedding 向量
        return [item.embedding for item in response.data]
