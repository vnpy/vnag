from abc import ABC, abstractmethod
from typing import Any

from .object import Segment


class BaseSegmenter(ABC):
    """
    文本分段器的抽象基类。

    该类定义了所有文本分段器需要遵循的接口。
    其核心职责是将长文本分割成一系列结构化的 `Segment` 对象。
    注意：本基类只负责分段逻辑，不涉及文件读取等 I/O 操作。
    """

    @abstractmethod
    def parse(self, text: str, metadata: dict[str, Any]) -> list[Segment]:
        """
        对传入的文本信息进行解析处理，返回处理好的 Segment 列表。

        参数:
            text: 待分段的原始文本。
            metadata: 与该文本关联的元数据字典，将被复制到每个生成的 Segment 中。

        返回:
            一个由 Segment 对象组成的列表，每个 Segment 代表一个文本片段。
        """
        pass

    @staticmethod
    def chunk_text(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
        """
        将长文本按固定大小切片（支持重叠），并返回所有非空片段的列表。

        参数:
            text: 待切分的原始文本。
            chunk_size: 每个片段的最大长度。
            overlap: 相邻片段之间重叠的字符数，默认为 0 (不重叠)。

        返回:
            一个由非空文本片段字符串组成的列表。

        注意:
            - 为了性能，片段内容保持原文，仅在判断是否为空白时执行 strip() 操作。
            - 所有完全由空白字符组成的片段都将被丢弃。
            - 切分的步长 `stride` 计算方式为 `max(1, chunk_size - overlap)`。
        """
        if chunk_size <= 0:
            return []

        # 计算切片步长，确保步长至少为 1
        stride: int = max(1, chunk_size - max(0, overlap))
        chunks: list[str] = []
        text_length: int = len(text)

        # 按照计算出的步长和分块大小进行切分
        for i in range(0, text_length, stride):
            chunk: str = text[i : i + chunk_size]
            if chunk.strip():  # 仅当片段包含非空白内容时才添加
                chunks.append(chunk)

        return chunks
