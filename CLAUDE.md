# VNAG 开发规范

## 项目背景

基于vnag框架扩展的RAG知识库问答系统：
- **技术栈**: ChromaDB + BGE-large-zh-v1.5 + PySide6==6.8.2.1 + OpenAI Compatible API + TinyDB
- **配置管理**: 使用vnag的.vnag目录体系
- **Python版本**: 3.10+
- **设计理念**: 保持vnag简洁优雅的架构风格

## 代码质量要求

- 符合flake8标准
- 能通过ruff和mypy检查
- 所有import放在文件顶部，不要在函数内import
- 类前必须有两个空行，函数间一个空行
- 避免不必要的try except捕获
- 不要有尾随空格
- 严格的类型注解要求
- 行太长的问题可以忽略

## 技术架构约定

### 核心架构原则
- **window.py**: 纯UI层，只负责界面交互和状态收集，不包含业务逻辑
- **gateway.py**: 统一的AI服务入口，整合所有AI相关功能
- **服务类**: 作为gateway的内部组件，不对外直接暴露

### 组件职责划分
- **AgentGateway**: 核心业务层，整合所有AI相关功能，包括对话管理、RAG服务、会话管理等
- **RAGService**: gateway 内部组件，负责 RAG 消息预处理（知识库检索 + 用户附件拼接）
- **DocumentService**: 处理文档解析与分块（知识库仅 .md；附件支持 .md/.txt/.pdf/.py）
- **VectorService**: RAGService内部组件，处理向量存储和检索（ChromaDB + BGE）
- **SessionManager**: gateway内部组件，管理对话会话和历史记录
- **window.py**: 纯UI展示层，只负责界面显示和用户交互，不包含任何业务逻辑

### 配置管理
使用统一的 gateway_setting.json 文件管理所有配置参数。

### 组件规范
- 会话存储：TinyDB轻量级JSON数据库，文件放在.vnag目录下
- 向量存储：ChromaDB持久化存储，文件放在.vnag目录下
- 界面：继承PySide6==6.8.2.1，保持vnag简洁风格
- 服务：轻量级服务类，private方法用下划线前缀
- 配置：JSON格式，使用vnag的utility组件

## 项目结构

```
vnag/
├── vnag/
│   ├── __init__.py
│   ├── __main__.py            # 应用入口
│   ├── window.py              # 纯UI展示层（最小化修改）
│   ├── gateway.py             # 核心业务层（完整AI对话系统）
│   ├── utility.py             # 工具函数
│   ├── setting.py             # 配置管理
│   ├── rag_service.py         # RAG消息预处理组件
│   ├── document_service.py    # 文档处理服务（支持md/txt/pdf/py）
│   ├── vector_service.py      # 向量存储服务（ChromaDB + BGE）
│   ├── session_manager.py     # 会话管理组件（TinyDB）
│   └── logo.ico
├── .vnag/docs/                # 知识库目录（仅 .md，用于向量化）
├── scripts/                   # 测试脚本与辅助脚本
│   ├── test_document_service.py
│   ├── test_vector_service.py
│   ├── test_rag_service.py
│   ├── test_session_manager.py
│   └── test_gateway.py
├── vnag_prompt.md             # VNAG系统Prompt模板
├── pyproject.toml
├── README.md
├── CLAUDE.md                  # 本开发规范
└── LICENSE
```

## RAG功能扩展规范

### 文档格式支持
- 知识库：仅 .md（.vnag/docs 目录，自动向量化）
- 用户文件：.md/.txt/.pdf/.py（直接加入上下文，不向量化）

### 文档处理优化
- **结构化分块**：Markdown 标题感知（# / ## / ###），代码块保护
- **长段控制**：段内按空行聚合，超过阈值定长切片（字符级，后续可升级 token 级）
- **元数据**：filename/source/file_type/chunk_index + section_title/section_order/section_part

### 向量检索增强
- **向量相似度**：ChromaDB + BGE 编码，余弦相似度
- **Top-K 检索**：基础 Top-K 检索（k=3，可配置）

### Prompt模板设计开发
- **系统角色定义**: 明确RAG助手身份和专业能力
- **回答要求规范**: 基于上下文、准确简洁、信息不足时明确说明
- **历史对话支持**: 包含最近对话历史，提升上下文理解
- **模板变量设计**: 支持{context}、{question}、{history}等变量替换
- **模板内嵌于代码**（template.py），支持 CHAT/RAG 两种模板

### 服务类设计原则
1. **单一职责**: 每个服务类只负责一个核心功能
2. **类型安全**: 严格的类型注解，支持mypy、ruff检查
3. **错误处理**: 明确的异常类型和错误信息

### Gateway统一接口设计
AgentGateway 类是系统的核心，提供统一的接口与大语言模型交互：

- **初始化**: 支持基本连接参数（base_url、api_key、model_name）
- **消息处理**: 支持普通消息和RAG增强消息
- **会话管理**: 支持创建、切换、删除会话
- **模型调用**: 流式响应
- **参数处理**: 可选参数如max_tokens和temperature只在有值时传递

