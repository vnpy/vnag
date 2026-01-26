# Agent 智能体

Agent 是 VNAG 的核心概念，代表一个具有特定能力和行为的 AI 智能体。

## TaskAgent

`TaskAgent` 是标准的任务型智能体，提供完整的对话和工具调用能力。

### 创建 Agent

```python
from vnag.engine import AgentEngine
from vnag.object import Profile

# 通过引擎创建 Agent
agent = engine.create_agent(profile, save=True)
```

参数说明：
- `profile`: Agent 配置对象
- `save`: 是否保存会话到本地文件

### 属性

```python
# 会话 ID
agent.id

# 会话名称
agent.name

# 使用的模型
agent.model

# 消息历史
agent.messages

# 关联的配置
agent.profile

# 关联的引擎
agent.engine
```

### 对话方法

#### stream() - 流式对话

```python
for delta in agent.stream("你好"):
    # delta.id - 响应 ID
    # delta.content - 文本内容
    # delta.thinking - 思考过程（如果有）
    # delta.calls - 工具调用请求
    # delta.finish_reason - 结束原因
    # delta.usage - Token 使用量
    
    if delta.content:
        print(delta.content, end="", flush=True)
```

#### invoke() - 阻塞式对话

```python
response = agent.invoke("你好")

print(response.id)       # 响应 ID
print(response.content)  # 完整内容
print(response.usage)    # Token 使用量
```

### 会话管理

```python
# 重命名会话
agent.rename("新名称")

# 设置模型
agent.set_model("gpt-4o")

# 删除最后一轮对话
agent.delete_round()

# 重新发送最后一轮（返回用户输入）
prompt = agent.resend_round()

# 生成会话标题
title = agent.generate_title(max_length=20)
```

### 中止流式生成

```python
# 在流式生成过程中中止
agent.abort_stream()
```

这会保存已生成的部分内容到会话历史。

## AgentTool

`AgentTool` 将一个 Agent 封装为可被其他 Agent 调用的工具。

### 创建 AgentTool

```python
from vnag.agent import AgentTool

# 创建专门的 Profile
expert_profile = Profile(
    name="代码专家",
    prompt="你是一个代码专家...",
    tools=["code-tools_execute-code"]
)

# 封装为工具
expert_tool = AgentTool(
    engine=engine,
    profile=expert_profile,
    model="gpt-4o",
    name="code-expert",           # 可选：自定义工具名
    description="调用代码专家分析代码"  # 可选：自定义描述
)

# 注册到引擎
engine.register_tool(expert_tool)
```

### 使用场景

AgentTool 适用于：
- **多 Agent 协作**：让一个 Agent 调用另一个专门的 Agent
- **能力组合**：将不同能力的 Agent 组合使用
- **任务分解**：复杂任务分解给多个专门的 Agent

```python
# 主 Agent 可以调用代码专家
main_profile = Profile(
    name="主助手",
    prompt="你是一个通用助手，可以调用代码专家帮助分析代码。",
    tools=["agent_code-expert"]  # 使用 agent_ 前缀
)

main_agent = engine.create_agent(main_profile)
```

## AgentEngine

`AgentEngine` 是智能体引擎，负责管理 Agent 的生命周期和工具系统。

### 初始化

```python
from vnag.engine import AgentEngine

engine = AgentEngine(gateway)
engine.init()
```

### Profile 管理

```python
# 添加配置
engine.add_profile(profile)

# 更新配置
engine.update_profile(profile)

# 获取配置
profile = engine.get_profile("名称")

# 获取所有配置
profiles = engine.get_all_profiles()

# 删除配置
engine.delete_profile("名称")
```

### Agent 管理

```python
# 创建 Agent
agent = engine.create_agent(profile, save=True)

# 获取 Agent
agent = engine.get_agent(session_id)

# 获取所有 Agent
agents = engine.get_all_agents()

# 删除 Agent
engine.delete_agent(session_id)
```

### 工具管理

```python
# 注册工具
engine.register_tool(my_tool)

# 获取工具 Schema
all_schemas = engine.get_tool_schemas()
filtered_schemas = engine.get_tool_schemas(["tool1", "tool2"])

# 获取本地工具
local_schemas = engine.get_local_schemas()

# 获取 MCP 工具
mcp_schemas = engine.get_mcp_schemas()

# 查询可用模型
models = engine.list_models()
```

### 工具执行

```python
from vnag.object import ToolCall

# 执行工具
tool_call = ToolCall(
    id="call_123",
    name="datetime-tools_current-date",
    arguments={}
)
result = engine.execute_tool(tool_call)
```

### 流式请求

```python
from vnag.object import Request

request = Request(
    model="gpt-4o",
    messages=messages,
    tool_schemas=schemas
)

for delta in engine.stream(request):
    print(delta.content, end="")
```

## Profile 配置

Profile 定义了 Agent 的行为特征。

```python
from vnag.object import Profile

profile = Profile(
    name="助手名称",           # 必填
    prompt="系统提示词",        # 必填
    tools=["tool1", "tool2"], # 可用工具
    temperature=0.7,          # 生成温度
    max_tokens=4096,          # 最大输出
    max_iterations=10         # 最大工具调用轮次
)
```

### 字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | 必填 | 配置名称 |
| `prompt` | str | 必填 | 系统提示词 |
| `tools` | list[str] | 必填 | 可用工具名称列表（可传空列表 `[]`） |
| `temperature` | float | None | 生成温度 (0-2) |
| `max_tokens` | int | None | 最大输出 token |
| `max_iterations` | int | 10 | 最大工具调用轮次 |

## Session 会话

Session 保存了完整的对话历史。

```python
from vnag.object import Session

session = Session(
    id="session_id",
    profile="配置名称",
    name="会话名称",
    model="gpt-4o",
    messages=[]
)
```

Session 会自动保存到 `.vnag/session/` 目录。

## 下一步

- [Gateway 网关](gateway.md) - 了解大模型 API 接口
- [Tool 工具系统](tool.md) - 了解工具系统

