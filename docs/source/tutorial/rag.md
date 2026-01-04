# 教程：实现一个最小可用的 RAG

本教程演示如何用 VNAG 组件快速搭建一个“可检索、可问答”的最小 RAG 流程。

## 目标

- 把本地文档切分为 `Segment`
- 写入向量库（Chroma 或 Qdrant）
- 用自然语言问题做检索，拿到最相关片段

## 1. 准备依赖

如果使用 ChromaDB：

```bash
pip install chromadb
```

如果使用本地嵌入模型：

```bash
pip install sentence-transformers
```

## 2. 索引文档

```python
from pathlib import Path

from vnag.embedders.sentence_embedder import SentenceEmbedder
from vnag.segmenters.markdown_segmenter import MarkdownSegmenter
from vnag.vectors.chromadb_vector import ChromaVector


def main() -> None:
    # 1) 初始化组件
    segmenter = MarkdownSegmenter(chunk_size=2000)
    embedder = SentenceEmbedder("BAAI/bge-large-zh-v1.5")
    vector = ChromaVector(name="demo", embedder=embedder)

    # 2) 读取并切分文档（metadata 必须至少包含 source）
    doc_path = Path("README.md").resolve()
    text = doc_path.read_text(encoding="utf-8")
    segments = segmenter.parse(text, metadata={"source": str(doc_path)})

    # 3) 写入向量库
    vector.add_segments(segments)
    print(f"已索引片段数: {vector.count}")


if __name__ == "__main__":
    main()
```

## 3. 检索

```python
from vnag.embedders.sentence_embedder import SentenceEmbedder
from vnag.vectors.chromadb_vector import ChromaVector


def main() -> None:
    embedder = SentenceEmbedder("BAAI/bge-large-zh-v1.5")
    vector = ChromaVector(name="demo", embedder=embedder)

    results = vector.retrieve(query_text="VNAG 的核心特点是什么？", k=3)
    for i, seg in enumerate(results, start=1):
        print(f"[{i}] distance={seg.score:.4f} source={seg.metadata.get('source')}")
        print(seg.text[:200])
        print()


if __name__ == "__main__":
    main()
```

## 4. 组合为“可回答”的 RAG（提示词拼接）

最简单的做法是把检索到的片段拼成上下文，然后交给大模型网关生成答案。可以参考示例脚本 `examples/rag/run_ctp_rag.py` 的实现思路。


