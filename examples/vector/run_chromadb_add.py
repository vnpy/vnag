from pathlib import Path

from vnag.embedders.sentence_embedder import SentenceEmbedder
from vnag.object import Segment
from vnag.segmenters.markdown_segmenter import MarkdownSegmenter
from vnag.vectors.chromadb_vector import ChromaVector


def main() -> None:
    """将指定 Markdown 文件切分后写入本地 Chroma 向量库"""
    # 读取文件内容
    filename: str = "veighna_station.md"
    filepath: Path = Path(f"../rag/knowledge/{filename}").resolve()
    with open(filepath, encoding="utf-8") as f:
        text: str = f.read()

    # 拆分文本为块
    segmenter: MarkdownSegmenter = MarkdownSegmenter(chunk_size=2000)
    file_type: str = filepath.suffix.lower().lstrip(".")
    metadata: dict[str, str] = {
        "filename": filename,
        "source": str(filepath),
        "file_type": file_type
    }
    segments: list[Segment] = segmenter.parse(text, metadata=metadata)
    print(f"总块数: {len(segments)}")

    # 写入向量库（使用 BGE 本地模型，name="bge"）
    embedder: SentenceEmbedder = SentenceEmbedder("BAAI/bge-large-zh-v1.5")
    vector: ChromaVector = ChromaVector(name="bge", embedder=embedder)

    # 如需使用 DashScope API，替换为（注意修改 name）：
    # from vnag.embedders.dashscope_embedder import DashscopeEmbedder
    # embedder = DashscopeEmbedder(api_key="your_api_key", model_name="text-embedder-v3")
    # vector = ChromaVector(name="dashscope", embedder=embedder)
   
    vector.add_segments(segments)

    print(f"写入完成，向量库中共有 {vector.count} 个块")


if __name__ == "__main__":
    main()