### 配置管理规范
```python
# setting.py 中的默认 SETTINGS（MVP）
SETTINGS: dict = {
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "",
    "model_name": "anthropic/claude-3.7-sonnet",
    "max_tokens": 2000,
    "temperature": 0.7
}

# gateway_setting.json 示例
{
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "your_api_key",
    "model_name": "anthropic/claude-3.7-sonnet",
    "max_tokens": 2000,
    "temperature": 0.7
}
```

## UI设计规范

### 界面扩展原则
1. **保持vnag风格**: 继续使用qdarkstyle主题 + 微软雅黑13号字体
2. **最小侵入**: 在现有布局基础上添加功能
3. **Cherry Studio体验**: 流畅的聊天交互体验
4. **用户友好**: 清晰的状态提示和进度反馈

### 界面布局
- **左侧面板**: 分为"会话"和"配置"两个标签页
- **右侧面板**: 聊天显示区域和输入区域
- **RAG开关按钮**: 显示"RAG ON"/"RAG OFF"文本

### UI增强功能
- **流式显示**: 支持回答内容的实时追加显示

### RAG工作模式
- **可选模式**: 通过Switch开关按钮控制RAG功能开启/关闭（默认开启）
- **RAG开启**: 知识库检索（docs/*.md文件） + 用户文件 + RAG模板
- **RAG关闭**: 只处理用户文件，不检索知识库，不使用RAG模板
- **智能上下文**: 用户上传文件直接加入对话上下文（不做向量化处理）
- **统一接口**: 所有模式都通过gateway统一调用
- **LLM选择**: 支持查询OpenAI API获取可用模型列表

### 历史对话存储
使用TinyDB轻量级JSON数据库存储会话历史记录，支持会话的创建、切换和删除操作。会话数据包含基本会话信息和消息内容，通过会话ID关联。

### 会话管理增强
- **自动标题**: 取用户首次提问的前20个字符作为默认标题
- **会话软删除**: 标记deleted字段而非物理删除
- **会话导出**: 支持JSON和Markdown格式导出


## 错误处理与稳定性

### 输入验证
- 输入验证：内容非空、长度合理（UI 端校验）

### API异常处理
- **异常处理**：统一捕获为用户友好文本并在 UI 显示；不做自动重试


## 开发路线

### 第一阶段（MVP核心功能）
- 基础RAG问答 + 聊天界面 + 多格式文档支持
- 文档处理：Markdown 结构化分块、代码块保护、长段定长切片
- 向量检索：ChromaDB + BGE，Top-K 基础检索
- 配置管理 + 会话管理 + 流式响应
- 单元测试：pytest，脚本位于 scripts/

### 第二阶段（完整产品）
- 语义切分优化（token 级、BM25 混合检索）
- 使用RecursiveCharacterTextSplitter，按优先级尝试不同分隔符
- 将ChromaDB距离值转换为相似度分数，提供百分比显示和检索排名信息
- 敏感内容检测和安全过滤
- 界面优化
- 模板外部化与可配置化
- 多层验证（UI端与服务端参数校验）
- 基础分类异常处理与友好提示

### 第三阶段（高级特性）
- 质量评估（多维度评估检索结果质量）+ 指代词处理 + 多Agent协作架构 + 实时交互能力
- 多轮对话检索
- 知识库md文件中的图片内容支持
- 代码高亮主题切换 + 设备自动检测
- UI交互优化（流式显示优化、代码块悬浮按钮、参考quivr设计）
- 智能排序兼容（在相似度基础上多信号加权，保留相似度百分比显示，可选 MMR 重排）
- 智能重试机制（指数退避 + 抖动，仅针对网络类可重试错误）

## 兼容性要求

### 向后兼容
- 现有vnag功能完全保留
- 原有配置文件继续有效
- 现有用户界面布局不变

### 版本固定
```toml
dependencies = [
    "PySide6==6.8.2.1",  # 固定版本，避免兼容性问题
    "openai", 
    "markdown",
    "qdarkstyle",
    "chromadb>=0.4.0",
    "sentence-transformers>=2.2.0",
    "pypdf>=3.0.0",
    "tinydb>=4.8.0",      # 轻量级JSON数据库
]
```

## 测试要求

### 单元测试
- 每个服务类对应测试文件（位于 scripts/）
- 使用 pytest 框架

### 集成测试
- RAG完整流程测试
- UI交互测试
- 配置加载测试

## 核心特性

### RAG功能特色
- **智能模式切换**: Switch开关控制RAG开启/关闭
- **双重上下文**: 知识库检索 + 用户文件处理
- **自动知识库**: docs目录自动初始化，后台构建知识库
- **智能文档处理**: Markdown结构感知分块、代码块保护

### 会话管理特色  
- **轻量级存储**: TinyDB替代重型数据库
- **完整会话历史**: 支持会话切换、删除、管理
- **简洁界面**: 最小化侵入的会话列表管理

## 注意事项

- 严格遵循vnag的简洁设计哲学
- PySide6版本必须固定为6.8.2.1
- 避免不必要的try except捕获
- 所有新功能都应该透明运行
- 保持与原有vnag用户体验的一致性
- 代码修改要最小化，优先扩展而非重构
- 错误处理要友好且明确
- 知识库构建对用户不可见，自动后台处理
- 智能分块功能必须在文档中明确说明Markdown格式要求

严格按照此规范开发，确保vnag-RAG版本的代码质量和用户体验一致性。
