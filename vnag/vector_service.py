import logging
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from .document_service import DocumentChunk
from .setting import SETTINGS
from .utility import get_folder_path


logger = logging.getLogger(__name__)


class VectorService:
    """向量存储服务"""

    def __init__(self) -> None:
        """构造函数"""
        self.persist_dir = get_folder_path(SETTINGS["vector_store.persist_directory"])
        self.embedding_model = SentenceTransformer(SETTINGS["embedding.model_name"])

        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )

        logger.info(f"Vector service initialized with {self.collection.count()} documents")

    def add_documents(self, chunks: list[DocumentChunk]) -> None:
        """添加文档分块到向量数据库"""
        if not chunks:
            return

        texts = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        # 生成向量
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=False)

        # 生成ID
        ids = [f"{chunk.metadata['filename']}_{chunk.metadata['chunk_index']}" 
               for chunk in chunks]

        # 添加到ChromaDB
        self.collection.add(
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

        logger.info(f"Added {len(chunks)} chunks to vector store")

    def similarity_search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """相似性搜索"""
        if self.collection.count() == 0:
            logger.warning("Vector store is empty")
            return []

        # 生成查询向量
        query_embedding = self.embedding_model.encode([query])

        # 执行搜索
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=k
        )

        # 格式化结果
        documents = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                documents.append({
                    'text': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0.0
                })

        logger.info(f"Found {len(documents)} similar documents for query")
        return documents

    def get_document_count(self) -> int:
        """获取文档数量"""
        return self.collection.count()

    def clear_documents(self) -> None:
        """清空所有文档"""
        # 删除现有集合
        self.client.delete_collection("documents")

        # 重新创建集合
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )

        logger.info("Cleared all documents from vector store")