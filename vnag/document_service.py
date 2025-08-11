from pathlib import Path
from typing import NamedTuple

import pypdf
from docx.api import Document as DocxDocument

from .utility import load_json


class DocumentChunk(NamedTuple):
    """文档分块"""
    text: str
    metadata: dict[str, str]


class DocumentService:
    """文档处理服务"""

    def __init__(self) -> None:
        """构造函数"""
        # 直接从配置文件读取设置
        settings = load_json("gateway_setting.json")
        self.chunk_size: int = settings.get("document.chunk_size", 1000)
        self.chunk_overlap: int = settings.get("document.chunk_overlap", 200)
        # 支持多格式（用户文件上传需要）
        self.supported_formats: list[str] = [".md", ".txt", ".pdf", ".docx"]

    def process_file(self, file_path: str) -> list[DocumentChunk]:
        """处理单个文件"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = path.suffix.lower()
        if extension not in self.supported_formats:
            raise ValueError(f"Unsupported format: {extension}")


        # 读取文本内容
        if extension in ['.md', '.txt']:
            text = self._read_text_file(path)
        elif extension == '.pdf':
            text = self._read_pdf_file(path)
        elif extension == '.docx':
            text = self._read_docx_file(path)
        else:
            raise ValueError(f"Unsupported extension: {extension}")

        # 创建文档分块
        return self._create_chunks(text, {
            'source': str(file_path),
            'filename': path.name,
            'file_type': extension
        })

    def _read_text_file(self, path: Path) -> str:
        """读取文本文件"""
        return path.read_text(encoding='utf-8')

    def _read_pdf_file(self, path: Path) -> str:
        """读取PDF文件"""
        text = ""

        with open(path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"

        return text

    def _read_docx_file(self, path: Path) -> str:
        """读取DOCX文件"""
        doc = DocxDocument(path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])

    def _create_chunks(
        self,
        text: str,
        metadata: dict[str, str]
    ) -> list[DocumentChunk]:
        """创建文档分块"""
        chunks: list[DocumentChunk] = []

        # 简单的字符分块算法
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size

            # 如果不是最后一块，尝试在句号处分割
            if end < text_length:
                # 寻找最近的句号
                period_pos = text.rfind('.', start, end)
                if period_pos > start:
                    end = period_pos + 1

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = str(len(chunks))

                chunks.append(DocumentChunk(
                    text=chunk_text,
                    metadata=chunk_metadata
                ))

            # 考虑重叠
            start = end - self.chunk_overlap if end < text_length else end

        return chunks
