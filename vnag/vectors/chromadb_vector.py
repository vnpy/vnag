from pathlib import Path
from typing import Any
from collections.abc import Mapping

import numpy as np
from numpy.typing import NDArray
import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.api.types import GetResult, QueryResult
from chromadb.config import Settings as ChromaSettings

from vnag.object import Segment
from vnag.utility import get_folder_path
from vnag.vector import BaseVector
from vnag.embedding import BaseEmbedding


class ChromaVector(BaseVector):
    """基于 ChromaDB 实现的向量存储。"""

    def __init__(
        self,
        name: str,
        embedding_model: BaseEmbedding
    ) -> None:
        """初始化 ChromaDB 向量存储。"""
        self.persist_dir: Path = get_folder_path("chroma_db").joinpath(name)
        self.embedding_model: BaseEmbedding = embedding_model

        self.client: ClientAPI = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self.collection: Collection = self.client.get_or_create_collection(
            name="segments", metadata={"hnsw:space": "cosine"}
        )

    def add_segments(self, segments: list[Segment]) -> list[str]:
        """将一批文档块添加到 ChromaDB 中。"""
        if not segments:
            return []

        texts: list[str] = [seg.text for seg in segments]
        metadatas: list[Mapping[str, Any]] = [seg.metadata for seg in segments]

        embeddings_np: NDArray[np.float32] = self.embedding_model.encode(
            texts
        )

        # 使用source（绝对路径）和chunk_index组合生成唯一ID
        ids: list[str] = [
            f"{seg.metadata['source']}_{seg.metadata['chunk_index']}"
            for seg in segments
        ]

        # 分批写入，避免触发 Chroma 单批上限（约 5461）
        db_batch_size: int = 3000
        for i in range(0, len(ids), db_batch_size):
            j = i + db_batch_size
            self.collection.upsert(
                embeddings=embeddings_np[i:j],
                documents=texts[i:j],
                metadatas=metadatas[i:j],
                ids=ids[i:j],
            )

        return ids

    def retrieve(self, query_text: str, k: int = 5) -> list[Segment]:
        """根据查询文本，从 ChromaDB 中检索相似的文档块。"""
        if self.count == 0:
            return []

        query_embedding_np: NDArray[np.float32] = self.embedding_model.encode(
            [query_text]
        )

        results: QueryResult = self.collection.query(
            query_embeddings=query_embedding_np, n_results=k
        )

        documents: list[list[str]] | None = results.get("documents")
        metadatas: list[list[Mapping[str, Any]]] | None = results.get("metadatas")
        distances: list[list[float]] | None = results.get("distances")

        if not (documents and metadatas and distances and documents[0]):
            return []

        retrieved_results: list[Segment] = []
        for text, meta, dist in zip(
            documents[0], metadatas[0], distances[0], strict=True
        ):
            # ChromaDB 返回的 metadata 字典可能包含非字符串值，
            # 而 Segment 要求 dict[str, str]。这里进行转换以确保类型安全。
            safe_meta: dict[str, str] = {
                str(key): str(value) for key, value in meta.items()
            }

            segment: Segment = Segment(text=text, metadata=safe_meta, score=dist)
            retrieved_results.append(segment)

        return retrieved_results

    def delete_segments(self, segment_ids: list[str]) -> bool:
        """根据ID列表，从 ChromaDB 中删除一个或多个文档。"""
        if not segment_ids:
            return True
        try:
            self.collection.delete(ids=segment_ids)
            return True
        except Exception:
            # 考虑在这里添加日志记录
            return False

    def get_segments(self, segment_ids: list[str]) -> list[Segment]:
        """根据ID列表，从 ChromaDB 中直接获取原始的文档块。"""
        if not segment_ids:
            return []

        results: GetResult = self.collection.get(ids=segment_ids)

        documents: list[str] | None = results.get("documents")
        metadatas: list[Mapping[str, Any]] | None = results.get("metadatas")

        if not (documents and metadatas):
            return []

        return [
            Segment(
                text=text,
                metadata={str(key): str(value) for key, value in meta.items()},
            )
            for text, meta in zip(documents, metadatas, strict=True)
        ]

    @property
    def count(self) -> int:
        """获取向量存储中的文档总数。"""
        count: int = self.collection.count()
        return count
