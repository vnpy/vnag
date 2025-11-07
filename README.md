# VNAG - Your Agent, Your Data.

<p align="center">
    <img src ="https://img.shields.io/badge/version-0.0.1-blueviolet.svg"/>
    <img src ="https://img.shields.io/badge/platform-windows|linux|macos-yellow.svg"/>
    <img src ="https://img.shields.io/badge/python-3.10|3.11|3.12|3.13-blue.svg" />
    <img src ="https://img.shields.io/github/license/vnpy/vnag.svg?color=orange"/>
</p>

<p align="center">
  <img src="https://vnag.oss-cn-shanghai.aliyuncs.com/vnag_0.1.0.png" width="800" alt="VNAG Screenshot">
</p>

VeighNa Agent (vnag) 是一款专为AI Agent开发而设计的Python框架，致力于为开发者提供简洁、强大且易于扩展的Agent构建工具。秉承"Your Agent, Your Data"的理念，vnag让您能够完全掌控自己的AI Agent和数据流程。

## 项目介绍

vnag是VeighNa团队推出的全新AI Agent开发框架，旨在降低AI Agent开发的门槛，让更多开发者能够快速构建属于自己的智能助手。

### 核心特点

- **🤖 Agent 引擎**: 强大的 Agent 引擎，负责对话流程编排和多轮工具调用。
- **🔧 双核工具体系**: 同时支持简单易用的本地函数工具和功能强大的 MCP 远程工具。
- **🔌 统一API接口**：支持OpenAI兼容的各种大模型API
- **🎨 现代化UI**：基于PySide6的美观用户界面
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

### 更多示例

通过 `examples` 目录下的丰富示例，您可以快速了解和掌握 vnag 框架的各项功能。

所有示例均可在项目根目录下直接运行。

### 网关（Gateway）

- 功能：测试与不同大模型提供商的 API 连接。
- 示例：
  ```bash
  # 测试 OpenAI Gataway
  python examples/gateway/run_openai_gateway.py
  ```

### 分段器（Segmenter）

- 功能：展示如何将不同类型的文档（Markdown, Python, C++）切分为结构化的数据段。
- 示例：
  ```bash
  # 运行 Markdown 分段器
  python examples/segmenter/run_markdown_segmenter.py
  ```

### 向量库（Vector）

- 功能：演示如何将文本数据向量化后存入向量数据库（ChromaDB 或 Qdrant），并进行相似度搜索。
- 示例：
  ```bash
  # 添加数据到 ChromaDB
  python examples/vector/run_chromadb_add.py

  # 从 ChromaDB 搜索数据
  python examples/vector/run_chromadb_search.py

  # 添加数据到 Qdrant
  python examples/vector/run_qdrant_add.py

  # 从 Qdrant 搜索数据
  python examples/vector/run_qdrant_search.py
  ```

### RAG

- 功能：一个完整的 RAG（检索增强生成）流程，结合了分段、入库和检索生成。
- 示例：
  ```bash
  # 运行一个基于CTP API文档的RAG问答
  python examples/rag/run_ctp_rag.py
  ```

### 工具调用（Tool）

- 功能：演示 Agent 如何调用本地或远程（MCP）工具。
- 示例：
  ```bash
  # 运行本地工具调用
  python examples/tool/run_local_tool.py
  ```

### Agent引擎

- 功能：展示 Agent 引擎如何编排对话流和工具调用。
- 示例：
  ```bash
  # 运行 Agent 引擎
  python examples/agent/run_agent_engine.py
  ```

### UI 界面

- 功能：启动一个完整的图形化聊天界面。
- 示例：
  ```bash
  # 运行聊天UI
  python examples/ui/run_chat_ui.py
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
│   ├── gateway.py             # 网关基类
│   ├── segmenter.py           # 分段器基类
│   ├── vector.py              # 向量库基类
│   ├── embedder.py            # 嵌入模型基类
│   ├── local.py               # 本地工具管理器
│   ├── mcp.py                 # MCP远程工具管理器
│   ├── engine.py              # Agent引擎
│   ├── gateways/              # 网关实现（OpenAI/Anthropic/Dashscope）
│   ├── segmenters/            # 分段器实现（Markdown/Python/C++/Simple）
│   ├── vectors/               # 向量库实现（ChromaDB/Qdrant）
│   ├── embedders/             # 嵌入模型实现（Dashscope/SentenceTransformer）
│   ├── tools/                 # 本地工具实现示例
│   └── ui/                    # GUI界面实现
├── examples/                  # 功能示例脚本集合
├── pyproject.toml             # 项目配置
├── README.md                  # 项目文档
└── LICENSE                    # 开源协议
```

### 核心模块说明

