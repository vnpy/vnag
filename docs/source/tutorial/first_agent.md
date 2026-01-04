# 创建第一个 Agent

本教程将带您从零开始创建一个能够进行对话的 AI Agent。

## 准备工作

确保您已经：

1. 安装了 VNAG（参见 [安装指南](../getting_started/installation.md)）
2. 配置了 API 密钥（如 `.vnag/connect_openai.json`）

## 完整代码

```python
from vnag.utility import load_json
from vnag.gateways.openai_gateway import OpenaiGateway
from vnag.engine import AgentEngine
from vnag.object import Profile


def main():
    # 1. 加载 API 配置
    setting = load_json("connect_openai.json")
    
    # 2. 创建并初始化网关
    gateway = OpenaiGateway()
    gateway.init(setting)
    
    # 3. 创建并初始化引擎
    engine = AgentEngine(gateway)
    engine.init()
    
    # 4. 定义 Agent 配置
    profile = Profile(
        name="我的第一个助手",
        prompt="你是一个友好、乐于助人的 AI 助手。请用简洁清晰的语言回答用户的问题。",
        tools=[],  # 暂不使用工具
        temperature=0.7
    )
    
    # 5. 创建 Agent
    agent = engine.create_agent(profile)
    agent.set_model("gpt-4o-mini")  # 设置模型
    
    # 6. 进行对话
    print("Agent 已创建，开始对话...\n")
    
    # 使用流式输出
    for delta in agent.stream("你好！请介绍一下你自己。"):
        if delta.content:
            print(delta.content, end="", flush=True)
    
    print("\n")


if __name__ == "__main__":
    main()
```

## 代码解析

### 第一步：加载配置

```python
from vnag.utility import load_json

setting = load_json("connect_openai.json")
```

`load_json` 函数会自动从 `.vnag` 目录加载配置文件。配置文件格式如下：

```json
{
    "api_key": "sk-your-api-key",
    "base_url": "https://api.openai.com/v1"
}
```

### 第二步：初始化网关

```python
from vnag.gateways.openai_gateway import OpenaiGateway

gateway = OpenaiGateway()
gateway.init(setting)
```

网关（Gateway）负责与大模型 API 通信。VNAG 支持多种网关：

- `OpenaiGateway` - OpenAI 及兼容接口
- `AnthropicGateway` - Anthropic Claude
- `DashscopeGateway` - 阿里云 Dashscope
- `DeepseekGateway` - DeepSeek
- `MinimaxGateway` - MiniMax
- `BailianGateway` - 阿里云百炼
- `OpenrouterGateway` - OpenRouter

### 第三步：初始化引擎

```python
from vnag.engine import AgentEngine

engine = AgentEngine(gateway)
engine.init()
```

引擎（AgentEngine）是框架的核心，负责：
- 管理网关连接
- 加载工具（本地工具和 MCP 工具）
- 创建和管理 Agent 实例

### 第四步：定义配置

```python
from vnag.object import Profile

profile = Profile(
    name="我的第一个助手",
    prompt="你是一个友好、乐于助人的 AI 助手...",
    tools=[],
    temperature=0.7
)
```

Profile 定义了 Agent 的行为特征：
- `name` - 配置名称
- `prompt` - 系统提示词，定义 Agent 的角色和行为
- `tools` - 可用的工具列表
- `temperature` - 生成温度（0-2，越高越随机）

### 第五步：创建 Agent

```python
agent = engine.create_agent(profile)
agent.set_model("gpt-4o-mini")
```

通过引擎创建 Agent 实例，并指定使用的模型。

### 第六步：进行对话

```python
# 流式输出
for delta in agent.stream("你好！"):
    if delta.content:
        print(delta.content, end="", flush=True)
```

`stream()` 方法返回一个生成器，实时输出 AI 的响应。每个 `delta` 包含一小段文本。

如果不需要流式输出，可以使用 `invoke()` 方法：

```python
# 阻塞式调用
response = agent.invoke("你好！")
print(response.content)
```

## 多轮对话

Agent 会自动维护对话历史，支持多轮连续对话：

```python
# 第一轮
for delta in agent.stream("我叫张三"):
    if delta.content:
        print(delta.content, end="", flush=True)
print("\n")

# 第二轮 - Agent 会记住之前的对话
for delta in agent.stream("我刚才说我叫什么？"):
    if delta.content:
        print(delta.content, end="", flush=True)
print("\n")
```

## 保存会话

如果希望保存会话历史到本地文件，创建 Agent 时设置 `save=True`：

```python
agent = engine.create_agent(profile, save=True)
```

会话文件将保存在 `.vnag/session/` 目录下。

## 下一步

- [配置 Profile](profile.md) - 学习如何更精细地定制 Agent 行为
- [使用本地工具](local_tool.md) - 让 Agent 能够调用工具

