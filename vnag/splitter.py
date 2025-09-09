from __future__ import annotations

from abc import ABC, abstractmethod
from typing import NamedTuple


class DocumentChunk(NamedTuple):
    """统一的文档分块结构"""
    text: str
    metadata: dict[str, str]


class BaseSplitter(ABC):
    """文本分割器抽象基类（只负责切分，不负责读取）"""

    @abstractmethod
    def split_text(self, text: str, metadata: dict[str, str]) -> list[DocumentChunk]:
        """对传入文本进行分块，返回 DocumentChunk 列表"""
        pass

    def pack_paragraphs(self, paragraphs: list[str], chunk_size: int) -> list[str]:
        """
        基于自然段（以空行为界）进行装箱聚合，输出不超过 chunk_size 的片段序列

        规则与行为：
        - 段间使用一个空行拼接，因此在聚合长度计算中需要额外 +2 的补偿
        - 若追加当前段后超过上限，则先 flush 现有缓冲为一个片段，再处理当前段
        - 对于单个段自身长度超过上限的情况，退化为定长切片（不重叠，不跨段）
        - 维持输入顺序，不做重叠
        """
        chunks: list[str] = []
        buffer: list[str] = []
        buffer_length: int = 0

        for p in paragraphs:
            # 段间空行补偿
            if buffer:
                separator_length: int = 2
            else:
                separator_length = 0

            p_len: int = len(p) + separator_length

            if buffer_length + p_len <= chunk_size:
                if buffer:
                    buffer.append("")
                buffer.append(p)
                buffer_length += p_len
                continue

            # flush 当前缓冲
            if buffer:
                assembled: str = "\n\n".join(buffer).strip()
                if assembled:
                    chunks.append(assembled)
                buffer = []
                buffer_length = 0

            # 单个段落本身超限：定长切片
            if len(p) > chunk_size:
                chunks.extend(self.split_by_length(p, chunk_size))
            else:
                buffer.append(p)
                buffer_length = len(p)

        # flush 剩余缓冲
        if buffer:
            assembled = "\n\n".join(buffer).strip() # 拼接缓冲
            if assembled:
                chunks.append(assembled)

        return chunks

    def pack_lines(self, lines: list[str], chunk_size: int) -> list[str]:
        """
        按“行”为最小单位进行装箱聚合，超过 chunk_size 时 flush 当前缓冲

        说明：
        - 行内保持原样，行间拼接使用一个换行符，因此聚合长度计算中需要额外+1
        - 不做重叠，维持原始顺序
        """
        chunks: list[str] = []
        buffer: list[str] = []
        buffer_length: int = 0

        for line in lines:
            # 行间换行补偿
            if buffer:
                newline_length = 1
            else:
                newline_length = 0

            added_length = len(line) + newline_length

            # 如果缓冲长度加上当前行长度小于等于chunk_size，则将当前行加入缓冲
            if buffer_length + added_length <= chunk_size:
                if buffer:
                    buffer.append("\n")
                buffer.append(line)
                buffer_length += added_length

            # 如果缓冲长度加上当前行长度大于chunk_size，则将缓冲中的内容加入chunks，并清空缓冲
            else:
                if buffer:
                    chunks.append("".join(buffer).strip())
                buffer = [line]
                buffer_length = len(line)

        if buffer:
            chunks.append("".join(buffer).strip())

        return chunks

    def split_by_length(self, text: str, chunk_size: int, overlap: int = 0) -> list[str]:
        """
        将长文本按固定大小切片（支持重叠），返回非空片段列表

        参数：
        - chunk_size：每片最大长度
        - overlap：相邻片段重叠字符数（默认 0，不重叠）

        说明：
        - 片段内容保持原文，仅用于判空时strip
        - 丢弃全空白片段
        - 步长 stride = max(1, chunk_size - overlap)
        """
        if chunk_size <= 0:
            return []

        # 计算步长
        stride: int = max(1, chunk_size - max(0, overlap))
        slices: list[str] = []
        n: int = len(text)

        # 按步长切分
        for i in range(0, n, stride):
            piece_raw: str = text[i : i + chunk_size]
            if piece_raw.strip():
                slices.append(piece_raw)

        return slices
