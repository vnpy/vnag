# 配置指南

VNAG 采用统一的配置文件管理机制，所有配置文件都存放在 `.vnag` 目录中。

## 配置目录

### 加载逻辑

1. **优先加载当前目录**：程序启动时，首先检查当前工作路径下是否存在 `.vnag` 目录
2. **备选用户主目录**：如果当前目录没有 `.vnag`，则使用用户主目录下的 `.vnag`

这种设计允许您：
- 为不同项目设置独立的本地配置
- 或配置一个全局共享的配置

### 目录结构

```
.vnag/
├── connect_openai.json      # OpenAI 网关配置
├── connect_anthropic.json   # Anthropic 网关配置
├── connect_dashscope.json   # Dashscope 网关配置
├── connect_deepseek.json    # DeepSeek 网关配置
├── connect_minimax.json     # MiniMax 网关配置
├── connect_bailian.json     # 百炼网关配置
├── connect_openrouter.json  # OpenRouter 网关配置
├── mcp_config.json          # MCP 工具配置
├── tool_filesystem.json    # 文件系统工具权限
├── profile/                 # Profile 配置目录
│   ├── 助手.json
│   └── 代码专家.json
├── session/                 # 会话历史目录
│   ├── 20240115_103000_123456.json
│   └── ...
├── log/                     # 追踪日志（按会话分文件）
│   ├── 20240115_103000_123456.log
│   └── ...
├── chroma_db/               # ChromaDB 数据（如果使用 ChromaVector）
├── qdrant_db/               # Qdrant 数据（如果使用 QdrantVector）
└── ui_setting.json          # UI 配置（如当前选择的网关类型、常用模型等）
```

## 网关配置

### OpenAI

**文件**：`.vnag/connect_openai.json`

```json
{
    "api_key": "sk-YourOpenAIKey",
    "base_url": "https://api.openai.com/v1"
}
```

适用于 OpenAI 官方 API 及所有兼容接口。

### Anthropic

**文件**：`.vnag/connect_anthropic.json`

```json
{
    "api_key": "sk-ant-YourAnthropicKey",
    "base_url": "https://api.anthropic.com"
}
```

### Dashscope

**文件**：`.vnag/connect_dashscope.json`

```json
{
    "api_key": "sk-YourDashscopeKey"
}
```

### DeepSeek

**文件**：`.vnag/connect_deepseek.json`

```json
{
    "api_key": "sk-YourDeepSeekKey",
    "base_url": "https://api.deepseek.com"
}
```

### MiniMax

**文件**：`.vnag/connect_minimax.json`

```json
{
    "api_key": "YourMinimaxKey",
    "base_url": "https://api.minimaxi.com/v1"
}
```

### 阿里云百炼

**文件**：`.vnag/connect_bailian.json`

```json
{
    "api_key": "sk-YourBailianKey",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
}
```

### OpenRouter

**文件**：`.vnag/connect_openrouter.json`

```json
{
    "api_key": "sk-YourOpenRouterKey",
    "base_url": "https://openrouter.ai/api/v1",
    "reasoning_effort": "medium"
}
```

| 字段 | 说明 |
|------|------|
| `reasoning_effort` | 推理强度：`low`、`medium`、`high` |

## MCP 配置

