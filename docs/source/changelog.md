# 更新日志

本页面记录 VNAG 的版本更新历史。

## v0.9.0

最新版本。

### 新功能

- 基于 Responses 交互的新版 OpenaiGateway
- 新增 BedrockGateway
- 新增 GeminiGateway
- 新增 OllamaGateway
- 会话历史导出功能
- 待办任务列表工具
- 用户提问交互工具
- 会话上下文自动压缩

### 改进

- 优化工具执行调度逻辑
- 设定生成标题默认温度为 1，适配当前多数 AI 接口
- 延迟导入 embedder 模块，优化启动速度
- 增强文件相关工具

### 修复

- 修复工具调用重复的问题

---

## v0.8.0

### 新功能

- 添加 DuckDB 向量化数据库支持
- 增加本地知识库功能
- 新增 Agent Skill 的支持
- 新增 MoonshotGateway、ZhipuGateway、VolcengineGateway
- 增加终端工具模块 terminal_tools
- 新增 CLI 交互模式

### 改进

- Embedder 类增加默认名称和参数
- Vector 类增加 list_segments 函数
- 增加 AI 服务的网络代理支持
- 优化回答内容中代码片段的展示
- 优化会话历史的删除和重发
- 当前会话返回结束前禁止发送新的请求
- 优化 TaskAgent 的 ReAct 执行
- 优化日志追踪模块

### 修复

- 修复 LiteLLM 接口的 content 缺失问题
- 修复停止请求后导致的状态异常问题

---

## v0.7.0

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

## v0.4.0

### 新功能

- 增加托盘栏小图标
- HistoryWidget 自动显示当前智能体欢迎语
- input_widget 关闭富文本支持

### 改进

- 实现 HistoryWidget 缩放系数自动存储
- 自动切换运行目录到 .vnag 所在路径
- 优化 CppSegmenter 分段器，过滤 include 文件内容

---

## v0.3.0

### 新功能

- AgentEngine 添加工具注册函数
- 添加 openai_embedder 子模块
- 添加 AgentTool，实现 Multi-Agent 支持

### 改进

- 避免 loguru 日志记录和其他库冲突
- 添加参数用于控制会话持久化

### 修复

- 修复 logger 初始化问题
- 修复仅有一个 MCP 服务时，服务名前缀的缺失问题

---

## v0.2.0

### 新功能

- 添加智能体配置数据结构
- 添加 TaskAgent 并调整 AgentEngine 完成适配
- 添加执行细节日志跟踪器
- 添加 Python 代码执行工具
- 添加 Web 访问相关工具
- 丰富本地文件工具
- 添加嵌入模型开发模板 embedder 类
- 添加 Qdrant 向量化数据库支持
- 添加 SessionWidget 并重构聊天窗口

### 改进

- 日志记录器调整为跟踪 TaskAgent
- 调整本地工具命名和 MCP 一致
- 修改 UI 界面支持 TaskAgent 交互
- 增加模型信息查询对话框
- 优化功能对话框控件细节
- 实现会话的删除和重发
- 实现 Enter 发送，Shift+Enter 换行
- 实现自动生成会话名称
- 更新项目示例 examples

---

## v0.1.0

### 新功能

- 添加基础框架
- 重构 BaseGateway，并实现 OpenaiGateway
- 实现 AnthropicGateway
- 阿里云 DashscopeGateway（目前不支持工具调用）
- 添加 list_models 函数用于查询所有支持的模型名称
- 流式调用 stream 接口支持
- 本地工具调用功能
- MCP 工具调用功能
- 新增文件系统本地工具集
- 新增网络本地工具集
- 新增 Agent 引擎，并调整 OpenaiGateway 支持工具调用
- 增加 UI 组件的 AgentEngine 工具调用支持
- 重构 UI 相关组件功能
- 添加基于 HTML 渲染 Markdown 返回内容
- 连接状态显示和关于信息
- 增加历史持久化功能
- 增加清空会话历史功能
- 使用 QWebEngineView 重构实现 HistoryWidget
- 添加文本分段器 BaseSegmenter
- 实现普通文本、Markdown 和 Python 分段器
- C++ 代码分段器
- 增加通用代码章节分割函数 pack_section
- 添加向量化数据库 BaseVector
- 添加 ChromaDB 支持
- 针对 CTP API 开发的 RAG 基础 Demo
- 整理新的代码开发示例目录

---

### 核心模块

- **Agent**: TaskAgent 任务型智能体、AgentTool 智能体工具
- **Gateway**: 统一的大模型 API 接口（含基于 Responses 的 OpenaiGateway，以及 OpenAI、Anthropic、Dashscope、DeepSeek、MiniMax、百炼、OpenRouter、LiteLLM、Moonshot、智谱、火山引擎、Bedrock、Gemini、Ollama 等）
- **Tool**: LocalManager 本地工具管理、McpManager MCP 工具管理
- **RAG**: Segmenter 分段器、Embedder 嵌入器、Vector 向量库（ChromaDB、Qdrant、DuckDB）
- **UI**: Chat UI 图形界面
- **CLI**: 命令行交互界面

### 内置工具

- datetime_tools: 日期时间工具
- file_tools: 文件系统工具
- network_tools: 网络工具
- code_tools: 代码执行工具
- web_tools: Web 工具
- search_tools: 联网搜索工具
- terminal_tools: 终端命令工具
- todo_tools: 进程内待办工具
- interaction_tools: 用户提问交互工具

---

*更多历史版本请查看 [CHANGELOG.md](https://github.com/vnpy/vnag/blob/main/CHANGELOG.md)*
