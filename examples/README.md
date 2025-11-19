# VeighNa Agent 代码开发示例

该目录包含了 `vnag` 项目的各类功能代码示例，旨在帮助用户快速理解和使用 `vnag` 的核心组件。

每个子目录都聚焦于一个特定的功能模块，并提供了可直接运行的脚本。


## 快速开始

### 1. 安装依赖

运行示例前，请确保已安装 `vnag` 及其依赖：

部分示例需要额外的可选依赖：

- **UI 示例**：需要 `PySide6`（图形界面库）
- **Vector 示例**：需要 `chromadb` 或 `qdrant-client`（向量数据库）、`sentence-transformers`（向量嵌入模型）
- **Segmenter 示例**：需要 `libclang`（C++ 代码解析）
- **RAG 示例**：需要 `chromadb`（向量数据库）、`sentence-transformers`（向量嵌入模型）
- **MCP Tool 示例**：需要 `fastmcp`（MCP 协议支持）、Node.js 环境

如果遇到缺少依赖的错误，可以根据提示安装对应的包。


## 目录说明

- **agent**: 演示如何使用 `AgentEngine` 驱动大模型，并结合工具调用来完成复杂任务。
- **gateway**: 演示如何通过各类 `Gateway` 接口与不同的大模型服务（如 OpenAI、Anthropic、阿里云百炼）进行交互。
- **rag**: 演示如何构建一个完整的 RAG（Retrieval-Augmented Generation）应用，包括知识库的解析、向量化、检索和生成。
- **segmenter**: 演示 `vnag` 中提供的多种文本及代码分段器的使用方法，用于将非结构化数据处理成结构化的知识片段。
- **tool**: 演示如何使用 `LocalManager` 和 `McpManager` 来管理和执行本地或外部的工具。
- **ui**: 演示如何启动一个基于 `vnag` 的图形化聊天界面，用于与大模型进行交互。
- **vector**: 演示如何与向量数据库（ChromaDB 和 Qdrant）进行交互，包括数据的新增和检索。


## 示例说明

### Gateway 示例

- **run_openai_gateway**: 演示如何使用 `OpenaiGateway` 调用 OpenAI 风格的 API 接口，例如 OpenAI 官方服务、OpenRouter 聚合路由服务等。

    - 使用时需要将 `connect_openai.json` 文件放置在用户目录下的 `.vnag` 文件夹中

- **run_anthropic_gateway**: 演示如何使用 `AnthropicGateway` 调用 Anthropic 风格的 API 接口，例如 Anthropic 官方服务、Kimi-K2 服务等。

    - 使用时需要将 `connect_anthropic.json` 文件放置在用户目录下的 `.vnag` 文件夹中

- **run_dashscope_gateway**: 演示如何使用 `DashscopeGateway` 调用阿里云百炼大模型服务的 API 接口。

    - 使用时需要将 `connect_dashscope.json` 文件放置在用户目录下的 `.vnag` 文件夹中

### Vector 示例

- **run_chromadb_add**: 演示如何使用 `ChromaVector` 将 Markdown 文件进行分段处理，并添加到 ChromaDB 向量数据库中。

    - 默认使用本地 `SentenceEmbedder`（无需 API Key，首次运行会自动下载模型）
    - 如需使用 DashScope API，可参考脚本中的注释修改

- **run_chromadb_search**: 演示如何根据查询文本从 ChromaDB 向量数据库中检索最相关的文本块。

    - 使用时需要先确保已通过 `run_chromadb_add` 导入知识库
    - 默认使用本地 `SentenceEmbedder`（需与写入时使用相同的 embedder 和 name）

- **run_qdrant_add**: 演示如何使用 `QdrantVector` 将 Markdown 文件进行分段处理，并添加到 Qdrant 向量数据库中。

    - 默认使用本地 `SentenceEmbedder`（无需 API Key，首次运行会自动下载模型）
    - 如需使用 DashScope API，可参考脚本中的注释修改

- **run_qdrant_search**: 演示如何根据查询文本从 Qdrant 向量数据库中检索最相关的文本块。

    - 使用时需要先确保已通过 `run_qdrant_add` 导入知识库
    - 默认使用本地 `SentenceEmbedder`（需与写入时使用相同的 embedder 和 name）

