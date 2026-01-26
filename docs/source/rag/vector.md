# Vector 向量库

向量库负责存储文本片段（Segment）的向量，并提供相似度检索能力。

## BaseVector 基类

VNAG 的向量库接口以 `Segment` 为中心：

```python
from vnag.object import Segment
from vnag.vector import BaseVector


class BaseVector:
    def add_segments(self, segments: list[Segment]) -> list[str]:
        """将文档块添加到向量存储中，返回存入的 ID 列表"""
        raise NotImplementedError

    def retrieve(self, query_text: str, k: int = 5) -> list[Segment]:
        """根据查询文本执行相似性检索"""
        raise NotImplementedError

    def delete_segments(self, segment_ids: list[str]) -> bool:
        """根据 ID 列表删除文档块"""
        raise NotImplementedError

    def get_segments(self, segment_ids: list[str]) -> list[Segment]:
        """根据 ID 列表获取文档块"""
        raise NotImplementedError

    @property
    def count(self) -> int:
        """获取向量存储中的文档总数"""
        raise NotImplementedError
```

检索返回的 `Segment.score` 为**距离（distance）**，数值越小表示越相似。

## ChromaVector

ChromaDB 是轻量级的本地向量库，适合开发与小规模知识库。

安装：

```bash
pip install chromadb
```

使用：

```python
from pathlib import Path

from vnag.embedders.sentence_embedder import SentenceEmbedder
from vnag.segmenters.simple_segmenter import SimpleSegmenter
from vnag.vectors.chromadb_vector import ChromaVector

segmenter = SimpleSegmenter(chunk_size=800, overlap=100)
embedder = SentenceEmbedder("BAAI/bge-large-zh-v1.5")
vector = ChromaVector(name="my_knowledge", embedder=embedder)

doc_path = Path("README.md").resolve()
text = doc_path.read_text(encoding="utf-8")
segments = segmenter.parse(text, metadata={"source": str(doc_path)})
vector.add_segments(segments)

results = vector.retrieve(query_text="VNAG 是什么？", k=3)
for seg in results:
    print(seg.score, seg.metadata.get("source"))
```

持久化目录：

- 默认保存在运行目录的 `.vnag/chroma_db/{name}/` 下。

## QdrantVector

Qdrant 是高性能向量引擎；本项目使用 `qdrant-client` 的本地持久化模式（path）。

安装：

```bash
pip install qdrant-client
```

使用：

```python
from pathlib import Path

from vnag.embedders.sentence_embedder import SentenceEmbedder
from vnag.segmenters.simple_segmenter import SimpleSegmenter
from vnag.vectors.qdrant_vector import QdrantVector

segmenter = SimpleSegmenter(chunk_size=800, overlap=100)
embedder = SentenceEmbedder("BAAI/bge-large-zh-v1.5")
vector = QdrantVector(name="my_knowledge", embedder=embedder)

doc_path = Path("README.md").resolve()
text = doc_path.read_text(encoding="utf-8")
segments = segmenter.parse(text, metadata={"source": str(doc_path)})
vector.add_segments(segments)

results = vector.retrieve(query_text="如何配置 VNAG？", k=3)
for seg in results:
    print(seg.score, seg.metadata.get("source"))
```

持久化目录：

- 默认保存在运行目录的 `.vnag/qdrant_db/` 下（集合名为 `name`）。


