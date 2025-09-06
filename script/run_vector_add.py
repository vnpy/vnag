from pathlib import Path

from vnag.splitters.markdown_splitter import MarkdownSplitter
from vnag.utility import read_text_file
from vnag.vector_service import VectorService


def add_md_file(vs: VectorService, file_path: str, chunk_size: int = 3000) -> int:
    """读取 Markdown 文件，切分并入库，返回入库分块数"""
    text: str = read_text_file(file_path)
    splitter = MarkdownSplitter(chunk_size=chunk_size)

    p = Path(file_path)
    base_meta: dict[str, str] = {
        "source": file_path,
        "filename": p.name,
        "file_type": "md",
    }

    chunks = splitter.split_text(text, base_meta)
    vs.add_documents(chunks)
    return len(chunks)


def main() -> None:
    """将指定 Markdown 文件切分后写入本地 Chroma 向量库"""
    FILE_PATH: str = r"D:\test\.vnag\docs\community\info\veighna_station.md"
    CHUNK_SIZE: int = 2000

    vs = VectorService()

    before = vs.get_document_count()
    n = add_md_file(vs, FILE_PATH, CHUNK_SIZE)
    after = vs.get_document_count()

    print(f"added_chunks={n}")
    print(f"collection_count_before={before}")
    print(f"collection_count_after={after}")


if __name__ == "__main__":
    main()
