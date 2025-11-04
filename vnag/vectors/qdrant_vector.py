from pathlib import Path
from typing import Any
from uuid import uuid5, NAMESPACE_DNS

import numpy as np
from numpy.typing import NDArray
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    CollectionDescription
)

from vnag.object import Segment
from vnag.utility import get_folder_path
from vnag.vector import BaseVector
from vnag.embedder import BaseEmbedder


class QdrantVector(BaseVector):
    """基于 Qdrant 实现的向量存储。"""

    def __init__(
        self,
        name: str,
        embedder: BaseEmbedder
    ) -> None:
        """初始化 Qdrant 向量存储。"""
        self.persist_dir: Path = get_folder_path("qdrant_db")
        self.embedder: BaseEmbedder = embedder
        self.collection_name: str = name

        # 通过编码样本获取实际维度
        self.dimension: int = embedder.encode(["qdrant"]).shape[1]

        self.client: QdrantClient = QdrantClient(
            path=str(self.persist_dir)
        )

        # 创建或获取集合
        self._init_collection()

    def _init_collection(self) -> None:
        """初始化或获取集合。"""
        collections: list[CollectionDescription] = self.client.get_collections().collections
        collection_names: list[str] = [col.name for col in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.dimension,
                    distance=Distance.COSINE
                )
            )

    def add_segments(self, segments: list[Segment]) -> list[str]:
        """将一批文档块添加到 Qdrant 中。"""
        if not segments:
            return []

        texts: list[str] = [seg.text for seg in segments]

        embeddings_np: NDArray[np.float32] = self.embedder.encode(texts)

        # 生成唯一ID（字符串形式，用于返回）
        string_ids: list[str] = [
            f"{seg.metadata['source']}_{seg.metadata['chunk_index']}"
            for seg in segments
        ]

        # 构建 Qdrant Points
        points: list[PointStruct] = []
        for string_id, segment, embedding in zip(
            string_ids,
            segments,
            embeddings_np,
            strict=True
        ):
            # 将字符串ID转为UUID（Qdrant要求）
            uuid_id: str = str(uuid5(NAMESPACE_DNS, string_id))

            # 构建 payload（包含文本、元数据和原始字符串ID）
            payload: dict[str, Any] = segment.metadata.copy()
            payload["text"] = segment.text
            payload["string_id"] = string_id

            point: PointStruct = PointStruct(
                id=uuid_id,
                vector=embedding.tolist(),
                payload=payload
            )
            points.append(point)

        # 分批插入，避免单批数据过大导致超时
        db_batch_size: int = 1000
        for i in range(0, len(points), db_batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                points=points[i:i + db_batch_size]
            )

        return string_ids

    def retrieve(self, query_text: str, k: int = 5) -> list[Segment]:
        """根据查询文本，从 Qdrant 中检索相似的文档块。"""
        if self.count == 0:
            return []

        query_embedding_np: NDArray[np.float32] = self.embedder.encode(
            [query_text]
        )

        # 执行搜索
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding_np[0].tolist(),
            limit=k
        )

        # 构建返回结果
        retrieved_results: list[Segment] = []
        for point in search_result:
            if point.payload:
                payload: dict[str, Any] = point.payload
            else:
                payload = {}
            text: str = payload.pop("text", "")

            # 转换 payload 为 metadata
            safe_meta: dict[str, str] = {
                str(key): str(value) for key, value in payload.items()
            }

            # Qdrant 返回 score（余弦相似度，越大越相似）
            # ChromaDB 返回 distance（余弦距离，越小越相似）
            # 为保持一致，将 Qdrant score 转为 distance
            distance: float = 1.0 - point.score
            segment: Segment = Segment(
                text=text,
                metadata=safe_meta,
                score=distance
            )
            retrieved_results.append(segment)

        return retrieved_results

    def delete_segments(self, segment_ids: list[str]) -> bool:
        """根据ID列表，从 Qdrant 中删除一个或多个文档。"""
        if not segment_ids:
            return True

        try:
            # 将字符串ID转为UUID
            uuid_ids: list[str] = [
                str(uuid5(NAMESPACE_DNS, sid)) for sid in segment_ids
            ]
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=uuid_ids
            )
            return True
        except Exception:
            return False

    def get_segments(self, segment_ids: list[str]) -> list[Segment]:
        """根据ID列表，从 Qdrant 中直接获取原始的文档块。"""
        if not segment_ids:
            return []

        # 将字符串ID转为UUID
        uuid_ids: list[str] = [
            str(uuid5(NAMESPACE_DNS, sid)) for sid in segment_ids
        ]

        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=uuid_ids
        )

        results: list[Segment] = []
        for point in points:
            if point.payload:
                payload: dict[str, Any] = point.payload
            else:
                payload = {}
            text: str = payload.pop("text", "")

            safe_meta: dict[str, str] = {
                str(key): str(value) for key, value in payload.items()
            }

            segment: Segment = Segment(text=text, metadata=safe_meta)
            results.append(segment)

        return results

    @property
    def count(self) -> int:
        """获取向量存储中的文档总数。"""
        collection_info = self.client.get_collection(self.collection_name)

        if collection_info.points_count:
            count: int = collection_info.points_count
        else:
            count = 0

        return count