**文件**：`.vnag/mcp_config.json`

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
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your-brave-api-key"
      }
    }
  }
}
```

### 配置说明

| 字段 | 说明 |
|------|------|
| `mcpServers` | MCP 服务器配置字典 |
| 服务器名称 | 自定义的服务器标识 |
| `command` | 启动命令 |
| `args` | 命令参数 |
| `env` | 环境变量（可选） |

### 常用 MCP 服务器

| 服务器 | 包名 | 说明 |
|--------|------|------|
| 文件系统 | `@modelcontextprotocol/server-filesystem` | 文件读写操作 |
| 顺序思考 | `@modelcontextprotocol/server-sequential-thinking` | 结构化思考 |
| Brave 搜索 | `@modelcontextprotocol/server-brave-search` | 网络搜索 |
| SQLite | `@modelcontextprotocol/server-sqlite` | 数据库操作 |

## 文件系统工具权限

**文件**：`.vnag/tool_filesystem.json`

```json
{
    "read_allowed": [
        "/home/user/documents",
        "/home/user/projects",
        "D:\\Projects"
    ],
    "write_allowed": [
        "/home/user/projects/output",
        "D:\\Projects\\output"
    ]
}
```

| 字段 | 说明 |
|------|------|
| `read_allowed` | 允许读取的目录列表 |
| `write_allowed` | 允许写入的目录列表 |

:::{warning}
出于安全考虑，文件系统工具只能访问配置中明确允许的路径。
:::

## Profile 配置

Profile 配置保存在 `.vnag/profile/` 目录下。

**示例**：`.vnag/profile/代码助手.json`

```json
{
    "name": "代码助手",
    "prompt": "你是一个专业的编程助手...",
    "tools": [
        "code-tools_execute-code",
        "file-tools_read-file"
    ],
    "temperature": 0.5,
    "max_tokens": 4096,
    "max_iterations": 10
}
```

## Session 配置

会话历史保存在 `.vnag/session/` 目录下。

**示例**：`.vnag/session/20240115_103000_123456.json`

```json
{
    "id": "20240115_103000_123456",
    "profile": "代码助手",
    "name": "Python 问题解答",
    "model": "gpt-4o",
    "messages": [
        {
            "role": "system",
            "content": "你是一个专业的编程助手..."
        },
        {
            "role": "user",
            "content": "如何使用列表推导式？"
        },
        {
            "role": "assistant",
            "content": "列表推导式是..."
        }
    ]
}
```

## UI 配置

**文件**：`.vnag/ui_setting.json`

此文件由 Chat UI 自动生成和管理，存储用户的界面偏好设置：

```json
{
    "gateway_type": "OpenAI",
    "favorite_models": ["gpt-4o", "gpt-4o-mini"],
    "zoom_factor": 1.0,
    "font_family": "微软雅黑",
    "font_size": 16
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `gateway_type` | str | 当前选择的网关类型（如 OpenAI、DeepSeek 等） |
| `favorite_models` | list[str] | 常用模型列表，会优先显示在模型下拉框中 |
| `zoom_factor` | float | 页面缩放倍数，默认 1.0 |
| `font_family` | str | 字体名称，默认"微软雅黑" |
| `font_size` | int | 字体大小，默认 16 |

:::{note}
此文件通常无需手动编辑，可通过 UI 界面进行设置。
:::

## 自定义工具

将 Python 工具文件放在**当前工作目录**的 `tools/` 目录下，会自动加载（用户自定义工具）。

:::{warning}
注意：自定义工具目录是 `{工作目录}/tools/`，**不是** `.vnag/tools/`。
:::

**示例**：`tools/my_tools.py`

```python
from vnag.local import LocalTool


def my_function(param: str) -> str:
    """我的自定义工具"""
    return f"处理结果: {param}"


# 必须是 LocalTool 实例才会被加载
my_tool = LocalTool(my_function)
```

## 环境变量

当前版本建议使用 `.vnag/connect_*.json` 或 UI 中的“AI服务配置”完成网关配置。

## 配置最佳实践

### 1. 项目级配置

为每个项目创建独立的 `.vnag` 目录：

```bash
cd my_project
mkdir .vnag
# 在此目录下添加配置文件
```

### 2. 敏感信息保护

将 `.vnag` 添加到 `.gitignore`：

```text
.vnag/
```

### 3. 配置模板

创建配置模板供团队使用：

```bash
.vnag.template/
├── connect_openai.json.example
├── mcp_config.json.example
└── tool_filesystem.json.example
```

## 下一步

- [高级用法](../advanced/index.md) - 更多高级功能
- [FAQ](../faq.md) - 常见问题解答