### RAG 示例

- **run_ctp_rag**: 演示一个针对 CTP API 的 RAG 应用，解析 knowledge 目录下的 C++ 头文件，将其向量化后存储，并根据用户提问检索相关信息以生成回答。

    - 默认使用本地 `SentenceEmbedder`（无需 API Key，首次运行会自动下载模型）
    - 使用时需要将 `connect_openai.json` 文件放置在用户目录下的 `.vnag` 文件夹中（用于大模型回答）

### Segmenter 示例

- **run_cpp_segmenter**: 演示如何使用 `CppSegmenter` 解析 C++ 头文件。

    - 无需额外配置，脚本会自动解析示例头文件

- **run_markdown_segmenter**: 演示如何使用 `MarkdownSegmenter` 解析 Markdown 文件。

    - 无需额外配置，脚本会自动解析示例 Markdown 文件

- **run_python_segmenter**: 演示如何使用 `PythonSegmenter` 解析 Python 代码文件。

    - 无需额外配置，脚本会自动解析示例 Python 文件

- **run_simple_segmenter**: 演示如何使用 `SimpleSegmenter` 按固定长度对文本进行切分。

    - 无需额外配置，脚本会自动对示例文本进行分段

### Tool 示例

- **run_local_tool**: 演示如何使用 `LocalManager` 来列出和执行内置的本地工具（如获取当前时间、文件操作、网络检测等）。

    - 文件系统工具需要配置权限：在用户目录下的 `.vnag` 文件夹中创建 `file_system_tool.json` 文件
    - 配置格式示例：`{"read_allowed": ["D:/project"], "write_allowed": ["D:/project/output"]}`

- **run_mcp_tool**: 演示如何使用 `McpManager` 来列出和执行通过 MCP（Module Communication Protocol）协议发现的外部工具。

    - 使用时需要在用户目录下的 `.vnag` 文件夹中创建 `mcp_config.json` 文件
    - 配置格式示例：
    ```json
    {
      "mcpServers": {
        "filesystem": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
        },
        "sequential-thinking": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
        }
      }
    }
    ```
    - **server_name 说明**：`filesystem`、`sequential-thinking` 等是服务器的自定义名称，用于在配置中标识不同的 MCP 服务器。实际的工具名称由 MCP 服务器自身决定，例如 `@modelcontextprotocol/server-filesystem` 提供的工具名为 `file-tools_list-directory`
    - **文件系统路径参数**：`filesystem` 服务器的 args 中最后一个参数 `"."` 指定了允许访问的根目录。`"."` 表示当前目录，也可以指定绝对路径如 `"D:/project"` 来限制访问范围
    - **重要提示（Windows）**：MCP filesystem 工具会严格比对路径大小写。在 Windows 上，请确保使用与实际文件夹名大小写一致的路径进入目录。例如，如果文件夹是 `D:\GitHub\vnag`，请使用 `cd D:\GitHub\vnag`（大写 GitHub）而不是 `cd D:\github\vnag`（小写 github），否则会导致 "Access denied" 错误。在 JSON 配置文件中，建议使用正斜杠如 `"D:/GitHub/vnag"`
    - 需要确保已安装 Node.js（MCP 工具通过 npx 命令执行）

### Agent 示例

- **run_task_agent**: 演示如何初始化 `AgentEngine`，创建智能体配置（Profile），并通过调用本地工具和 MCP 工具来处理用户请求。脚本会在开始时打印所有可用的模型、配置和智能体列表，帮助用户选择合适的参数。

    - 使用时需要将 `connect_openai.json` 文件放置在用户目录下的 `.vnag` 文件夹中（用于大模型调用）
    - 需要在 `.vnag` 文件夹中创建 `mcp_config.json` 文件（用于 MCP 工具调用，如文件系统工具）
    - 脚本会自动打印可用模型、已有配置和智能体列表，方便用户参考
    - 示例中使用了本地工具（`day_of_week`）和 MCP 工具（`filesystem_list_directory`）

### UI 示例

- **run_chat_ui**: 演示如何初始化 `OpenaiGateway` 并启动 `MainWindow`，从而运行一个可以与大模型进行交互的聊天应用。

    - 使用时需要将 `connect_openai.json` 文件放置在用户目录下的 `.vnag` 文件夹中
