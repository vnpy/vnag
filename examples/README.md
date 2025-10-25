# VeighNa Agent 代码开发示例

该目录包含了 `vnag` 项目的各类功能代码示例，旨在帮助用户快速理解和使用 `vnag` 的核心组件。

每个子目录都聚焦于一个特定的功能模块，并提供了可直接运行的脚本。

## 目录说明

- **agent**: 演示如何使用 `AgentEngine` 驱动大模型，并结合工具调用来完成复杂任务。
- **gateway**: 演示如何通过各类 `Gateway` 接口与不同的大模型服务（如 OpenAI、Anthropic、阿里云百炼）进行交互。
- **rag**: 演示如何构建一个完整的 RAG（Retrieval-Augmented Generation）应用，包括知识库的解析、向量化、检索和生成。
- **segmenter**: 演示 `vnag` 中提供的多种文本及代码分段器的使用方法，用于将非结构化数据处理成结构化的知识片段。
- **tool**: 演示如何使用 `LocalManager` 和 `McpManager` 来管理和执行本地或外部的工具。
- **ui**: 演示如何启动一个基于 `vnag` 的图形化聊天界面，用于与大模型进行交互。
- **vector**: 演示如何与向量数据库（ChromaDB）进行交互，包括数据的新增和检索。
