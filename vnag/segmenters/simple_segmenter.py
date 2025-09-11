from typing import Any

from vnag.object import Segment
from vnag.segmenter import BaseSegmenter


class SimpleSegmenter(BaseSegmenter):
    """
    一个简单的文本分段器，它按用户指定的固定长度切分文本，并支持重叠。

    该分段器适用于处理没有明显结构化特征的纯文本文档。
    """

    def __init__(self, chunk_size: int = 1000, overlap: int = 100) -> None:
        """
        初始化 SimpleSegmenter。

        参数:
            chunk_size: 每个文本片段的最大长度，默认为 1000。
            overlap: 相邻片段之间的重叠字符数，默认为 100。
        """
        # 校验并修正重叠大小，确保其小于 chunk_size
        if overlap >= chunk_size:
            overlap = max(0, chunk_size - 1)

        self.chunk_size: int = chunk_size
        self.overlap: int = overlap

    def parse(self, text: str, metadata: dict[str, Any]) -> list[Segment]:
        """
        将输入文本分割成一系列结构化的 Segment。

        参数:
            text: 待分段的原始文本。
            metadata: 与该文本关联的元数据字典。

        返回:
            一个由 Segment 对象组成的列表。
        """
        if not text.strip():
            return []

        # 使用基类提供的通用方法对文本进行分块
        chunks: list[str] = self.chunk_text(text, self.chunk_size, self.overlap)
        total_chunks: int = len(chunks)

        segments: list[Segment] = []
        for idx, chunk in enumerate(chunks):
            # 为每个文本块创建独立的元数据副本，并添加分段信息
            meta: dict[str, Any] = metadata.copy()
            meta["chunk_index"] = str(idx)
            meta["section_part"] = f"{idx + 1}/{total_chunks}"

            segment = Segment(text=chunk, metadata=meta)
            segments.append(segment)

        return segments
