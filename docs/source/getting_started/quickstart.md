# 快速开始

本教程将帮助您在 3 分钟内启动一个功能完备的 AI Agent。

## 第一步：配置 API 密钥

VNAG 需要 API 密钥来与大模型服务进行通信。

1. 在项目根目录下创建 `.vnag` 目录（如果不存在）
2. 创建配置文件 `connect_openai.json`（或其他服务商）
3. 填入您的 API 配置

**示例配置文件**：

```json
{
    "api_key": "sk-YourAPIKey",
    "base_url": "https://api.openai.com/v1"
}
```

:::{tip}
您也可以通过 UI 界面配置：运行程序后，点击【菜单栏 → 功能 → AI服务配置】
:::

## 第二步：运行聊天 UI

在项目根目录下运行：

```bash
python examples/ui/run_chat_ui.py
```

恭喜！您现在应该能看到一个美观的聊天窗口了。

## 第三步：创建您的 Agent

在 UI 界面中：

1. **创建 Profile**：点击左侧面板的「+」按钮，定义 Agent 的系统提示词、工具集和模型参数
2. **新建会话**：基于 Profile 创建新的对话会话
3. **开始对话**：在输入框中输入消息，与 Agent 交互

## 通过代码创建 Agent

如果您希望通过代码控制 Agent，可以参考以下示例：

```python
from vnag.utility import load_json
from vnag.gateways.openai_gateway import OpenaiGateway
from vnag.engine import AgentEngine
from vnag.object import Profile

# 1. 加载配置并初始化网关
setting = load_json("connect_openai.json")
gateway = OpenaiGateway()
gateway.init(setting)

# 2. 初始化引擎
engine = AgentEngine(gateway)
engine.init()

# 3. 创建 Profile（智能体配置）
profile = Profile(
    name="我的助手",
    prompt="你是一个乐于助人的 AI 助手。",
    tools=["datetime-tools_current-date"],  # 工具列表，不需要工具时传空列表 []
    temperature=0.7
)

# 4. 创建 Agent 并对话
agent = engine.create_agent(profile)
agent.set_model("gpt-4o-mini")

# 流式输出
for delta in agent.stream("你好，请介绍一下你自己"):
    if delta.content:
        print(delta.content, end="", flush=True)
```

## 使用工具

VNAG 支持两种类型的工具：

### 本地工具

内置的本地工具包括日期时间、文件系统、网络、代码执行、Web 等。在 Profile 中添加工具名称即可使用：

```python
profile = Profile(
    name="工具助手",
    prompt="你是一个能够使用工具的助手。",
    tools=[
        "datetime-tools_current-date",      # 获取当前日期
        "datetime-tools_day-of-week",       # 获取星期几
        "network-tools_ping",               # 网络 ping 测试
    ]
)
```

### MCP 工具

MCP 工具需要在 `.vnag/mcp_config.json` 中配置：

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

配置后，MCP 工具会自动加载，可在 Profile 的工具列表中选择使用。

## 运行示例

`examples` 目录提供了丰富的示例脚本：

```bash
# 测试 Gateway
python examples/gateway/run_openai_gateway.py

# 测试本地工具
python examples/tool/run_local_tool.py

# 测试 MCP 工具
python examples/tool/run_mcp_tool.py

# 测试 TaskAgent
python examples/agent/run_task_agent.py
```

## 下一步

- [核心概念](key_concepts.md) - 深入理解 Agent、Profile、Tool 等概念
- [教程](../tutorial/index.md) - 更多详细的使用教程
- [API 参考](../api/index.rst) - 查看完整的 API 文档

