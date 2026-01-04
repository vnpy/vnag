# 更新日志

本页面记录 VNAG 的版本更新历史。

## v0.6.0

最新版本。

### 新功能

- 支持多种大模型网关：OpenAI、Anthropic、Dashscope、DeepSeek、MiniMax、百炼、OpenRouter
- 思维链（Thinking）内容的提取和显示
- 完整的 RAG 支持：分段器、嵌入器、向量库
- 本地工具和 MCP 远程工具双核体系
- 基于 PySide6 的现代化图形界面
- 执行追踪和日志记录

### 核心模块

- **Agent**: TaskAgent 任务型智能体、AgentTool 智能体工具
- **Gateway**: 统一的大模型 API 接口
- **Tool**: LocalManager 本地工具管理、McpManager MCP 工具管理
- **RAG**: Segmenter 分段器、Embedder 嵌入器、Vector 向量库
- **UI**: Chat UI 图形界面

### 内置工具

- datetime_tools: 日期时间工具
- file_tools: 文件系统工具
- network_tools: 网络工具
- code_tools: 代码执行工具
- web_tools: Web 工具

---

*更多历史版本请查看 [CHANGELOG.md](https://github.com/vnpy/vnag/blob/main/CHANGELOG.md)*

