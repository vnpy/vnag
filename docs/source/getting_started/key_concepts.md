# 核心概念

本文档介绍 VNAG 的核心概念和设计理念，帮助您更好地理解和使用这个框架。

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         UI 层                                │
│                    (Chat UI / 自定义界面)                     │
├─────────────────────────────────────────────────────────────┤
│                       Agent 层                               │
│              (TaskAgent / AgentEngine)                       │
├─────────────────────────────────────────────────────────────┤
│                       Tool 层                                │
│           (LocalManager / McpManager)                        │
├─────────────────────────────────────────────────────────────┤
│                     Gateway 层                               │
│     (OpenAI / Anthropic / Dashscope / DeepSeek / ...)       │
└─────────────────────────────────────────────────────────────┘
```

## Agent（智能体）

Agent 是 VNAG 的核心概念，代表一个具有特定能力和行为的 AI 智能体。

### TaskAgent

`TaskAgent` 是标准的、可直接使用的任务型智能体。它具有以下特点：

- **对话管理**：自动维护对话历史
- **工具调用**：根据需要自动调用配置的工具
- **流式输出**：支持实时流式返回 AI 响应
- **会话持久化**：可选择保存会话到本地文件

```python
from vnag.agent import TaskAgent

# TaskAgent 通过 AgentEngine 创建
agent = engine.create_agent(profile, save=True)

# 流式对话
for delta in agent.stream("你好"):
    print(delta.content, end="")

# 阻塞式对话
response = agent.invoke("你好")
print(response.content)
```

### AgentTool

`AgentTool` 将一个 Agent 封装为可被其他 Agent 调用的工具，实现 Agent 之间的协作。

## Profile（配置）

Profile 定义了 Agent 的行为配置，是创建 Agent 的模板。

```python
from vnag.object import Profile

profile = Profile(
    name="代码助手",                    # 配置名称
    prompt="你是一个专业的代码助手...",   # 系统提示词
    tools=["code-tools_execute-code"],  # 可用工具列表
    temperature=0.7,                    # 生成温度
    max_tokens=4096,                    # 最大输出 token
    max_iterations=10                   # 最大工具调用轮次
)
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | str | 是 | 配置名称，用于标识和检索 |
| `prompt` | str | 是 | 系统提示词，定义 Agent 的角色和行为 |
| `tools` | list[str] | 是 | 工具名称列表，Agent 可以调用的工具（不需要工具时传 `[]`） |
| `temperature` | float | 否 | 生成温度，控制随机性（0-2） |
| `max_tokens` | int | 否 | 单次回复的最大 token 数 |
| `max_iterations` | int | 否 | 单次请求中最大的工具调用轮次（默认 10） |

## Session（会话）

Session 保存了一次完整的对话历史和状态。

```python
from vnag.object import Session

session = Session(
    id="20240101_120000_123456",    # 会话唯一标识
    profile="代码助手",              # 关联的 Profile 名称
    name="Python 问题解答",          # 会话名称
    model="gpt-4o",                  # 使用的模型
    messages=[]                      # 消息历史
)
```

## Message（消息）

Message 是对话中的单条消息，支持多种角色和内容类型。

```python
from vnag.object import Message
from vnag.constant import Role

# 用户消息
user_msg = Message(role=Role.USER, content="你好")

# 系统消息
system_msg = Message(role=Role.SYSTEM, content="你是一个助手")

# 助手消息（可能包含工具调用）
assistant_msg = Message(
    role=Role.ASSISTANT,
    content="让我查询一下...",
    tool_calls=[...]  # 工具调用请求
)
```

### 角色类型

| 角色 | 说明 |
|------|------|
| `Role.SYSTEM` | 系统消息，用于设置 Agent 的行为 |
| `Role.USER` | 用户消息 |
| `Role.ASSISTANT` | AI 助手的回复 |

## Gateway（网关）

Gateway 是与大模型 API 通信的抽象层，提供统一的接口。

### 支持的网关

| 网关 | 说明 |
|------|------|
| `OpenaiGateway` | OpenAI API（及兼容接口） |
| `AnthropicGateway` | Anthropic Claude API |
| `DashscopeGateway` | 阿里云 Dashscope API |
| `DeepseekGateway` | DeepSeek API（支持思维链） |
| `MinimaxGateway` | MiniMax API |
| `BailianGateway` | 阿里云百炼平台 |
| `OpenrouterGateway` | OpenRouter 多模型平台 |
| `LitellmGateway` | LiteLLM 网关代理服务 |

### 使用示例

```python
from vnag.gateways.openai_gateway import OpenaiGateway

gateway = OpenaiGateway()
gateway.init({
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1"
})

# 查询可用模型
models = gateway.list_models()
```

## Tool（工具）

工具赋予 Agent 与外部世界交互的能力。

### LocalTool（本地工具）

本地工具是 Python 函数的封装，可以快速将任意函数转换为 Agent 可调用的工具。

```python
from vnag.local import LocalTool

def get_weather(city: str) -> str:
    """获取指定城市的天气信息"""
    return f"{city}的天气是晴天，温度25°C"

weather_tool = LocalTool(get_weather)
engine.register_tool(weather_tool)
```

### MCP 工具

MCP（Model Context Protocol）工具通过远程服务器提供，支持更复杂的功能。

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

## Engine（引擎）

`AgentEngine` 是整个框架的核心引擎，负责：

- 管理 Gateway 连接
- 加载和管理工具
- 创建和管理 Agent 实例
- 协调工具调用

```python
from vnag.engine import AgentEngine

engine = AgentEngine(gateway)
engine.init()

# 获取所有工具
tools = engine.get_tool_schemas()

# 创建 Agent
agent = engine.create_agent(profile)

# 注册自定义工具
engine.register_tool(my_tool)
```

## 数据流程

一次典型的对话流程如下：

```
用户输入 → TaskAgent.stream()
            ↓
        构建 Request
            ↓
        Gateway.stream() → 大模型 API
            ↓
        收到 Delta 流式响应
            ↓
        是否需要工具调用？
            ↓ 是
        Engine.execute_tool()
            ↓
        将结果添加到消息
            ↓
        继续请求大模型
            ↓ 否
        返回最终响应
```

## 下一步

- [教程](../tutorial/index.md) - 通过实际示例深入学习
- [核心组件](../components/index.md) - 详细了解各个组件的使用方法

