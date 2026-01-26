from pathlib import Path

from vnag.embedders.sentence_embedder import SentenceEmbedder
from vnag.object import Segment
from vnag.segmenters.markdown_segmenter import MarkdownSegmenter
from vnag.vectors.chromadb_vector import ChromaVector


def main() -> None:
    """ChromaDB 向量库完整示例：添加文档 + 相似性检索"""
    # ========== 第一部分：添加文档到向量库 ==========
    print("=" * 50)
    print("第一步：将 Markdown 文件切分后写入 ChromaDB 向量库")
    print("=" * 50)

    # 读取文件内容
    filename: str = "veighna_station.md"
    base_dir: Path = Path(__file__).resolve().parent.parent
    filepath: Path = (base_dir / "rag/knowledge" / filename).resolve()
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

    # 创建向量库（使用 BGE 本地模型，name="bge"）
    embedder: SentenceEmbedder = SentenceEmbedder("BAAI/bge-large-zh-v1.5")
    vector: ChromaVector = ChromaVector(name="bge", embedder=embedder)

    # 如需使用 DashScope API，替换为（注意修改 name）：
    # from vnag.embedders.dashscope_embedder import DashscopeEmbedder
    # embedder = DashscopeEmbedder(api_key="your_api_key", model_name="text-embedding-v3")
    # vector = ChromaVector(name="dashscope", embedder=embedder)

    # 如需使用 OpenRouter API，替换为（注意修改 name）：
    # from vnag.embedders.openai_embedder import OpenaiEmbedder
    # embedder = OpenaiEmbedder(
    #     base_url="https://openrouter.ai/api/v1",
    #     api_key="your_api_key",
    #     model_name="qwen/qwen3-embedding-8b"
    # )
    # vector = ChromaVector(name="openai", embedder=embedder)

    # 写入向量库
    vector.add_segments(segments)
    print(f"写入完成，向量库中共有 {vector.count} 个块")

    # ========== 第二部分：执行相似性检索 ==========
    print()
    print("=" * 50)
    print("第二步：执行向量检索")
    print("=" * 50)

    # 执行查询
    query: str = "如何实现 VeighNa Station 登录"
    print(f"查询内容: {query}")
    print()

    results: list[Segment] = vector.retrieve(query_text=query, k=5)
    for i, segment in enumerate(results, 1):
        print("-" * 40)
        print(f"结果 {i}:")
        print(f"  相关性得分（距离）: {segment.score:.4f}")
        print(f"  metadata 元数据: {segment.metadata}")
        print(f"  文本内容: {segment.text[:200]}...")


if __name__ == "__main__":
    main()
