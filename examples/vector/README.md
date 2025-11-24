# 向量数据库示例

该目录下的脚本用于演示如何使用 `vnag` 与向量数据库（ChromaDB）进行交互。

- `run_chromadb_add.py`: 演示了如何将 Markdown 文件进行分段处理，并将得到的文本块添加（写入）到 ChromaDB 向量数据库中。
- `run_chromadb_search.py`: 演示了如何根据给定的查询文本，从 ChromaDB 向量数据库中检索最相关的文本块。

**注意**：`ChromaVector` 支持可插拔的 Embedding 模型（本地 SentenceTransformer 或 DashScope API），写入和检索时必须使用相同的 `name` 和 `embedding_model`。具体用法见脚本内注释。
