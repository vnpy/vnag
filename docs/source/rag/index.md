# RAG 模块

RAG（Retrieval-Augmented Generation，检索增强生成）是一种让 AI 能够基于自定义知识库回答问题的技术。

## 本章内容

```{toctree}
:maxdepth: 2

segmenter
embedder
vector
```

## RAG 概述

RAG 系统通常包含以下步骤：

- **索引阶段**：文档 → 分段（Segmenter）→ 片段（Segment）→ 向量化（Embedder）→ 写入向量库（Vector）
- **检索阶段**：问题 → 向量化 → 相似检索 → 拼接上下文 → 交给大模型生成答案

## 快速示例（可运行）

下面示例演示：读取一个 Markdown 文档，切分后写入 ChromaDB，然后用自然语言问题做检索。

```python
from pathlib import Path

from vnag.embedders.sentence_embedder import SentenceEmbedder
from vnag.segmenters.markdown_segmenter import MarkdownSegmenter
from vnag.vectors.chromadb_vector import ChromaVector


def main() -> None:
    # 1) 初始化分段器/嵌入器/向量库
    segmenter = MarkdownSegmenter(chunk_size=2000)
    embedder = SentenceEmbedder("BAAI/bge-large-zh-v1.5")
    vector = ChromaVector(name="docs", embedder=embedder)

    # 2) 索引文档（注意：metadata 至少要包含 source，向量库会用它生成唯一ID）
    doc_path = Path("README.md").resolve()
    text = doc_path.read_text(encoding="utf-8")
    segments = segmenter.parse(text, metadata={"source": str(doc_path)})
    vector.add_segments(segments)

    # 3) 检索
    results = vector.retrieve(query_text="VNAG 支持哪些核心能力？", k=3)
    for i, seg in enumerate(results, start=1):
        print(f"[{i}] score(distance)={seg.score:.4f} source={seg.metadata.get('source')}")
        print(seg.text[:200])
        print()


if __name__ == "__main__":
    main()
```

## 下一步

- [Segmenter 分段器](segmenter.md)
- [Embedder 嵌入器](embedder.md)
- [Vector 向量库](vector.md)
- [教程 - 实现 RAG](../tutorial/rag.md)


