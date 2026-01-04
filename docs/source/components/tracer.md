# Tracer 追踪器

追踪器用于记录 Agent 的执行过程，帮助调试和分析。

## LogTracer

`LogTracer` 是默认的追踪器实现，将执行日志写入文件。

### 基本使用

```python
from vnag.tracer import LogTracer

tracer = LogTracer(
    session_id="session_123",
    profile_name="我的助手"
)
```

LogTracer 会自动被 TaskAgent 使用，无需手动创建。

### 日志文件

日志保存在运行目录的 `.vnag/log/` 目录下，并且**按会话分文件**：

- `.vnag/log/{session_id}.log`

### 日志格式

```
2024-01-15 10:30:00.123 | INFO     | 我的助手 | LLM -> 请求已发送 (模型: gpt-4o)
2024-01-15 10:30:01.456 | INFO     | 我的助手 | LLM <- 响应已接收
2024-01-15 10:30:01.789 | INFO     | 我的助手 | 工具 -> 开始执行: datetime-tools_current-time
2024-01-15 10:30:01.999 | INFO     | 我的助手 | 工具 <- 执行完毕: datetime-tools_current-time
```

## 追踪事件

追踪器记录以下事件：

### on_llm_start

LLM 请求开始时触发：

```python
def on_llm_start(self, request: Request) -> None:
    # 记录请求信息
    # - 模型名称
    # - 消息数量
    # - 工具数量
```

### on_llm_delta

收到流式响应块时触发：

```python
def on_llm_delta(self, delta: Delta) -> None:
    # 记录响应片段
    # - 内容片段
    # - 思考片段
    # - 工具调用
```

### on_llm_end

LLM 响应结束时触发：

```python
def on_llm_end(self, message: Message) -> None:
    # 记录完整响应
    # - 完整内容
    # - 思考过程
    # - 工具调用请求
```

### on_tool_start

工具执行开始时触发：

```python
def on_tool_start(self, tool_call: ToolCall) -> None:
    # 记录工具调用
    # - 工具名称
    # - 调用参数
```

### on_tool_end

工具执行结束时触发：

```python
def on_tool_end(self, result: ToolResult) -> None:
    # 记录执行结果
    # - 工具名称
    # - 执行结果
```

## 自定义追踪器

您可以创建自定义追踪器来满足特定需求：

```python
from vnag.object import Request, Delta, Message, ToolCall, ToolResult


class CustomTracer:
    """自定义追踪器"""
    
    def __init__(self, session_id: str, profile_name: str):
        self.session_id = session_id
        self.profile_name = profile_name
        self.events = []
    
    def on_llm_start(self, request: Request) -> None:
        self.events.append({
            "type": "llm_start",
            "model": request.model,
            "message_count": len(request.messages)
        })
    
    def on_llm_delta(self, delta: Delta) -> None:
        if delta.content:
            self.events.append({
                "type": "llm_delta",
                "content": delta.content
            })
    
    def on_llm_end(self, message: Message) -> None:
        self.events.append({
            "type": "llm_end",
            "content": message.content,
            "tool_calls": len(message.tool_calls)
        })
    
    def on_tool_start(self, tool_call: ToolCall) -> None:
        self.events.append({
            "type": "tool_start",
            "name": tool_call.name,
            "arguments": tool_call.arguments
        })
    
    def on_tool_end(self, result: ToolResult) -> None:
        self.events.append({
            "type": "tool_end",
            "name": result.name,
            "content": result.content
        })
    
    def get_summary(self) -> dict:
        """获取执行摘要"""
        return {
            "session_id": self.session_id,
            "total_events": len(self.events),
            "llm_calls": len([e for e in self.events if e["type"] == "llm_end"]),
            "tool_calls": len([e for e in self.events if e["type"] == "tool_end"])
        }
```

## 使用场景

### 1. 调试 Agent 行为

通过追踪日志了解：
- Agent 如何处理请求
- 工具调用的顺序和参数
- 每次 LLM 调用的内容

### 2. 性能分析

记录时间戳来分析：
- LLM 响应时间
- 工具执行时间
- 端到端延迟

### 3. 日志审计

保存完整的执行记录用于：
- 问题排查
- 行为分析
- 合规审计

## 查看追踪日志

### 通过文件

直接打开对应会话的日志文件，例如：`.vnag/log/20240115_103000_123456.log`。

### 通过代码

```python
# 读取日志文件
with open(".vnag/log/20240115_103000_123456.log", "r", encoding="utf-8") as f:
    logs = f.read()
    print(logs)
```

## 下一步

- [API 参考](../api/index.rst) - 查看完整 API
- [高级用法](../advanced/index.md) - 更多高级功能

