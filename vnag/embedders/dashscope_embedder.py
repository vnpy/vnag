import time

import dashscope
from dashscope import TextEmbedding
import numpy as np
from numpy.typing import NDArray

from vnag.embedder import BaseEmbedder


class DashscopeEmbedder(BaseEmbedder):
    """阿里云 DashScope Embedding API 适配器"""

    default_name: str = "DashScope"
    default_setting: dict = {
        "api_key": "",
        "model_name": "text-embedding-v3",
    }

    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-v3",
        batch_size: int = 10,
        max_retries: int = 3
    ) -> None:
        """初始化 DashScope Embedding

        参数:
            api_key: DashScope API Key
            model_name: 模型名称
            batch_size: 批量大小（DashScope 限制最大 10）
            max_retries: 最大重试次数
        """
        # 设置 API Key
        dashscope.api_key = api_key
        # 设置模型名称
        self.model_name: str = model_name
        # 设置批量大小
        self.batch_size: int = min(batch_size, 10)
        # 设置最大重试次数
        self.max_retries: int = max_retries

    def encode(self, texts: list) -> NDArray[np.float32]:
        """编码文本为向量"""
        embeddings: list = []

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
                response: dashscope.TextEmbeddingResponse = TextEmbedding.call(
                    model=self.model_name,
                    input=batch
                )

                if response.status_code == 200:
                    return [
                        item['embedding']
                        for item in response.output['embeddings']
                    ]
                else:
                    last_error = (
                        f"status_code={response.status_code}, "
                        f"message={response.message}"
                    )

            except Exception as e:
                last_error = str(e)

            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)

        raise RuntimeError(
            f"DashScope API 调用失败（重试 {self.max_retries} 次）: "
            f"{last_error}"
        )
