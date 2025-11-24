import time

from openai import OpenAI
import numpy as np
from numpy.typing import NDArray

from vnag.embedder import BaseEmbedder


class OpenaiEmbedder(BaseEmbedder):
    """OpenAI Embedding API 适配器"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str = "qwen/qwen3-embedding-8b",
        batch_size: int = 100,
        max_retries: int = 3,
        timeout: float = 60.0
    ) -> None:
        """初始化 OpenAI Embedding

        参数:
            api_key: OpenAI API Key
            model_name: 模型名称（默认 qwen/qwen3-embedding-8b）
            base_url: API 基础 URL
            batch_size: 批量大小（建议不超过 100）
            max_retries: 最大重试次数
            timeout: 请求超时时间（秒）
        """
        # 设置模型名称
        self.model_name: str = model_name
        # 设置批量大小
        self.batch_size: int = batch_size
        # 设置最大重试次数
        self.max_retries: int = max_retries

        # 创建 OpenAI 客户端
        self.client: OpenAI = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries
        )

    def encode(self, texts: list[str]) -> NDArray[np.float32]:
        """编码文本为向量"""
        embeddings: list[list[float]] = []

        # 分批编码
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self._encode_batch_with_retry(batch)
            embeddings.extend(batch_embeddings)

        return np.array(embeddings, dtype=np.float32)

    def _encode_batch_with_retry(self, batch: list[str]) -> list[list[float]]:
        """带重试的批量编码"""
        last_error: str = ""

        # 重试编码
        for attempt in range(self.max_retries):
            try:
                # 使用 OpenAI SDK 调用 embeddings API
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=batch
                )

                # 提取 embedding 向量
                return [item.embedding for item in response.data]

            except Exception as e:
                last_error = str(e)

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)

        raise RuntimeError(
            f"OpenAI API 调用失败（重试 {self.max_retries} 次）: "
            f"{last_error}"
        )
