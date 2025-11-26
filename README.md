# VNAG - Your Agent, Your Data.

<p align="center">
    <img src ="https://img.shields.io/badge/version-0.3.0-blueviolet.svg"/>
    <img src ="https://img.shields.io/badge/platform-windows|linux|macos-yellow.svg"/>
    <img src ="https://img.shields.io/badge/python-3.10|3.11|3.12|3.13-blue.svg" />
    <img src ="https://img.shields.io/github/license/vnpy/vnag.svg?color=orange"/>
</p>

<p align="center">
  <img src="https://vnag.oss-cn-shanghai.aliyuncs.com/vnag_0.2.0.png" width="800" alt="VNAG Screenshot">
</p>

VeighNa Agent (vnag) 是一款专为AI Agent开发而设计的Python框架，致力于为开发者提供简洁、强大且易于扩展的Agent构建工具。秉承"Your Agent, Your Data"的理念，vnag让您能够完全掌控自己的AI Agent和数据流程。

## 项目介绍

vnag是VeighNa团队推出的全新AI Agent开发框架，旨在降低AI Agent开发的门槛，让更多开发者能够快速构建属于自己的智能助手。

### 核心特点

- **🤖 可定制智能体**: 轻松创建和管理多个智能体，每个都可拥有独立的角色（系统提示词）、能力（工具集）和行为模式（模型参数）。
- **🔧 双核工具体系**: 同时支持简单易用的本地函数工具和功能强大的 MCP 远程工具。
- **🔌 统一API接口**：支持OpenAI兼容的各种大模型API
- **🎨 现代化UI**：基于PySide6的图形化界面，不仅是聊天窗口，更是强大的智能体调试和管理工具。
- **📝 智能对话**：支持Markdown渲染的聊天界面
- **💾 数据管控**：本地化的对话历史和配置管理
- **🧩 易于扩展**：清晰的模块化架构，便于二次开发

### 适用场景

- AI聊天机器人开发
- 智能客服系统
- 知识问答助手
- 个人AI助理
- 企业内部智能工具

## 环境准备与安装

### 1. 克隆项目

```bash
git clone https://github.com/vnpy/vnag.git
cd vnag
```

### 2. (推荐) 创建并激活虚拟环境

为了保持项目依赖的隔离，强烈建议您使用 Python 虚拟环境。

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
.\venv\Scripts\activate

