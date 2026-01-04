# Message 消息

Message 是对话系统中的基本单元，表示一条消息。

## Message 结构

```python
from vnag.object import Message
from vnag.constant import Role

message = Message(
    role=Role.USER,                    # 消息角色
    content="你好",                     # 文本内容
    thinking="",                       # 思考过程
    reasoning=[],                      # 推理数据
    tool_calls=[],                     # 工具调用请求
    tool_results=[]                    # 工具执行结果
)
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `role` | Role | 消息角色 |
| `content` | str | 文本内容 |
| `thinking` | str | 模型思考过程 |
| `reasoning` | list[dict] | 推理数据（特定模型） |
| `tool_calls` | list[ToolCall] | 工具调用请求 |
| `tool_results` | list[ToolResult] | 工具执行结果 |

## 消息角色

```python
from vnag.constant import Role

Role.SYSTEM      # 系统消息
Role.USER        # 用户消息
Role.ASSISTANT   # 助手消息
```

### 系统消息

系统消息用于设置 Agent 的行为和角色：

```python
system_msg = Message(
    role=Role.SYSTEM,
    content="""你是一个专业的编程助手。

规则：
1. 回答要简洁明了
2. 提供代码示例时要加注释
3. 遇到不确定的问题要说明
"""
)
```

### 用户消息

用户消息表示用户的输入：

```python
# 普通文本消息
user_msg = Message(
    role=Role.USER,
    content="请帮我写一个冒泡排序"
)

# 带工具结果的消息
user_msg = Message(
    role=Role.USER,
    tool_results=[
        ToolResult(
            id="call_123",
            name="get_time",
            content="14:30:00"
        )
    ]
)
```

### 助手消息

助手消息表示 AI 的回复：

```python
# 普通回复
assistant_msg = Message(
    role=Role.ASSISTANT,
    content="这是一个冒泡排序的实现..."
)

# 带思考过程的回复
assistant_msg = Message(
    role=Role.ASSISTANT,
    thinking="用户需要冒泡排序，我来分析一下...",
    content="冒泡排序是一种简单的排序算法..."
)

# 带工具调用的回复
assistant_msg = Message(
    role=Role.ASSISTANT,
    content="让我查询一下当前时间",
    tool_calls=[
        ToolCall(
            id="call_123",
            name="datetime-tools_current-time",
            arguments={}
        )
    ]
)
```

## 工具调用消息

当 Agent 需要调用工具时，会生成带有 `tool_calls` 的助手消息：

```python
# 助手请求调用工具
assistant_msg = Message(
    role=Role.ASSISTANT,
    content="我需要查询天气信息",
    tool_calls=[
        ToolCall(
            id="call_abc",
            name="get_weather",
            arguments={"city": "北京"}
        )
    ]
)

# 用户返回工具结果
user_msg = Message(
    role=Role.USER,
    tool_results=[
        ToolResult(
            id="call_abc",
            name="get_weather",
            content="北京：晴，25°C"
        )
    ]
)
```

## 思考过程

部分模型支持返回思考过程：

```python
# DeepSeek 等模型的思考过程
message = Message(
    role=Role.ASSISTANT,
    thinking="让我分析一下这个问题...\n1. 首先需要理解需求\n2. 然后设计方案...",
    content="根据您的需求，建议..."
)

# 访问思考内容
if message.thinking:
    print(f"思考过程：{message.thinking}")
```

## 推理数据

某些模型返回结构化的推理数据：

```python
# MiniMax 等模型的推理数据
message = Message(
    role=Role.ASSISTANT,
    reasoning=[
        {"type": "step", "content": "分析问题"},
        {"type": "step", "content": "设计方案"},
        {"type": "conclusion", "content": "最终结论"}
    ],
    content="最终答案..."
)
```

## 序列化

Message 支持 Pydantic 的序列化方法：

```python
# 转换为字典
data = message.model_dump()

# 从字典创建
message = Message.model_validate(data)

# 转换为 JSON
json_str = message.model_dump_json()
```

## 对话历史

在 Agent 中，消息历史保存在 Session 中：

```python
# 获取对话历史
messages = agent.messages

# 遍历消息
for msg in messages:
    print(f"[{msg.role.value}] {msg.content[:50]}...")

# 获取最后一条消息
last_msg = messages[-1] if messages else None
```

## 消息构建示例

### 构建完整对话

```python
messages = [
    # 系统消息
    Message(
        role=Role.SYSTEM,
        content="你是一个天气助手"
    ),
    
    # 用户第一次提问
    Message(
        role=Role.USER,
        content="北京天气怎么样？"
    ),
    
    # 助手请求调用工具
    Message(
        role=Role.ASSISTANT,
        content="让我查询北京的天气",
        tool_calls=[
            ToolCall(id="1", name="get_weather", arguments={"city": "北京"})
        ]
    ),
    
    # 工具返回结果
    Message(
        role=Role.USER,
        tool_results=[
            ToolResult(id="1", name="get_weather", content="晴，25°C")
        ]
    ),
    
    # 助手最终回复
    Message(
        role=Role.ASSISTANT,
        content="北京今天天气晴朗，温度25°C，适合外出。"
    )
]
```

## 下一步

- [Tracer 追踪器](tracer.md) - 了解执行追踪
- [API 参考](../api/index.rst) - 查看完整 API

