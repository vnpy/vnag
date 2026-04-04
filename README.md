# VNAG - Your Agent, Your Data.

<p align="center">
    <img src ="https://img.shields.io/badge/version-0.8.0-blueviolet.svg"/>
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
- **🧠 技能系统**: 两级加载机制，让智能体按需加载专业操作指南，避免上下文膨胀。
- **🔌 统一API接口**：支持OpenAI兼容的各种大模型API
- **🎨 现代化UI**：基于PySide6的图形化界面，不仅是聊天窗口，更是强大的智能体调试和管理工具。
- **⌨️ 命令行界面**：基于Prompt Toolkit的CLI交互界面，适合终端环境下使用。
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

1.  请参考 "配置" 章节的说明，在 `.vnag` 目录下创建一个 `connect_xxx.json` 文件（如 `connect_openai.json`、`connect_deepseek.json` 等）。
2.  打开该文件，填入对应服务的 API Key 和 Base URL。
3.  您也可以通过UI界面【菜单栏-功能-AI服务配置】可视化配置API服务。

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
  - **模型参数**: 如 `temperature`, `max_tokens` 等，用于控制模型的生成行为。需要注意的是，部分模型会固定使用 `1.0` 或忽略自定义温度。

**两种方式来自定义 Agent:**

1.  **通过UI界面（推荐）**:
    运行 `python examples/ui/run_chat_ui.py` 启动图形化界面。在界面中，您可以直观地创建和管理 Profile，然后基于选定的 Profile 创建 Agent 实例进行对话。

2.  **通过代码**:
    `examples/agent/run_task_agent.py` 脚本详细演示了如何通过代码来创建 `Profile` 对象，并使用 `AgentEngine` 来创建一个 `TaskAgent` 实例。这为您提供了更大的灵活性，可以将 vnag 集成到您自己的应用程序中。

## 功能示例

`examples` 目录提供了丰富的示例脚本，帮助您快速了解和掌握 vnag 框架的各项功能。所有示例均可在项目根目录下直接运行。

| 功能模块 | 示例脚本 | 说明 |
|---------|---------|------|
| **Gateway<br/>网关** | `run_completion_gateway.py`<br/>`run_anthropic_gateway.py`<br/>`run_dashscope_gateway.py`<br/>`run_ollama_gateway.py` | 测试与不同大模型提供商的 API 连接 |
| **Segmenter<br/>分段器** | `run_simple_segmenter.py`<br/>`run_markdown_segmenter.py`<br/>`run_python_segmenter.py`<br/>`run_cpp_segmenter.py` | 将不同类型的文档切分为结构化数据段 |
| **Vector<br/>向量库** | `run_chromadb_demo.py`<br/>`run_qdrant_demo.py`<br/>`run_duckdb_demo.py` | 文本向量化存储和相似度搜索 |
| **RAG** | `run_ctp_rag.py` | 完整的 RAG 流程：分段、入库、检索生成 |
| **Tool<br/>工具** | `run_local_tool.py`<br/>`run_mcp_tool.py` | 本地工具和 MCP 远程工具调用 |
| **Agent<br/>智能体** | `run_task_agent.py`<br/>`run_agent_tool.py` | 通过代码创建和配置 TaskAgent |
| **UI<br/>界面** | `run_chat_ui.py` | 图形化智能体管理和调试界面 |

运行示例：

```bash
# 示例：测试 OpenAI Gateway
python examples/gateway/run_completion_gateway.py

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

#### 网关连接配置

每个网关对应一个 `connect_{gateway_name}.json` 文件，存放在 `.vnag/` 目录下。

```json
// connect_openai.json（OpenAI 及兼容接口）
{
    "api_key": "sk-YourOpenAIKey",
    "base_url": "https://api.openai.com/v1"
}
```

```json
// connect_deepseek.json（DeepSeek，支持思维链推理）
{
    "api_key": "sk-YourDeepSeekKey",
    "base_url": "https://api.deepseek.com"
}
```

支持的网关：OpenAI、Anthropic、Dashscope、Ollama、DeepSeek、智谱、火山引擎、Moonshot、MiniMax、百炼、OpenRouter、LiteLLM、Bedrock、Gemini。各网关的完整配置示例请参考 [Gateway 文档](docs/source/components/gateway.md)。

#### MCP 配置

MCP 工具通过 `.vnag/mcp_config.json` 配置，依赖本地 [Node.js](https://nodejs.org/) 环境：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    }
  }
}
```

## 项目结构

```
vnag/
├── vnag/                # 核心框架
│   ├── agent.py         # 智能体（TaskAgent / AgentTool）
│   ├── engine.py        # 智能体引擎
│   ├── skill.py         # 技能系统
│   ├── gateways/        # 大模型网关（15 种）
│   ├── tools/           # 内置本地工具（9 类）
│   ├── segmenters/      # RAG 分段器
│   ├── embedders/       # RAG 嵌入器
│   ├── vectors/         # RAG 向量库
│   ├── ui/              # GUI 图形界面
│   └── cli/             # CLI 命令行界面
├── examples/            # 功能示例脚本
├── skills/              # 技能文件目录
└── docs/                # 项目文档
```

各模块的详细说明请参考 [核心概念](docs/source/getting_started/key_concepts.md) 和 [核心组件](docs/source/components/index.md) 文档。

### 内置工具

vnag 内置了日期时间、文件系统、网络、终端与系统、代码执行、Web、联网搜索、待办管理、交互提问等 9 类本地工具，开箱即用。其中文件系统工具支持全文读取、带行号分段读取、字符串替换与按行块替换，适合代码编辑与自动化修订场景；交互工具支持模型在 GUI 或 CLI 中主动向用户提问并等待回答。完整的工具列表和使用说明请参考 [Tool 文档](docs/source/components/tool.md)。

## 功能概览

| 模块 | 说明 |
|------|------|
| **Agent 引擎** | ReAct 循环编排、多轮对话、Profile 配置、技能系统、执行追踪 |
| **LLM 网关** | OpenAI、Anthropic、Dashscope、Ollama、DeepSeek、智谱、火山引擎、Moonshot、MiniMax、百炼、OpenRouter、LiteLLM、Bedrock、Gemini，支持流式输出和思维链 |
| **工具系统** | 本地函数工具、MCP 远程工具、9 类内置工具，支持交互式提问工具 |
| **RAG** | 4 种分段器（Simple / Markdown / Python / C++）、3 种嵌入器（OpenAI / Dashscope / SentenceTransformers）、3 种向量库（ChromaDB / Qdrant / DuckDB） |
| **图形界面** | 基于 PySide6 的聊天 UI，支持 Profile 管理、多智能体切换、Markdown 渲染、Thinking 显示和交互式工具提问 |
| **命令行界面** | 基于 Prompt Toolkit 的 CLI，支持自动补全、Markdown 终端渲染和交互式工具提问 |

详细的功能更新记录请参考 [CHANGELOG](CHANGELOG.md)。

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

# 运行测试
python -m unittest discover -s tests -p "test_*.py" -v
```

### 问题反馈

如果您遇到任何问题或有建议，请通过以下方式联系我们：

- 在GitHub上提交[Issue](https://github.com/vnpy/vnag/issues)
- 发送邮件至：contact@mail.vnpy.com

## 版权说明

本项目采用MIT开源协议，详情请参阅[LICENSE](LICENSE)文件。

---

**立即开始您的AI Agent开发之旅！🚀**
