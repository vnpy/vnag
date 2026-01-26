# 核心组件

本章节详细介绍 VNAG 框架的核心组件，帮助您深入理解框架的设计和使用方法。

## 本章内容

```{toctree}
:maxdepth: 2

agent
gateway
tool
message
tracer
```

## 组件概览

VNAG 采用模块化的分层架构：

```
┌─────────────────────────────────────────────────────────────┐
│                       TaskAgent                              │
│                   (对话管理、工具编排)                         │
├─────────────────────────────────────────────────────────────┤
│                      AgentEngine                             │
│              (工具管理、Agent 工厂)                           │
├──────────────────────┬──────────────────────────────────────┤
│    LocalManager      │         McpManager                    │
│    (本地工具)         │         (MCP 工具)                    │
├──────────────────────┴──────────────────────────────────────┤
│                      BaseGateway                             │
│          (OpenAI / Anthropic / Dashscope / ...)             │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件说明

| 组件 | 模块 | 说明 |
|------|------|------|
| **TaskAgent** | `vnag.agent` | 任务型智能体，负责对话和工具调用 |
| **AgentEngine** | `vnag.engine` | 智能体引擎，管理工具和 Agent 生命周期 |
| **BaseGateway** | `vnag.gateway` | 网关基类，统一大模型 API 接口 |
| **LocalManager** | `vnag.local` | 本地工具管理器 |
| **McpManager** | `vnag.mcp` | MCP 工具管理器 |
| **LogTracer** | `vnag.tracer` | 执行追踪器，记录调试信息 |

## 数据对象

| 对象 | 模块 | 说明 |
|------|------|------|
| **Message** | `vnag.object` | 对话消息 |
| **Request** | `vnag.object` | LLM 请求 |
| **Response** | `vnag.object` | LLM 响应（阻塞式） |
| **Delta** | `vnag.object` | LLM 响应块（流式） |
| **Profile** | `vnag.object` | Agent 配置 |
| **Session** | `vnag.object` | 会话历史 |
| **ToolSchema** | `vnag.object` | 工具定义 |
| **ToolCall** | `vnag.object` | 工具调用请求 |
| **ToolResult** | `vnag.object` | 工具执行结果 |
| **Usage** | `vnag.object` | Token 用量统计 |
| **Segment** | `vnag.object` | 文档片段（用于 RAG） |

## 常量定义

```python
from vnag.constant import Role, FinishReason

# 消息角色
Role.SYSTEM      # 系统消息
Role.USER        # 用户消息
Role.ASSISTANT   # 助手消息

# 结束原因
FinishReason.STOP        # 正常结束
FinishReason.TOOL_CALLS  # 需要调用工具
FinishReason.LENGTH      # 达到长度限制
FinishReason.UNKNOWN     # 未知原因
FinishReason.ERROR       # 发生错误
```

## 下一步

选择您感兴趣的组件深入了解：

- [Agent 智能体](agent.md) - 核心智能体类
- [Gateway 网关](gateway.md) - 大模型 API 接口
- [Tool 工具系统](tool.md) - 本地和 MCP 工具
- [Message 消息](message.md) - 消息结构和格式
- [Tracer 追踪器](tracer.md) - 执行追踪和调试

