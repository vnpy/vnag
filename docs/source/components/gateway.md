# Gateway 网关

Gateway 是与大模型 API 通信的抽象层，提供统一的接口规范。

## BaseGateway 基类

所有网关都继承自 `BaseGateway`：

```python
from vnag.gateway import BaseGateway

class BaseGateway(ABC):
    """网关基类"""
    
    default_name: str = ""      # 默认网关名称
    default_setting: dict = {}  # 默认配置
    
    @abstractmethod
    def init(self, setting: dict) -> bool:
        """初始化客户端"""
        pass
    
    @abstractmethod
    def invoke(self, request: Request) -> Response:
        """阻塞式调用"""
        pass
    
    @abstractmethod
    def stream(self, request: Request) -> Generator[Delta, None, None]:
        """流式调用"""
        pass
    
    @abstractmethod
    def list_models(self) -> list[str]:
        """查询可用模型"""
        pass
```

## 支持的网关

### OpenaiGateway

OpenAI API 及兼容接口。

```python
from vnag.gateways.openai_gateway import OpenaiGateway

gateway = OpenaiGateway()
gateway.init({
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1"
})
```

**配置说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `api_key` | str | API 密钥 |
| `base_url` | str | API 基础地址 |

**配置文件**：`.vnag/connect_openai.json`

```json
{
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1"
}
```

### AnthropicGateway

Anthropic Claude API。

```python
from vnag.gateways.anthropic_gateway import AnthropicGateway

gateway = AnthropicGateway()
gateway.init({
    "api_key": "sk-ant-xxx",
    "base_url": "https://api.anthropic.com"
})
```

**配置文件**：`.vnag/connect_anthropic.json`

### DashscopeGateway

阿里云 Dashscope API。

```python
from vnag.gateways.dashscope_gateway import DashscopeGateway

gateway = DashscopeGateway()
gateway.init({
    "api_key": "sk-xxx"
})
```

**配置文件**：`.vnag/connect_dashscope.json`

### DeepseekGateway

DeepSeek API，支持思维链推理。

```python
from vnag.gateways.deepseek_gateway import DeepseekGateway

gateway = DeepseekGateway()
gateway.init({
    "api_key": "sk-xxx",
    "base_url": "https://api.deepseek.com"
})
```

**特点**：
- 支持思维链（Thinking）输出
- 在响应的 `thinking` 字段中返回思考过程

**配置文件**：`.vnag/connect_deepseek.json`

### MinimaxGateway

MiniMax API，支持交错思维。

```python
from vnag.gateways.minimax_gateway import MinimaxGateway

gateway = MinimaxGateway()
gateway.init({
    "api_key": "xxx",
    "base_url": "https://api.minimaxi.com/v1"
})
```

**配置文件**：`.vnag/connect_minimax.json`

### BailianGateway

阿里云百炼平台，支持 Qwen3/QwQ 深度思考。

```python
from vnag.gateways.bailian_gateway import BailianGateway

gateway = BailianGateway()
gateway.init({
    "api_key": "sk-xxx",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
})
```

**配置文件**：`.vnag/connect_bailian.json`

### OpenrouterGateway

OpenRouter 多模型平台。

```python
from vnag.gateways.openrouter_gateway import OpenrouterGateway

gateway = OpenrouterGateway()
gateway.init({
    "api_key": "sk-xxx",
    "base_url": "https://openrouter.ai/api/v1",
    "reasoning_effort": "medium"  # 可选
})
```

**配置说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `api_key` | str | OpenRouter API 密钥 |
| `base_url` | str | API 地址 |
| `reasoning_effort` | str | 推理强度（low/medium/high） |

**配置文件**：`.vnag/connect_openrouter.json`

## 使用网关

### 基本使用

```python
from vnag.object import Request, Message
from vnag.constant import Role

# 创建请求
messages = [
    Message(role=Role.SYSTEM, content="你是一个助手"),
    Message(role=Role.USER, content="你好")
]

request = Request(
    model="gpt-4o",
    messages=messages,
    temperature=0.7
)

# 流式调用
for delta in gateway.stream(request):
    if delta.content:
        print(delta.content, end="")

# 阻塞式调用
response = gateway.invoke(request)
print(response.content)
```

### 查询模型

```python
models = gateway.list_models()
for model in models:
    print(model)
```

### 工具调用

```python
from vnag.object import ToolSchema

# 定义工具
tool_schema = ToolSchema(
    name="get_weather",
    description="获取天气信息",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名称"}
        },
        "required": ["city"]
    }
)

# 带工具的请求
request = Request(
    model="gpt-4o",
    messages=messages,
    tool_schemas=[tool_schema]
)

for delta in gateway.stream(request):
    if delta.calls:
        for call in delta.calls:
            print(f"调用工具: {call.name}")
            print(f"参数: {call.arguments}")
```

## Request 请求对象

```python
from vnag.object import Request

request = Request(
    model="gpt-4o",           # 模型名称
    messages=[...],           # 消息列表
    tool_schemas=[...],       # 工具定义列表
    temperature=0.7,          # 生成温度 (0-2)
    top_p=0.9,               # 核采样参数
    max_tokens=4096          # 最大输出 token
)
```

## Response 响应对象

阻塞式调用返回：

```python
response = gateway.invoke(request)

response.id             # 响应 ID
response.content        # 完整内容
response.thinking       # 思考过程（如果有）
response.usage          # Token 使用量
response.finish_reason  # 结束原因
response.message        # 完整消息对象
```

## Delta 流式响应块

流式调用返回：

```python
for delta in gateway.stream(request):
    delta.id             # 响应 ID
    delta.content        # 内容片段
    delta.thinking       # 思考片段（如果有）
    delta.reasoning      # 推理数据（特定模型）
    delta.calls          # 工具调用请求
    delta.finish_reason  # 结束原因
    delta.usage          # Token 使用量
```

## 思维链支持

部分网关支持返回模型的思考过程：

```python
# DeepSeek 示例
for delta in gateway.stream(request):
    if delta.thinking:
        print(f"[思考] {delta.thinking}")
    if delta.content:
        print(delta.content, end="")
```

支持思维链的网关：
- `DeepseekGateway`
- `MinimaxGateway`
- `BailianGateway`
- `OpenrouterGateway`（取决于模型）

## 自定义网关

如需支持其他 API，可以继承 `BaseGateway`：

```python
from vnag.gateway import BaseGateway
from vnag.object import Request, Response, Delta

class CustomGateway(BaseGateway):
    
    default_name = "custom"
    
    def init(self, setting: dict) -> bool:
        self.api_key = setting.get("api_key")
        self.base_url = setting.get("base_url")
        # 初始化客户端
        return True
    
    def invoke(self, request: Request) -> Response:
        # 实现阻塞式调用
        pass
    
    def stream(self, request: Request):
        # 实现流式调用
        pass
    
    def list_models(self) -> list[str]:
        # 返回可用模型列表
        return ["model-1", "model-2"]
```

## 下一步

- [Tool 工具系统](tool.md) - 了解工具系统
- [高级用法 - 自定义网关](../advanced/custom_gateway.md) - 详细的自定义网关教程

