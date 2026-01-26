# 思维链集成

部分大模型支持输出思考过程（Thinking/Reasoning），本文介绍如何在 VNAG 中使用这一特性。

## 什么是思维链

思维链（Chain of Thought）是模型在回答问题前的内部推理过程。支持思维链的模型会在最终回答之前展示其思考步骤。

```
用户: 1+2+3+...+100 等于多少？

思考过程:
这是一个等差数列求和问题。
使用高斯公式：S = n(a1 + an) / 2
其中 n=100, a1=1, an=100
S = 100 × (1 + 100) / 2 = 100 × 101 / 2 = 5050

回答: 1到100的和等于5050。
```

## 支持的网关

以下网关支持思维链输出：

| 网关 | 字段 | 说明 |
|------|------|------|
| DeepseekGateway | `thinking` | DeepSeek 思维链 |
| MinimaxGateway | `reasoning` | MiniMax 交错思维 |
| BailianGateway | `thinking` | 百炼 Qwen3/QwQ 深度思考 |
| OpenrouterGateway | `thinking` / `reasoning` | 取决于具体模型 |

## 使用思维链

### 流式输出

```python
from vnag.gateways.deepseek_gateway import DeepseekGateway
from vnag.object import Request, Message
from vnag.constant import Role

# 初始化 DeepSeek 网关
gateway = DeepseekGateway()
gateway.init({
    "api_key": "your-api-key",
    "base_url": "https://api.deepseek.com"
})

# 构建请求
request = Request(
    model="deepseek-reasoner",
    messages=[
        Message(role=Role.USER, content="解释相对论的核心概念")
    ]
)

# 流式获取响应
print("思考过程：")
for delta in gateway.stream(request):
    if delta.thinking:
        print(delta.thinking, end="", flush=True)
    
print("\n\n回答：")
for delta in gateway.stream(request):
    if delta.content:
        print(delta.content, end="", flush=True)
```

### 在 TaskAgent 中使用

```python
from vnag.gateways.deepseek_gateway import DeepseekGateway
from vnag.engine import AgentEngine
from vnag.object import Profile

# 初始化
gateway = DeepseekGateway()
gateway.init({"api_key": "your-api-key"})

engine = AgentEngine(gateway)
engine.init()

# 创建 Agent
profile = Profile(
    name="推理助手",
    prompt="你是一个善于推理的助手。",
    tools=[]
)

agent = engine.create_agent(profile)
agent.set_model("deepseek-reasoner")

# 对话并显示思考过程
thinking_content = ""
response_content = ""

for delta in agent.stream("如何证明根号2是无理数？"):
    if delta.thinking:
        thinking_content += delta.thinking
        print(f"[思考] {delta.thinking}", end="", flush=True)
    if delta.content:
        response_content += delta.content
        print(delta.content, end="", flush=True)

print("\n")
print(f"完整思考过程：{thinking_content}")
print(f"最终回答：{response_content}")
```

## Message 中的思维链

思考过程会保存在 Message 的 `thinking` 和 `reasoning` 字段中：

```python
# 获取消息历史
for message in agent.messages:
    if message.role == Role.ASSISTANT:
        if message.thinking:
            print(f"思考：{message.thinking}")
        if message.reasoning:
            print(f"推理：{message.reasoning}")
        print(f"回答：{message.content}")
```

## Delta 结构

流式响应中的思维链字段：

```python
class Delta(BaseModel):
    id: str
    content: str | None = None      # 回答内容
    thinking: str | None = None     # 思考过程（字符串）
    reasoning: list[dict] = []      # 推理数据（结构化）
    ...
```

### thinking vs reasoning

- **thinking**：纯文本的思考过程，用于 DeepSeek、百炼等
- **reasoning**：结构化的推理数据，用于 MiniMax 等

```python
# MiniMax 的 reasoning 格式示例
reasoning = [
    {"type": "step", "index": 0, "text": "分析问题..."},
    {"type": "step", "index": 1, "text": "推导公式..."},
    {"type": "conclusion", "index": 2, "text": "得出结论..."}
]
```

## UI 中的思维链显示

Chat UI 会自动显示思考过程：

- 思考内容以折叠形式显示
- 点击可展开查看完整思考过程
- 历史消息也会保留思考内容

## 最佳实践

### 1. 选择合适的模型

不是所有模型都支持思维链，选择专门的推理模型：

- DeepSeek Reasoner
- Qwen3 / QwQ
- Claude 3.5 Sonnet（通过 OpenRouter）

### 2. 优化提示词

对于需要推理的任务，可以在提示词中引导：

```python
profile = Profile(
    name="数学助手",
    prompt="""你是一个数学专家。

回答问题时：
1. 先分析问题的关键点
2. 列出解题思路
3. 逐步推导
4. 给出最终答案
""",
    tools=[]
)
```

### 3. 利用思考过程

思考过程可以用于：

- 调试 Agent 行为
- 理解 AI 的决策逻辑
- 作为解释提供给用户

```python
# 记录思考过程用于分析
with open("thinking_log.txt", "a") as f:
    f.write(f"问题：{question}\n")
    f.write(f"思考：{thinking_content}\n")
    f.write(f"回答：{response_content}\n\n")
```

### 4. 处理长思考过程

某些问题可能产生很长的思考过程：

```python
# 限制显示的思考长度
max_thinking_display = 500

if len(thinking_content) > max_thinking_display:
    display_thinking = thinking_content[:max_thinking_display] + "..."
else:
    display_thinking = thinking_content
```

## 自定义网关中的思维链

如果您要自定义网关并支持思维链，需要在 Delta 中设置 `thinking` 字段：

```python
def stream(self, request: Request):
    for chunk in api_response:
        # 解析思考内容
        thinking = chunk.get("reasoning_content", "")
        content = chunk.get("content", "")
        
        yield Delta(
            id=response_id,
            content=content if content else None,
            thinking=thinking if thinking else None,
            ...
        )
```

## 下一步

- [API 参考](../api/index.rst) - 查看完整 API
- [FAQ](../faq.md) - 常见问题解答

