# 更新日志

本页面记录 VNAG 的版本更新历史。

## v0.7.0

最新版本。

### 新功能

- 新增 LitellmGateway，支持 LiteLLM AI 网关代理服务
- 添加联网搜索工具集（博查、Tavily、Serper、Jina 四种搜索 API）
- 新增基于 jina.ai 的 fetch_markdown 工具，用于获取网页 Markdown 内容
- 增加 Token 使用量的跟踪和显示
- 增加回答一键复制按钮

### 改进

- AgentEngine.list_models 增加异常处理，避免 UI 初始化显示失败
- 添加项目 Sphinx 文档

---

## v0.6.0

### 新功能

- 增加历史会话的思考内容显示

### 改进

- 模型下拉框仅显示当前可用模型
- 对于交错思维的思考输出强制换行
- 完成 OpenrouterGateway 的 Gemini 模型推理支持
- 优化报错信息对话框的显示

### 修复

- 修复关闭时信号对象销毁导致的报错
- 完善 OpenrouterGateway 的 Claude 系列模型支持
- 修复 DeepSeek 和 MiniMax 的工具调用数据传递问题

---

## v0.5.0

### 新功能

- 增加对于推理思考（thinking）内容的支持
- 添加 DeepseekGateway，支持思维链输出和输入
- 添加 MinimaxGateway，支持交错思维
- 添加 BailianGateway，阿里云百炼 AI 服务
- 添加 OpenrouterGateway，支持思考推理输出
- 添加 AI 服务配置对话框
- 支持 pythonw.exe 运行（重定向 std 输出）

### 改进

- AgentWidget 发送消息前检查 AI 服务是否已配置
- 支持 AI 服务配置中的列表选项
- 优化运行时目录的管理
- 标题生成独立处理，避免失败触发 abort_stream() 导致消息重复
- 优化会话历史的删除和重发
- 精简默认安装依赖项
- 支持模型名称中不包含厂商名的情况

---

### 核心模块

- **Agent**: TaskAgent 任务型智能体、AgentTool 智能体工具
- **Gateway**: 统一的大模型 API 接口（支持 OpenAI、Anthropic、Dashscope、DeepSeek、MiniMax、百炼、OpenRouter、LiteLLM）
- **Tool**: LocalManager 本地工具管理、McpManager MCP 工具管理
- **RAG**: Segmenter 分段器、Embedder 嵌入器、Vector 向量库
- **UI**: Chat UI 图形界面

### 内置工具

- datetime_tools: 日期时间工具
- file_tools: 文件系统工具
- network_tools: 网络工具
- code_tools: 代码执行工具
- web_tools: Web 工具
- search_tools: 联网搜索工具

---

*更多历史版本请查看 [CHANGELOG.md](https://github.com/vnpy/vnag/blob/main/CHANGELOG.md)*
