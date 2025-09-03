from typing import Any
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from .document_service import DocumentChunk
from .utility import get_folder_path


class VectorService:
    """向量存储服务"""

    def __init__(self) -> None:
        """构造函数"""
        # 直接使用固定值
        self.persist_dir: Path = get_folder_path("chroma_db")
        self.embedding_model: SentenceTransformer = SentenceTransformer("BAAI/bge-large-zh-v1.5")

        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False)    # 不发送匿名使用统计
        )

        # 获取或创建集合
        self.collection: chromadb.Collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}                      # 使用余弦相似度
        )

    def add_documents(self, chunks: list[DocumentChunk]) -> None:
        """添加文档分块到向量数据库"""
        if not chunks:
            return

        texts: list = [chunk.text for chunk in chunks]
        metadatas: list = [chunk.metadata for chunk in chunks]

        # 生成向量
        embeddings: list = self.embedding_model.encode(texts, show_progress_bar=False).tolist()

        # 生成ID
        ids: list = []
        for chunk in chunks:
            ids.append(f"{chunk.metadata['filename']}_{chunk.metadata['chunk_index']}")

        # 添加到ChromaDB
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

    def similarity_search(
        self,
        query: str,
        k: int = 5
    ) -> list[dict[str, Any]]:
        """相似性搜索"""
        # 没有collection就返回空列表
        if self.collection.count() == 0:
            return []

        # 生成查询向量
        query_embedding: list = self.embedding_model.encode([query]).tolist()

        # 执行搜索
        results: chromadb.QueryResult = self.collection.query(
            query_embeddings=query_embedding,
            n_results=k
        )

        # 简化类型处理，直接忽略索引类型检查
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]

        pairs: zip = zip(docs, metas, dists, strict=True)
        documents: list[dict[str, Any]] = []
        for t, m, d in pairs:
            documents.append({
                "text": t,
                "metadata": m,
                "distance": d
            })

        return documents

    def get_document_count(self) -> int:
        """获取文档数量"""
        document_count: int = self.collection.count()
        return document_count