# 激活虚拟环境 (macOS/Linux)
source venv/bin/activate
```

### 3. 安装依赖

```bash
# 从源码安装项目及其依赖
pip install -e .
```

## 快速开始

### 您的第一个 Agent (3步搞定)

跟随以下三个步骤，您将在3分钟内启动一个功能完备的聊天机器人UI。

**第1步：安装依赖**

如果您已经完成了上一章节 "环境准备与安装" 的操作，那么依赖已经安装完毕，可以跳过此步。

**第2步：配置API密钥**

vnag 需要 API 密钥来与大模型服务进行通信。

1.  请参考 "配置" 章节的说明，在 `.vnag` 目录下创建一个 `connect_openai.json` 文件。
2.  打开该文件，填入您的 OpenAI API Key 和 Base URL。

**第3步：运行聊天UI**

一切准备就绪！在项目根目录下运行以下命令：

```bash
python examples/ui/run_chat_ui.py
```

现在，您应该能看到一个美观的聊天窗口了！恭喜您成功运行了第一个 Agent！

运行后，您将看到一个完整的 Agent 管理界面。在这里，您可以创建和配置自己的智能体（Agent），定义它的系统提示词（System Prompt）、选择需要使用的工具、并调整模型参数（如温度）等。

### 自定义您的 Agent

vnag 0.2.0 引入了 `TaskAgent` 和 `Profile` 的概念，让您可以轻松定义和管理多个具有不同功能和行为的智能体。

**核心概念:**

- **Agent (智能体)**: 一个独立的智能体实例，拥有自己的对话历史和配置。
- **Profile (配置)**: 定义了 Agent 行为的配置模板，包括：
  - **系统提示词 (Prompt)**: 设定 Agent 的角色和行为准则。
  - **工具集 (Tools)**: 从本地工具和MCP工具中选择 Agent 可以使用的工具。
  - **模型参数**: 如 `temperature`, `max_tokens` 等，用于控制模型的生成行为。

**两种方式来自定义 Agent:**

1.  **通过UI界面（推荐）**:
    运行 `python examples/ui/run_chat_ui.py` 启动图形化界面。在界面中，您可以直观地创建和管理 Profile，然后基于选定的 Profile 创建 Agent 实例进行对话。

2.  **通过代码**:
    `examples/agent/run_task_agent.py` 脚本详细演示了如何通过代码来创建 `Profile` 对象，并使用 `AgentEngine` 来创建一个 `TaskAgent` 实例。这为您提供了更大的灵活性，可以将 vnag 集成到您自己的应用程序中。

## 功能示例

`examples` 目录提供了丰富的示例脚本，帮助您快速了解和掌握 vnag 框架的各项功能。所有示例均可在项目根目录下直接运行。

| 功能模块 | 示例脚本 | 说明 |
|---------|---------|------|
| **Gateway<br/>网关** | `run_openai_gateway.py`<br/>`run_anthropic_gateway.py`<br/>`run_dashscope_gateway.py` | 测试与不同大模型提供商的 API 连接 |
| **Segmenter<br/>分段器** | `run_simple_segmenter.py`<br/>`run_markdown_segmenter.py`<br/>`run_python_segmenter.py`<br/>`run_cpp_segmenter.py` | 将不同类型的文档切分为结构化数据段 |
| **Vector<br/>向量库** | `run_chromadb_add.py` / `run_chromadb_search.py`<br/>`run_qdrant_add.py` / `run_qdrant_search.py` | 文本向量化存储和相似度搜索 |
| **RAG** | `run_ctp_rag.py` | 完整的 RAG 流程：分段、入库、检索生成 |
| **Tool<br/>工具** | `run_local_tool.py`<br/>`run_mcp_tool.py` | 本地工具和 MCP 远程工具调用 |
| **Agent<br/>智能体** | `run_task_agent.py`<br/>`run_agent_tool.py` | 通过代码创建和配置 TaskAgent |
| **UI<br/>界面** | `run_chat_ui.py` | 图形化智能体管理和调试界面 |

运行示例：

```bash
# 示例：测试 OpenAI Gateway
python examples/gateway/run_openai_gateway.py

# 示例：运行聊天 UI
python examples/ui/run_chat_ui.py

