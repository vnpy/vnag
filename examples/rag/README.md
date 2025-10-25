# RAG 示例

该目录下的脚本用于演示如何基于 `vnag` 构建并运行一个完整的 RAG（Retrieval-Augmented Generation）应用。

- `run_ctp_rag.py`: 演示了一个针对 CTP API 的 RAG 应用，它会解析 `knowledge` 目录下的 C++ 头文件，将其向量化后存储，并根据用户提问，检索相关信息以生成回答。
- `knowledge`: 存放 RAG 应用所需的知识库源文件。
