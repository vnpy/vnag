from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token

from vnag.object import Segment
from vnag.segmenter import BaseSegmenter


class MarkdownSegmenter(BaseSegmenter):
    """
    Markdown 文本分段器，它利用标题（Headings）来创建结构化的文本段。
    """

    def __init__(self, chunk_size: int = 2000) -> None:
        """
        初始化 MarkdownSegmenter。

        参数:
            chunk_size: 每个文本块的最大长度，默认为 2000。
        """
        self.chunk_size: int = chunk_size
        self.md_parser: MarkdownIt = MarkdownIt()

    def parse(self, text: str, metadata: dict[str, Any]) -> list[Segment]:
        """
        将输入的 Markdown 文本分割成一系列结构化的 Segment。

        处理流程:
        1. 使用 markdown-it-py 解析文本，获取 Tokens。
        2. 调用 `group_by_headings` 方法，按标题将 Tokens 分割成逻辑章节。
        3. 对于过长的章节，调用 `pack_paragraphs` 按段落进行打包，确保每个块不超过 `chunk_size`。
        4. 为每个最终的文本块创建 `Segment` 对象，并附加元数据。
        """
        tokens: list[Token] = self.md_parser.parse(text)
        sections: list[tuple[str, str]] = group_by_headings(text, tokens)

        segments: list[Segment] = []
        segment_index: int = 0
        section_order: int = 0

        for title, content in sections:
            chunks: list[str]
            # 如果一个章节内容过长，则调用段落打包函数进一步切分
            if len(content) > self.chunk_size:
                chunks = pack_paragraphs(content.split("\n\n"), self.chunk_size)
            else:
                chunks = [content]

            total_chunks: int = len(chunks)
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue

                # 为每个文本块创建独立的元数据副本，并添加分段信息
                chunk_meta: dict[str, Any] = metadata.copy()
                chunk_meta["chunk_index"] = str(segment_index)
                chunk_meta["section_order"] = str(section_order)
                chunk_meta["section_part"] = f"{i + 1}/{total_chunks}"

                if title:
                    chunk_meta["section_title"] = title

                segments.append(Segment(text=chunk, metadata=chunk_meta))
                segment_index += 1

            section_order += 1

        return segments


def group_by_headings(text: str, tokens: list[Token]) -> list[tuple[str, str]]:
    """
    根据标题 Token 将 Markdown 文本分割成章节。

    参数:
        text: 原始 Markdown 文本。
        tokens: 由 markdown-it-py 解析生成的 Token 列表。

    返回:
        一个元组列表，每个元组包含 (章节标题, 章节内容)。
    """
    sections: list[tuple[str, str]] = []
    current_section_lines: list[str] = []
    current_title: str = "默认章节"  # 为文档开始处、第一个标题前的内容设置默认标题

    lines: list[str] = text.splitlines()

    # 找到所有标题 Token 及其所在的行号
    heading_indices: dict[int, str] = {
        token.map[0]: token.content
        for token in tokens
        if token.type == "heading_open"
    }

    # 如果没有找到任何标题，则将整个文档作为一个章节处理
    if not heading_indices:
        return [(current_title, text)]

    # 逐行遍历，根据标题行进行内容分组
    for i, line in enumerate(lines):
        if i in heading_indices:
            # 当遇到一个新的标题时，保存前一个已收集的章节内容
            if current_section_lines:
                sections.append(
                    (current_title, "\n".join(current_section_lines).strip())
                )

            # 开始一个新的章节
            current_title = heading_indices[i]
            current_section_lines = [line]
        else:
            # 将当前行内容追加到当前章节
            current_section_lines.append(line)

    # 在遍历结束后，保存最后一个章节的内容
    if current_section_lines:
        sections.append((current_title, "\n".join(current_section_lines).strip()))

    return sections


def pack_paragraphs(paragraphs: list[str], chunk_size: int) -> list[str]:
    """
    将段落列表打包成不超过指定大小的文本块。

    该函数模拟将段落一个个放入箱子（文本块）的过程，以尽可能填满每个箱子，
    同时确保单个段落不会被分割（除非该段落本身就超过了最大长度）。

    参数:
        paragraphs: 待打包的字符串段落列表。
        chunk_size: 每个文本块的最大长度。

    返回:
        一个由打包好的文本块字符串组成的列表。

    注意:
        - 段落之间使用 `\n\n` 连接，拼接长度会计入总长度。
        - 如果单个段落的长度超过 `chunk_size`，它将被强制切分为更小的块。
    """
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_len: int = 0

    for paragraph in paragraphs:
        # 计算段落间分隔符的长度
        separator_len: int = 2 if buffer else 0
        paragraph_len: int = len(paragraph)

        # 检查将当前段落加入缓冲区后是否会超长
        if buffer_len + paragraph_len + separator_len <= chunk_size:
            # 未超长：加入缓冲区
            buffer.append(paragraph)
            buffer_len += paragraph_len + separator_len
            continue

        # 已超长：需要先处理（清空）缓冲区
        if buffer:
            assembled_chunk: str = "\n\n".join(buffer).strip()
            if assembled_chunk:
                chunks.append(assembled_chunk)
            buffer = []
            buffer_len = 0

        # 处理当前段落
        if paragraph_len > chunk_size:
            # 如果段落本身就超长，直接进行定长切分
            chunks.extend(BaseSegmenter.chunk_text(paragraph, chunk_size))
        else:
            # 否则，将该段落作为新缓冲区的第一个元素
            buffer.append(paragraph)
            buffer_len = paragraph_len

    # 清空最后一个缓冲区中剩余的内容
    if buffer:
        assembled_chunk: str = "\n\n".join(buffer).strip()
        if assembled_chunk:
            chunks.append(assembled_chunk)

    return chunks
