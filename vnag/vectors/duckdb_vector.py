import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
import duckdb
from duckdb import DuckDBPyConnection

from vnag.object import Segment
from vnag.utility import get_folder_path
from vnag.vector import BaseVector
from vnag.embedder import BaseEmbedder


class DuckdbVector(BaseVector):
    """基于 DuckDB VSS 扩展实现的向量存储。"""

    def __init__(
        self,
        name: str,
        embedder: BaseEmbedder
    ) -> None:
        """初始化 DuckDB 向量存储。"""
        self.persist_dir: Path = get_folder_path("duckdb_vector")
        self.db_path: Path = self.persist_dir.joinpath(f"{name}.duckdb")
        self.embedder: BaseEmbedder = embedder

        # 通过编码样本获取实际维度
        self.dimension: int = embedder.encode(["duckdb"]).shape[1]

        # 创建数据库连接
        self.conn: DuckDBPyConnection = duckdb.connect(str(self.db_path))

        # 初始化数据库
        self._init_database()

    def _init_database(self) -> None:
        """初始化数据库：安装扩展、创建表和索引。"""
        # 安装并加载 VSS 扩展
        self.conn.execute("INSTALL vss;")
        self.conn.execute("LOAD vss;")

        # 启用实验性持久化
        self.conn.execute("SET hnsw_enable_experimental_persistence = true;")

        # 创建表（如果不存在）
        create_table_sql: str = f"""
            CREATE TABLE IF NOT EXISTS segments (
                id VARCHAR PRIMARY KEY,
                text VARCHAR,
                metadata VARCHAR,
                embedding FLOAT[{self.dimension}]
            );
        """
        self.conn.execute(create_table_sql)

        # 检查索引是否存在，不存在则创建
        index_exists: bool = self._check_index_exists("segments_hnsw_idx")
        if not index_exists:
            create_index_sql: str = """
                CREATE INDEX segments_hnsw_idx ON segments
                USING HNSW(embedding) WITH (metric = 'cosine');
            """
            self.conn.execute(create_index_sql)

    def _check_index_exists(self, index_name: str) -> bool:
        """检查索引是否存在。"""
        result = self.conn.execute(
            "SELECT COUNT(*) FROM duckdb_indexes() WHERE index_name = ?",
            [index_name]
        ).fetchone()
        return result is not None and result[0] > 0

    def add_segments(self, segments: list[Segment]) -> list[str]:
        """将一批文档块添加到 DuckDB 中。"""
        if not segments:
            return []

        texts: list[str] = [seg.text for seg in segments]

        embeddings_np: NDArray[np.float32] = self.embedder.encode(texts)

        # 生成唯一ID
        ids: list[str] = [
            f"{seg.metadata['source']}_{seg.metadata['chunk_index']}"
            for seg in segments
        ]

        # 准备插入数据
        insert_sql: str = """
            INSERT OR REPLACE INTO segments (id, text, metadata, embedding)
            VALUES (?, ?, ?, ?);
        """

        # 分批插入
        db_batch_size: int = 1000
        for i in range(0, len(ids), db_batch_size):
            j: int = i + db_batch_size
            batch_ids: list[str] = ids[i:j]
            batch_texts: list[str] = texts[i:j]
            batch_segments: list[Segment] = segments[i:j]
            batch_embeddings: NDArray[np.float32] = embeddings_np[i:j]

            for seg_id, text, seg, embedding in zip(
                batch_ids,
                batch_texts,
                batch_segments,
                batch_embeddings,
                strict=True
            ):
                metadata_json: str = json.dumps(
                    seg.metadata, ensure_ascii=False
                )
                embedding_list: list[float] = embedding.tolist()
                self.conn.execute(
                    insert_sql,
                    [seg_id, text, metadata_json, embedding_list]
                )

        return ids

    def retrieve(self, query_text: str, k: int = 5) -> list[Segment]:
        """根据查询文本，从 DuckDB 中检索相似的文档块。"""
        if self.count == 0:
            return []

        query_embedding_np: NDArray[np.float32] = self.embedder.encode([query_text])
        query_embedding_list: list[float] = query_embedding_np[0].tolist()

        # 使用余弦相似度进行搜索
        # 注意：array_cosine_similarity 返回相似度（越大越相似）
        # 为与 ChromaDB 保持一致，转换为距离（1 - similarity）
        search_sql: str = f"""
            SELECT
                id,
                text,
                metadata,
                array_cosine_similarity(embedding, ?::FLOAT[{self.dimension}]) AS similarity
            FROM segments
            ORDER BY similarity DESC
            LIMIT ?;
        """

        results = self.conn.execute(
            search_sql,
            [query_embedding_list, k]
        ).fetchall()

        retrieved_results: list[Segment] = []
        for row in results:
            text: str = row[1]
            metadata_json: str = row[2]
            similarity: float = row[3]

            # 解析 metadata JSON
            metadata: dict[str, Any] = json.loads(metadata_json)
            safe_meta: dict[str, str] = {
                str(key): str(value) for key, value in metadata.items()
            }

            # 转换为距离（与 ChromaDB 一致）
            distance: float = 1.0 - similarity

            segment: Segment = Segment(
                text=text,
                metadata=safe_meta,
                score=distance
            )
            retrieved_results.append(segment)

        return retrieved_results

    def delete_segments(self, segment_ids: list[str]) -> bool:
        """根据ID列表，从 DuckDB 中删除一个或多个文档。"""
        if not segment_ids:
            return True

        try:
            # 使用参数化查询删除
            placeholders: str = ", ".join(["?"] * len(segment_ids))
            delete_sql: str = f"DELETE FROM segments WHERE id IN ({placeholders});"
            self.conn.execute(delete_sql, segment_ids)
            return True
        except Exception:
            return False

    def get_segments(self, segment_ids: list[str]) -> list[Segment]:
        """根据ID列表，从 DuckDB 中直接获取原始的文档块。"""
        if not segment_ids:
            return []

        placeholders: str = ", ".join(["?"] * len(segment_ids))
        select_sql: str = f"""
            SELECT id, text, metadata FROM segments
            WHERE id IN ({placeholders});
        """

        results = self.conn.execute(select_sql, segment_ids).fetchall()

        segments: list[Segment] = []
        for row in results:
            text: str = row[1]
            metadata_json: str = row[2]

            metadata: dict[str, Any] = json.loads(metadata_json)
            safe_meta: dict[str, str] = {
                str(key): str(value) for key, value in metadata.items()
            }

            segment: Segment = Segment(text=text, metadata=safe_meta)
            segments.append(segment)

        return segments

    def list_segments(self, limit: int = 100, offset: int = 0) -> list[Segment]:
        """分页获取向量存储中的文档块（不需要语义查询）。"""
        select_sql: str = """
            SELECT id, text, metadata FROM segments
            ORDER BY id
            LIMIT ? OFFSET ?;
        """

        results = self.conn.execute(select_sql, [limit, offset]).fetchall()

        segments: list[Segment] = []
        for row in results:
            text: str = row[1]
            metadata_json: str = row[2]

            metadata: dict[str, Any] = json.loads(metadata_json)
            safe_meta: dict[str, str] = {
                str(key): str(value) for key, value in metadata.items()
            }

            segment: Segment = Segment(text=text, metadata=safe_meta)
            segments.append(segment)

        return segments

    @property
    def count(self) -> int:
        """获取向量存储中的文档总数。"""
        result = self.conn.execute(
            "SELECT COUNT(*) FROM segments;"
        ).fetchone()

        if result is not None:
            count: int = result[0]
        else:
            count = 0

        return count
