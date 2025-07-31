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

## 技术架构约定

### 核心架构原则
- **window.py**: 纯UI层，只负责界面交互和状态收集，不包含业务逻辑
- **gateway.py**: 统一的AI服务入口，整合所有AI相关功能
- **服务类**: 作为gateway的内部组件，不对外直接暴露

### 组件职责划分
- **AgentGateway**: 核心业务层，整合所有AI相关功能，包括对话管理、RAG服务等
- **RAGService**: gateway内部组件，只负责消息预处理，不直接调用模型
- **DocumentService**: gateway内部组件，处理文档解析和分块
- **VectorService**: gateway内部组件，处理向量存储和检索
- **SessionManager**: gateway内部组件，管理对话会话和历史记录
- **TokenMonitor**: gateway内部组件，监控token使用量
- **window.py**: 纯UI展示层，只负责界面显示和用户交互，不包含任何业务逻辑

### 配置管理
```python
from .utility import get_file_path, load_json, save_json
config_path = get_file_path("rag_config.json")
```

### 日志记录
```python
import logging
logger = logging.getLogger(__name__)
```

### 组件规范
- 会话存储：TinyDB轻量级JSON数据库，文件放在.vnag目录下
- 向量存储：ChromaDB持久化存储，文件放在.vnag目录下
- 界面：继承PySide6==6.8.2.1，保持vnag简洁风格
- 服务：轻量级服务类，private方法用下划线前缀
- 配置：JSON格式，使用vnag的utility函数

## 项目结构

```
vnag/
├── vnag/
│   ├── __init__.py
│   ├── __main__.py            # 应用入口
│   ├── window.py              # 主界面（扩展RAG功能+会话管理）
│   ├── gateway.py             # AI网关（增强流式响应）
│   ├── utility.py             # 工具函数（扩展配置管理）
│   ├── setting.py             # 配置管理（新增）
│   ├── rag_service.py         # RAG核心服务（新增）
│   ├── document_service.py    # 文档处理服务（新增）
│   ├── vector_service.py      # 向量存储服务（新增）
│   ├── session_manager.py     # 会话管理服务（新增）
│   ├── token_monitor.py       # Token监控服务（新增）
│   └── logo.ico
├── docs/                      # 示例知识库（从rag_system复制）
├── vnag_prompt.md             # VNAG系统Prompt模板（新增）
├── pyproject.toml
├── README.md
├── CLAUDE.md                  # 本开发规范
└── LICENSE
```

## RAG功能扩展规范

### 文档格式支持
支持以下格式的文档导入和处理：
- **.md, .txt** - 纯文本格式
- **.pdf** - 使用pypdf库解析
- **.docx** - 使用python-docx库解析

### 服务类设计原则
1. **单一职责**: 每个服务类只负责一个核心功能
2. **轻量级**: 单个服务类代码量控制在200行以内
3. **类型安全**: 严格的类型注解，支持mypy检查
4. **错误处理**: 明确的异常类型和错误信息

### Gateway统一接口设计
```python
class AgentGateway:
    """核心业务层 - 完整的AI对话系统"""
    def __init__(self) -> None:
        # 内部组件，外部不直接访问
        self._rag_service: RAGService | None = None
        self._document_service: DocumentService | None = None
        self._vector_service: VectorService | None = None
        self._session_manager: SessionManager | None = None
        self._token_monitor: TokenMonitor | None = None
        
        # 对话状态（框架独立运行）
        self.chat_history: list[dict[str, str]] = []
    
    def init(self, base_url: str, api_key: str, model_name: str) -> None:
        """初始化连接和所有内部服务组件"""
        pass
    
    def send_message(self, message: str, use_rag: bool = True, user_files: list[str] | None = None) -> str | None:
        """发送消息并获取回复（框架核心接口）"""
        # 添加用户消息到历史
        # 调用模型获取回复
        # 添加助手回复到历史
        # 保存会话
        pass
        
    def get_chat_history(self) -> list[dict[str, str]]:
        """获取当前对话历史"""
        return self.chat_history
        
    def clear_history(self) -> None:
        """清空对话历史"""
        pass
    
    def invoke_model(self, messages: list[dict[str, str]], 
                    use_rag: bool = False, 
                    user_files: list[str] | None = None) -> str | None:
        """底层模型调用接口（供内部使用）"""
        pass
        
    def invoke_streaming(self, messages: list[dict[str, str]], 
                        use_rag: bool = False, 
                        user_files: list[str] | None = None) -> Generator[str, None, None] | None:
        """底层流式调用接口（供内部使用）"""
        pass

class SessionManager:
    """gateway内部组件，管理对话会话"""
    def save_session(self, chat_history: list[dict]) -> None:
        """保存会话到持久化存储"""
        pass
    
    def load_session(self, session_id: str = None) -> list[dict]:
        """加载会话历史"""
        pass
```

