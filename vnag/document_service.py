from pathlib import Path
from typing import NamedTuple

import pypdf


class DocumentChunk(NamedTuple):
    """文档分块"""
    text: str
    metadata: dict[str, str]


class DocumentService:
    """文档处理服务"""

    def __init__(self) -> None:
        """构造函数"""
        # 分块参数先写死（MVP）：后续计划改为基于token的max_chunk_tokens/overlap_tokens，并回收至配置
        self.chunk_size: int = 1000
        self.chunk_overlap: int = 200
        # 支持多格式（用户文件上传需要）
        self.supported_formats: list[str] = [".md", ".txt", ".pdf"]

    def process_file(self, file_path: str) -> list[DocumentChunk]:
        """处理单个文件"""
        path: Path = Path(file_path)

        extension = path.suffix.lower()
        if extension not in self.supported_formats:
            raise ValueError(f"不支持的类型：{extension}")

        # 读取文本内容
        if extension in ['.md', '.txt']:
            text: str = self._read_text_file(path)
        else:
            text = self._read_pdf_file(path)

        # 创建文档分块
        chunks: list = self._create_chunks(text, {
            'source': str(file_path),
            'filename': path.name,
            'file_type': extension
        })
        return chunks

    def _read_text_file(self, path: Path) -> str:
        """读取文本文件"""
        text: str = path.read_text(encoding='utf-8')
        return text

    def _read_pdf_file(self, path: Path) -> str:
        """读取PDF文件"""
        text: str = ""

        with open(path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"

        return text

    def _create_chunks(
        self,
        text: str,
        metadata: dict[str, str]
    ) -> list[DocumentChunk]:
        """创建文档分块"""
        chunks: list[DocumentChunk] = []

        # 简单的字符分块算法
        start: int = 0
        text_length: int = len(text)

        while start < text_length:
            end: int = start + self.chunk_size

            # 如果不是最后一块，尝试在句号处分割
            if end < text_length:
                # 寻找最近的句号
                period_pos: int = text.rfind('.', start, end)
                if period_pos > start:
                    end = period_pos + 1

            chunk_text: str = text[start:end].strip()

            if chunk_text:
                chunk_metadata: dict = metadata.copy()
                chunk_metadata['chunk_index'] = str(len(chunks))

                chunks.append(DocumentChunk(
                    text=chunk_text,
                    metadata=chunk_metadata
                ))

            # 考虑重叠
            if end < text_length:
                start = end - self.chunk_overlap
            else:
                start = end

        return chunks