- **`engine.py`**: Agent 引擎，负责对话管理、工具调用编排和与大模型交互。
- **`gateway.py` & `gateways/`**: 定义了与大模型 API 通信的统一接口，并提供了 OpenAI、Anthropic、Dashscope 等多种实现。
- **`segmenter.py` & `segmenters/`**: 用于将文档（如 Markdown、Python、C++ 源码）解析为结构化数据段，是 RAG 的基础。
- **`vector.py` & `vectors/`**: 向量数据库的统一接口和实现（支持 ChromaDB 和 Qdrant），用于存储和检索知识片段。
- **`embedder.py` & `embedders/`**: 文本嵌入模型的统一接口和实现（支持 Dashscope API 和本地 SentenceTransformer），用于将文本转换为向量。
- **`local.py`**: 本地工具管理器，可以自动加载和执行本地 Python 函数作为工具。
- **`mcp.py`**: MCP（元计算平台）工具管理器，用于连接 `fastmcp` 服务，实现在远端执行更复杂的工具。
- **`tools/`**: 提供一系列开箱即用的本地工具，详情请见下方“内置本地工具”章节。
- **`ui/`**: 基于 PySide6 的图形用户界面，提供一个开箱即用的聊天应用。
- **`object.py`**: 定义了框架中所有核心数据对象，如 `Message`, `Request`, `ToolCall` 等。
- **`examples/`**: 包含各个模块的独立示例脚本，是学习和测试框架功能的最佳入口。

### 内置本地工具

`vnag` 在 `vnag/tools/` 目录下提供了一系列开箱即用的本地工具，方便 Agent 直接调用。

#### 日期时间工具 (`datetime_tools.py`)

- **get_current_date**: 获取 YYYY-MM-DD 格式的当前日期。
- **get_current_time**: 获取 HH:MM:SS 格式的当前时间。
- **get_current_datetime**: 获取 YYYY-MM-DD HH:MM:SS 格式的当前日期和时间。
- **get_day_of_week**: 获取中文格式的当天星期数（如：星期一）。

#### 文件系统工具 (`file_tools.py`)

> **安全说明**：文件系统工具的使用受到权限控制。您需要在 `.vnag/file_system_tool.json` 配置文件中明确指定允许读写的路径，以防止 Agent 访问未授权的文件。

- **list_directory**: 列出指定路径下的所有文件和子目录。
- **read_file**: 读取指定文件的文本内容。
- **write_file**: 将指定的文本内容写入文件（会覆盖已有内容）。

#### 网络工具 (`network_tools.py`)

- **ping**: 检查与目标主机的网络连通性。
- **telnet**: 测试目标主机上的特定端口是否开放。
- **get_local_ip**: 获取本机的局域网 IP 地址。
- **get_public_ip**: 获取本机的公网 IP 地址。
- **get_mac_address**: 获取本机的 MAC 地址。

## 开发状态

### 当前功能 ✅

- [x] **Agent引擎**：支持多轮对话和自动工具调用编排。
- [x] **LLM网关**：兼容 OpenAI、Anthropic、Dashscope API，支持流式输出。
- [x] **RAG支持**：
    - [x] **分段器**：Markdown（按标题）、Python（AST）、C++（libclang AST）。
    - [x] **向量库**：集成 ChromaDB，支持高效的本地向量存储和检索。
- [x] **工具系统**：
    - [x] **本地工具**：自动加载 Python 函数作为工具。
    - [x] **MCP工具**：通过 `fastmcp` 客户端集成远程工具。
- [x] **图形界面**：基于 PySide6 的现代化聊天 UI。
- [x] **示例脚本**：覆盖所有核心功能的详细 `examples` 示例。

## 常见问题 (FAQ)

**Q: 运行 `python examples/xxx.py` 报错 `ModuleNotFoundError: No module named 'vnag'`?**

**A:** 这是因为您没有正确安装项目。请确保您已经在项目根目录下，并且**已激活虚拟环境**，然后执行 `pip install -e .` 命令。这个命令会以可编辑模式安装项目，让 Python 解释器能够找到 `vnag` 模块。

**Q: 程序启动了，但是请求大模型API时报错怎么办？**

**A:** 请仔细检查 `.vnag` 目录下的 `connect_xxx.json` 配置文件。确认 `api_key` (密钥) 和 `base_url` (API地址) 都已正确填写。同时，请确保您的网络环境可以正常访问该 API 地址。

**Q: 运行MCP相关示例时，提示 `npx` 不是内部或外部命令？**

**A:** 这个错误表示您的系统中没有安装 Node.js，或者 Node.js 的路径没有被添加到系统环境变量中。请参考本文档 "配置" 章节中的提示，从 [Node.js官网](https://nodejs.org/) 下载并安装 LTS (长期支持) 版本。

## 贡献代码

我们欢迎所有形式的贡献！无论是bug报告、功能建议还是代码贡献。

### 开发流程

1. Fork本项目
2. 创建您的功能分支：`git checkout -b feature/AmazingFeature`
3. 提交您的更改：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 提交Pull Request

### 代码规范

项目使用以下工具确保代码质量：

- **Ruff**：代码格式化和linting
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
- 发送邮件至：xiaoyou.chen@mail.vnpy.com

## 版权说明

本项目采用MIT开源协议，详情请参阅[LICENSE](LICENSE)文件。

---

**立即开始您的AI Agent开发之旅！🚀**
