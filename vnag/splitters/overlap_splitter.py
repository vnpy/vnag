from vnag.splitter import BaseSplitter, DocumentChunk


class OverlapSplitter(BaseSplitter):
    """普通的定长重叠分块器（按字符计）

    说明：
    - 仅负责将纯文本按固定长度切分，支持重叠
    - 不做标题或语义识别，简单可预期
    - 生成 chunk_index 元数据，便于后续检索
    """

    def __init__(self, chunk_size: int = 3000, overlap: int = 200) -> None:
        """构造函数"""
        if overlap >= chunk_size:
            overlap = max(0, chunk_size - 1)

        self.chunk_size: int = chunk_size
        self.overlap: int = overlap

    def split_text(self, text: str, metadata: dict[str, str]) -> list[DocumentChunk]:
        """对传入文本进行结构化分块"""
        chunks: list[DocumentChunk] = self._create_chunks_overlap(text, metadata)
        return chunks

    def _create_chunks_overlap(self, text: str, metadata: dict[str, str]) -> list[DocumentChunk]:
        """定长切片 + 重叠步进

        规则：
        - 步长 stride = chunk_size - overlap
        - 片段取 text[start : start + chunk_size] 并 strip
        - 过滤空白片段
        - 写入元数据：chunk_index、section_title=overlap、section_order=0、section_part=j/total
        """
        if not text:
            return []

        pieces: list[str] = self.split_by_length(text, self.chunk_size, self.overlap)

        total: int = len(pieces)
        out: list[DocumentChunk] = []
        for idx, piece in enumerate(pieces):
            meta: dict[str, str] = metadata.copy()
            meta["chunk_index"] = str(idx)
            meta["section_title"] = "overlap"
            meta["section_order"] = str(idx)
            meta["section_part"] = f"{idx + 1}/{total}"
            out.append(DocumentChunk(text=piece, metadata=meta))

        return out