### 配置管理规范
```python
# .vnag/rag_config.json
{
    "llm": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-3.5-turbo",
        "max_tokens": 2000,
        "temperature": 0.7
    },
    "embedding": {
        "model_name": "BAAI/bge-large-zh-v1.5",
        "device": "cpu"
    },
    "vector_store": {
        "persist_directory": "chroma_db"
    },
    "document": {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "supported_formats": [".md", ".txt", ".pdf", ".docx"]
    }
}
```

## UI设计规范

### 界面扩展原则
1. **保持vnag风格**: 继续使用qdarkstyle主题 + 微软雅黑13号字体
2. **最小侵入**: 在现有布局基础上添加功能
3. **Cherry Studio体验**: 流畅的聊天交互体验
4. **用户友好**: 清晰的状态提示和进度反馈

### RAG工作模式
- **可选模式**: 通过Switch开关按钮控制RAG功能开启/关闭（默认开启）
- **RAG开启**: 知识库检索 + 用户文件 + RAG模板
- **RAG关闭**: 只处理用户文件，不检索知识库，不使用RAG模板
- **智能上下文**: 用户上传文件在两种模式下都会加入对话上下文
- **统一接口**: 所有模式都通过gateway统一调用，保持架构清晰

### 历史对话存储
使用TinyDB轻量级JSON数据库：
```python
# .vnag/chat_sessions.json - TinyDB数据库文件
{
  "sessions": [
    {
      "id": "uuid-string",
      "title": "会话标题", 
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00",
      "deleted": false
    }
  ],
  "messages": [
    {
      "session_id": "uuid-string",
      "role": "user|assistant",
      "content": "消息内容",
      "timestamp": "2024-01-01T00:00:00"
    }
  ]
}
```

## 已完成功能清单

### ✅ 基础架构扩展
- [x] 复制rag_system示例文档到vnag/docs/
- [x] 扩展utility.py配置管理
- [x] 增强gateway.py流式响应
- [x] 扩展window.py界面功能（RAG开关+文件选择+会话管理）
- [x] 添加依赖项到pyproject.toml（TinyDB替代Peewee）

### ✅ RAG核心功能实现
- [x] 实现RAGService核心服务（支持RAG/非RAG双模式）
- [x] 实现DocumentService文档处理（.md/.txt/.pdf/.docx）
- [x] 实现VectorService向量存储（ChromaDB + BGE）
- [x] 集成BGE嵌入模型（BAAI/bge-large-zh-v1.5）

### ✅ 完整系统功能
- [x] 会话管理TinyDB升级（替代JSON文件存储）
- [x] Token使用监控（80%预警机制）
- [x] RAG可选模式（Switch开关控制）
- [x] 用户文件上传和处理
- [x] 代码简化和优化

### 🔄 当前状态
vnag已实现完整的RAG功能，包含知识库问答、会话管理、文件处理等核心特性，达到生产级应用水平。

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
    "python-docx>=0.8.0", 
    "tinydb>=4.8.0",      # 轻量级JSON数据库
]
```

## 测试要求

### 单元测试
- 每个服务类需要对应的测试文件
- 测试覆盖率要求 > 80%
- 使用pytest框架

### 集成测试
- RAG完整流程测试
- UI交互测试
- 配置加载测试

## 核心特性

### RAG功能特色
- **智能模式切换**: Switch开关控制RAG开启/关闭
- **双重上下文**: 知识库检索 + 用户文件处理
- **自动知识库**: docs目录自动初始化，后台构建知识库
- **灵活文档支持**: .md/.txt/.pdf/.docx多格式支持

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

严格按照此规范开发，确保vnag-RAG版本的代码质量和用户体验一致性。