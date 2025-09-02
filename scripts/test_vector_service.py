"""VectorService 简单功能测试。

条件：
- 使用假的 embedding 与 collection，避免下载与持久化副作用。
- 仅测试最小功能路径：添加后检索。

期望：
- 检索结果数量与添加一致；字段完整。
"""

from typing import Any, cast
from vnag.vector_service import VectorService
from vnag.document_service import DocumentChunk


class _FakeNdArray:
    def __init__(self, data: list[list[float]]) -> None:
        self._data = data

    def tolist(self) -> list[list[float]]:
        return self._data


class _FakeEmbedding:
    def encode(
        self,
        texts: list[str],
        show_progress_bar: bool = False,  # noqa: FBT001
    ) -> _FakeNdArray:
        data = []
        for _ in texts:
            data.append([0.0, 0.0, 0.0])
        return _FakeNdArray(data)


class _FakeCollection:
    def __init__(self) -> None:
        self._docs: list[str] = []
        self._metas: list[dict[str, Any]] = []
        self._ids: list[str] = []

    # Chroma-like API
    def add(
        self,
        embeddings: list[list[float]] | None = None,
        documents: list[str] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        if documents:
            self._docs.extend(documents)
        if metadatas:
            self._metas.extend(metadatas)
        if ids:
            self._ids.extend(ids)

    def count(self) -> int:
        return len(self._docs)

    def query(
        self,
        query_embeddings: list[list[float]] | list[float],
        n_results: int,
    ) -> dict:
        n = min(n_results, len(self._docs))
        return {
            "documents": [self._docs[:n]],
            "metadatas": [self._metas[:n]],
            "distances": [[0.0 for _ in range(n)]],
        }


class _VectorServiceNoInit(VectorService):
    def __init__(self) -> None:
        # 提供假依赖，跳过重型初始化
        self.embedding_model = cast(Any, _FakeEmbedding())
        # client/collection 仅用于测试桩，不参与类型校验
        self.client = cast(Any, None)
        self.collection = cast(Any, _FakeCollection())


def test_add_and_search_simple() -> None:
    """给定两段文本，添加后检索应返回两条且字段完整。"""
    vs = _VectorServiceNoInit()
    chunks = []
    chunks.append(
        DocumentChunk(
            text="para1",
            metadata={"filename": "f1.md", "chunk_index": "0"},
        )
    )
    chunks.append(
        DocumentChunk(
            text="para2",
            metadata={"filename": "f1.md", "chunk_index": "1"},
        )
    )
    vs.add_documents(chunks)
    out = vs.similarity_search("q", k=5)
    assert len(out) == 2  # 返回两条
    assert {
        "text",
        "metadata",
        "distance",
    } <= set(out[0].keys())  # 字段完整


def test_similarity_search_empty() -> None:
    """空库时相似度检索应返回空列表。"""
    vs = _VectorServiceNoInit()
    out = vs.similarity_search("hello", k=3)
    assert out == []


def test_get_document_count() -> None:
    """计数：空库为 0，添加两条后为 2。"""
    vs = _VectorServiceNoInit()
    assert vs.get_document_count() == 0

    chunks = []
    chunks.append(DocumentChunk(
        text="p1",
        metadata={"filename": "f.md", "chunk_index": "0"},
    ))
    chunks.append(DocumentChunk(
        text="p2",
        metadata={"filename": "f.md", "chunk_index": "1"}
    ))
    vs.add_documents(chunks)
    assert vs.get_document_count() == 2
