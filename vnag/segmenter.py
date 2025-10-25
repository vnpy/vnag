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
            chunk: str = text[i:i + chunk_size]
            if chunk.strip():  # 仅当片段包含非空白内容时才添加
                chunks.append(chunk)

        return chunks


def pack_lines(lines: list[str], chunk_size: int) -> list[str]:
    """
    将代码行列表打包成不超过指定大小的文本块。

    该函数模拟将代码行一个个放入箱子（文本块）的过程，以尽可能填满每个箱子。

    参数:
        lines: 待打包的字符串代码行列表。
        chunk_size: 每个文本块的最大长度。

    返回:
        一个由打包好的文本块字符串组成的列表。

    注意:
        - 代码行之间使用 `\n` 连接，拼接长度会计入总长度。
        - 该函数不处理单行超长的情况，单个超长行会自成一个块。
    """
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_len: int = 0

    for line in lines:
        separator_len: int = 1 if buffer else 0
        line_len: int = len(line)

        # 检查将当前行加入缓冲区后是否会超长
        if buffer_len + line_len + separator_len <= chunk_size:
            # 未超长：加入缓冲区
            buffer.append(line)
            buffer_len += line_len + separator_len
            continue

        # 已超长：先将当前缓冲区打包成块
        if buffer:
            assembled_chunk: str = "\n".join(buffer).strip()
            if assembled_chunk:
                chunks.append(assembled_chunk)

        # 然后将当前行作为新缓冲区的开始
        buffer = [line]
        buffer_len = line_len

    # 清空最后一个缓冲区中剩余的内容
    if buffer:
        assembled_chunk = "\n".join(buffer).strip()
        if assembled_chunk:
            chunks.append(assembled_chunk)

    return chunks


def pack_section(section_content: str, chunk_size: int) -> list[str]:
    """
    将一个大的代码章节（如整个函数或类）分割成多个大小合适的块。

    这是一个三层降级式的分块策略，以确保在任何情况下都能生成大小合规的块：
    1. 首先，尝试按“段落”（由空行分隔的代码块）进行聚合。这有助于保持代码的逻辑内聚性。
    2. 如果按段落聚合后仍有超长的块，则对这些块退而求其次，按“行”进行聚合。
    3. 如果单行本身就超长（极端情况），则强制按固定长度进行切分，作为最终的兜底保障。

    参数:
        section_content: 待分割的完整代码章节字符串。
        chunk_size: 每个块的最大长度限制。

    返回:
        一个由分割好的文本块字符串组成的列表。
    """
    # 如果章节本身没有超长，直接返回，无需分割。
    if len(section_content) <= chunk_size:
        return [section_content]

    # --- 第一层：按“段落”（空行）进行智能聚合 ---
    paragraphs: list[str] = [p.strip() for p in section_content.split("\n\n") if p.strip()]

    # 使用一个辅助函数来“装箱”，将多个小段落合并成一个不超长的块。
    paragraph_chunks: list[str] = []
    buffer: list[str] = []
    buffer_len: int = 0
    for para in paragraphs:
        para_len: int = len(para)
        separator_len: int = 2 if buffer else 0  # 段落间用 "\n\n" 分隔

        # 如果将当前段落加入缓冲区会超长
        if buffer_len + para_len + separator_len > chunk_size:
            # 先将当前缓冲区的内容打包成一个块
            if buffer:
                paragraph_chunks.append("\n\n".join(buffer))
            # 然后将当前段落作为新缓冲区的开始
            buffer = [para]
            buffer_len = para_len
        else:
            # 未超长，则加入缓冲区
            buffer.append(para)
            buffer_len += para_len + separator_len

    # 清空最后一个缓冲区
    if buffer:
        paragraph_chunks.append("\n\n".join(buffer))

    # --- 第二层：对仍然超长的块，按“行”进行聚合 ---
    line_chunks: list[str] = []
    for chunk in paragraph_chunks:
        # 如果这个基于段落的块没有超长，则直接采纳
        if len(chunk) <= chunk_size:
            line_chunks.append(chunk)
            continue

        # 如果超长了，就对它进行更细粒度的、按行的切分
        line_chunks.extend(pack_lines(chunk.splitlines(), chunk_size))

    # --- 第三层：对极端超长的单行，进行强制定长切分（兜底） ---
    final_chunks: list[str] = []
    for chunk in line_chunks:
        # 如果这个基于行的块没有超长，则直接采纳
        if len(chunk) <= chunk_size:
            final_chunks.append(chunk)
        else:
            # 如果单行本身就超长，执行强制切分
            final_chunks.extend(
                [chunk[i:i + chunk_size] for i in range(0, len(chunk), chunk_size)]
            )

    return final_chunks