# 其他示例类似，将对应路径和文件名替换即可
```

## 配置

vnag 采用统一的配置文件管理机制，所有配置文件都存放在名为 `.vnag` 的隐藏目录中。

### 加载逻辑

1.  **优先加载当前目录**：程序启动时，会首先检查当前工作路径下是否存在 `.vnag` 目录。如果存在，则会直接加载该目录下的所有配置文件。
2.  **备选用户主目录**：如果当前工作路径下没有 `.vnag` 目录，程序会自动在您的系统用户主目录（Home Directory）下寻找并使用 `.vnag` 目录。如果该目录不存在，程序会自动创建。

通过这种方式，您可以为不同的项目设置独立的本地配置，或者配置一个全局共享的配置。

### 配置文件示例

#### 1. 网关连接配置

用于存储访问各类大模型 API 所需的密钥（key）、基地址（base_url）等信息。每个网关对应一个独立的 JSON 文件。

- **文件名**：`connect_{gateway_name}.json` (例如: `connect_openai.json`)
- **存放路径**：`.vnag/`

**`connect_openai.json` 示例:**
```json
{
    "api_key": "sk-YourOpenAIKey",
    "base_url": "https://api.openai.com/v1"
}
```

#### 2. MCP 配置

用于连接 `fastmcp` 元计算平台，以调用远程工具。

- **文件名**：`mcp_config.json`
- **存放路径**：`.vnag/`

**`mcp_config.json` 示例:**
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

> **注意**：MCP 服务通过 `npx` 命令执行，这依赖于本地的 [Node.js](https://nodejs.org/) 环境。请确保您已正确安装 Node.js（建议使用 LTS 版本）。

## 项目结构

```
vnag/
├── vnag/                       # 核心模块
│   ├── __init__.py            # 版本信息
│   ├── object.py              # 数据对象（Message/Request等）
│   ├── constant.py            # 枚举常量
│   ├── utility.py             # 工具函数
│   ├── agent.py               # Agent基类
│   ├── engine.py              # Agent引擎
│   ├── tracer.py              # 执行追踪器
│   ├── gateway.py             # 网关基类
│   ├── gateways/              # 网关实现
│   │   ├── openai_gateway.py
│   │   ├── anthropic_gateway.py
│   │   └── dashscope_gateway.py
│   ├── embedder.py            # 嵌入器基类
│   ├── embedders/             # 嵌入器实现
│   │   ├── openai_embedder.py
│   │   ├── dashscope_embedder.py
│   │   └── sentence_embedder.py
│   ├── segmenter.py           # 分段器基类
│   ├── segmenters/            # 分段器实现
│   │   ├── simple_segmenter.py
│   │   ├── markdown_segmenter.py
│   │   ├── python_segmenter.py
│   │   └── cpp_segmenter.py
│   ├── vector.py              # 向量库基类
│   ├── vectors/               # 向量库实现
│   │   ├── chromadb_vector.py
│   │   └── qdrant_vector.py
│   ├── local.py               # 本地工具管理器
│   ├── mcp.py                 # MCP远程工具管理器
│   ├── tools/                 # 内置本地工具
│   │   ├── datetime_tools.py  # 日期时间工具
│   │   ├── file_tools.py      # 文件系统工具
│   │   ├── network_tools.py   # 网络工具
│   │   ├── code_tools.py      # 代码工具
│   │   └── web_tools.py       # Web工具
│   └── ui/                    # GUI界面实现
│       ├── base.py            # UI基类
│       ├── qt.py              # Qt主界面
│       ├── widget.py          # 界面组件
│       ├── window.py          # 窗口管理
│       ├── worker.py          # 异步工作线程
│       ├── setting.py         # 设置管理
│       ├── logo.ico           # 应用图标
│       └── resources/         # 前端资源
├── examples/                  # 功能示例脚本集合
│   ├── agent/                 # Agent示例
│   │   ├── run_task_agent.py  # 任务型Agent
│   │   └── run_agent_tool.py  # Agent工具调用
│   ├── gateway/               # 网关示例
│   │   ├── run_openai_gateway.py
│   │   ├── run_anthropic_gateway.py
│   │   └── run_dashscope_gateway.py
│   ├── segmenter/             # 分段器示例
│   │   ├── run_simple_segmenter.py
│   │   ├── run_markdown_segmenter.py
│   │   ├── run_python_segmenter.py
│   │   └── run_cpp_segmenter.py
│   ├── vector/                # 向量库示例
│   │   ├── run_chromadb_add.py
│   │   ├── run_chromadb_search.py
│   │   ├── run_qdrant_add.py
│   │   └── run_qdrant_search.py
│   ├── rag/                   # RAG示例
│   │   ├── run_ctp_rag.py
│   │   └── knowledge/         # 示例知识库
│   ├── tool/                  # 工具调用示例
│   │   ├── run_local_tool.py
│   │   └── run_mcp_tool.py
│   └── ui/                    # UI示例
│       └── run_chat_ui.py
├── dist/                      # 发布包
├── pyproject.toml             # 项目配置
├── README.md                  # 项目文档
├── CHANGELOG.md               # 更新日志
└── LICENSE                    # 开源协议
```

### 核心模块说明

- **`object.py`**: 定义了框架中所有核心数据对象，如 `Message`, `Request`, `ToolCall` 等。
- **`constant.py`**: 定义了框架使用的枚举常量，如角色类型、工具调用状态等。
- **`utility.py`**: 提供通用工具函数，如配置文件加载、JSON处理等。
- **`agent.py`**: Agent 基类，定义了智能体的基本接口和行为规范。
- **`engine.py`**: Agent 引擎，负责对话管理、工具调用编排和与大模型交互。
- **`tracer.py`**: 执行追踪器，用于记录和调试 Agent 的执行过程。
- **`gateway.py` & `gateways/`**: 定义了与大模型 API 通信的统一接口，并提供了 OpenAI、Anthropic、Dashscope 等多种实现。
- **`embedder.py` & `embedders/`**: 定义了文本嵌入的统一接口，并提供了 OpenAI、Dashscope、Sentence Transformers 等多种实现。
- **`segmenter.py` & `segmenters/`**: 用于将文档（如 Markdown、Python、C++ 源码）解析为结构化数据段，是 RAG 的基础。
- **`vector.py` & `vectors/`**: 向量数据库的统一接口和实现（支持 ChromaDB 和 Qdrant），用于存储和检索知识片段。
- **`local.py`**: 本地工具管理器，可以自动加载和执行本地 Python 函数作为工具。
- **`mcp.py`**: MCP（元计算平台）工具管理器，用于连接 `fastmcp` 服务，实现在远端执行更复杂的工具。
- **`tools/`**: 提供一系列开箱即用的本地工具（日期时间、文件系统、网络、代码、Web等），详情请见下方"内置本地工具"章节。
- **`ui/`**: 基于 PySide6 的图形用户界面，提供一个开箱即用的聊天应用，包含完整的 Agent 管理和调试功能。
- **`examples/`**: 包含各个模块的独立示例脚本，是学习和测试框架功能的最佳入口。

### 内置本地工具

`vnag` 在 `vnag/tools/` 目录下提供了一系列开箱即用的本地工具，方便 Agent 直接调用。

#### 日期时间工具 (`datetime_tools.py`)

- **current_date**: 获取 YYYY-MM-DD 格式的当前日期字符串。
- **current_time**: 获取 HH:MM:SS 格式的当前时间字符串。
- **current_datetime**: 获取 YYYY-MM-DD HH:MM:SS 格式的当前日期和时间字符串。
- **day_of_week**: 获取中文格式的当天星期数（如：星期一）。

#### 文件系统工具 (`file_tools.py`)

> **安全说明**：文件系统工具的使用受到权限控制。您需要在 `.vnag/file_system_tool.json` 配置文件中明确指定允许读写的路径，以防止 Agent 访问未授权的文件。

- **list_directory**: 列出指定路径下的所有文件和子目录。
- **read_file**: 读取指定文件的文本内容（自动检测编码）。
- **write_file**: 将文本内容写入到指定文件（如果文件已存在，则会覆盖）。
- **delete_file**: 删除指定路径的文件。
- **glob_files**: 根据给定的模式和路径，匹配符合条件的文件。
- **search_content**: 在指定路径下递归搜索包含指定内容的文件。
- **replace_content**: 替换指定文件中的内容。

#### 网络工具 (`network_tools.py`)

- **ping**: 通过执行 ping 命令检查与主机的网络连通性。
- **telnet**: 通过尝试建立套接字连接来测试目标主机的端口是否开放。
- **get_local_ip**: 获取本机的局域网 IP 地址。
- **get_public_ip**: 通过请求外部服务获取本机的公网 IP 地址。
- **get_mac_address**: 获取本机的 MAC 地址，格式为 XX:XX:XX:XX:XX:XX。

#### 代码执行工具 (`code_tools.py`)

> **安全警告**：代码执行工具会在独立进程中执行 Python 代码，但并未提供安全的沙箱环境。被执行的代码将拥有与主进程相同的权限，包括文件系统和网络访问权限。请仅对可信代码和文件使用此功能。

- **execute_file**: 在独立进程中执行指定路径的 Python 文件（默认超时30秒）。
- **execute_code**: 在独立进程中执行 Python 代码字符串（默认超时30秒）。

#### Web工具 (`web_tools.py`)

- **fetch_html**: 获取并返回指定 URL 的 HTML 内容。
- **fetch_json**: 获取并解析来自 URL 的 JSON 数据。
- **check_link**: 检查链接的 HTTP 状态码和状态信息。

## 开发状态

### 当前功能 ✅

- [x] **Agent引擎**：
    - [x] 支持多轮对话管理
    - [x] 自动工具调用编排
    - [x] 可配置的 Profile 系统（系统提示词、工具集、模型参数）
    - [x] 执行追踪和日志记录
- [x] **LLM网关**：
    - [x] OpenAI API 兼容
    - [x] Anthropic Claude API 支持
    - [x] 阿里云 Dashscope API 支持
    - [x] 流式输出和非流式输出
    - [x] 统一的网关接口，易于扩展
- [x] **嵌入器**：
    - [x] OpenAI Embeddings
    - [x] Dashscope Embeddings
    - [x] Sentence Transformers（本地嵌入模型）
- [x] **RAG支持**：
    - [x] **分段器**：Simple（固定长度）、Markdown（按标题层级）、Python（AST语法树）、C++（libclang AST）
    - [x] **向量库**：集成 ChromaDB 和 Qdrant，支持高效的本地向量存储和检索
    - [x] 完整的 RAG 流程示例
- [x] **工具系统**：
    - [x] **本地工具**：自动加载 Python 函数作为工具，支持类型提示和文档字符串
    - [x] **MCP工具**：通过 MCP 客户端集成远程工具服务器
    - [x] **内置工具**：日期时间、文件系统、网络、代码执行、Web 工具
- [x] **图形界面**：
    - [x] 基于 PySide6 的现代化聊天 UI
    - [x] Profile 配置管理（创建、编辑、删除）
    - [x] Agent 实例管理（多智能体切换）
    - [x] Markdown 渲染和代码高亮
    - [x] 执行追踪日志查看
- [x] **示例脚本**：覆盖所有核心功能的详细 `examples` 示例，包括网关、分段器、向量库、RAG、工具调用、Agent 和 UI。

## 常见问题 (FAQ)

**Q: 运行 `python examples/xxx.py` 报错 `ModuleNotFoundError: No module named 'vnag'`?**

**A:** 这是因为您没有正确安装项目。请确保您已经在项目根目录下，并且**已激活虚拟环境**，然后执行 `pip install -e .` 命令。这个命令会以可编辑模式安装项目，让 Python 解释器能够找到 `vnag` 模块。

**Q: 程序启动了，但是请求大模型API时报错怎么办？**

**A:** 请仔细检查 `.vnag` 目录下的 `connect_xxx.json` 配置文件。确认 `api_key` (密钥) 和 `base_url` (API地址) 都已正确填写。同时，请确保您的网络环境可以正常访问该 API 地址。

**Q: 运行MCP相关示例时，提示 `npx` 不是内部或外部命令？**

**A:** 这个错误表示您的系统中没有安装 Node.js，或者 Node.js 的路径没有被添加到系统环境变量中。请参考本文档 "配置" 章节中的提示，从 [Node.js官网](https://nodejs.org/) 下载并安装 LTS (长期支持) 版本。

**Q: 使用文件系统工具时提示"没有权限访问"怎么办？**

**A:** 出于安全考虑，文件系统工具需要明确的权限配置。请在 `.vnag/file_system_tool.json` 文件中的 `read_allowed` 或 `write_allowed` 数组中添加您需要访问的目录路径。配置文件会在首次加载工具时自动生成。

**Q: 如何为不同的项目使用不同的配置？**

**A:** vnag 支持项目级配置。只需在项目目录下创建 `.vnag` 文件夹并放置配置文件即可。程序会优先加载当前目录下的配置，如果不存在则使用用户主目录下的全局配置。

**Q: UI 界面中创建的 Agent 和 Profile 保存在哪里？**

**A:** 所有 Agent 实例和 Profile 配置都保存在 `.vnag` 目录下，以 JSON 格式存储。您可以直接编辑这些文件，或者在 UI 界面中进行管理。

**Q: 运行 C++ 分段器时报错找不到 libclang？**

**A:** C++ 分段器依赖 libclang 库。请确保您已安装 LLVM/Clang，并且系统能够找到 `libclang` 动态链接库。在 Windows 上，可能需要将 LLVM 的 bin 目录添加到 PATH 环境变量中。

**Q: 如何自定义本地工具？**

**A:** 创建一个 Python 函数，并使用 `LocalTool` 包装即可。函数需要有清晰的类型提示和文档字符串，以便 Agent 理解如何使用。可以参考 `vnag/tools/` 目录下的示例。

## 贡献代码

我们欢迎所有形式的贡献！无论是bug报告、功能建议还是代码贡献。

### 开发流程

1. **Fork 本项目**：点击 GitHub 页面右上角的 Fork 按钮
2. **克隆到本地**：`git clone https://github.com/your-username/vnag.git`
3. **创建功能分支**：`git checkout -b feature/AmazingFeature`
4. **进行开发**：编写代码、添加测试、更新文档
5. **提交更改**：`git commit -m 'Add some AmazingFeature'`
6. **推送到远程**：`git push origin feature/AmazingFeature`
7. **提交 Pull Request**：在 GitHub 上创建 PR，详细描述您的更改

### 代码规范

项目使用以下工具确保代码质量：

- **Ruff**：代码格式化和 linting
- **MyPy**：静态类型检查

在提交代码前，请运行：

```bash
# 代码检查
ruff check .

# 类型检查
mypy vnag
```

### 问题反馈

如果您遇到任何问题或有建议，请通过以下方式联系我们：

- 在GitHub上提交[Issue](https://github.com/vnpy/vnag/issues)
- 发送邮件至：contact@mail.vnpy.com

## 版权说明

本项目采用MIT开源协议，详情请参阅[LICENSE](LICENSE)文件。

---

**立即开始您的AI Agent开发之旅！🚀**
