# 自定义网关

本教程介绍如何创建自定义网关以支持新的大模型 API。

## 网关接口

所有网关都需要继承 `BaseGateway` 并实现以下方法：

```python
from abc import ABC, abstractmethod
from collections.abc import Generator
from vnag.object import Request, Response, Delta


class BaseGateway(ABC):
    """网关基类"""
    
    default_name: str = ""      # 网关名称
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

## 完整示例

以下是一个自定义网关的完整实现：

```python
from collections.abc import Generator
from typing import Any

from vnag.gateway import BaseGateway
from vnag.object import (
    Request, Response, Delta, Message, Usage, ToolCall
)
from vnag.constant import Role, FinishReason


class CustomGateway(BaseGateway):
    """自定义网关示例"""
    
    default_name = "custom"
    
    default_setting = {
        "api_key": "",
        "base_url": "https://api.example.com/v1"
    }
    
    def __init__(self):
        self.api_key: str = ""
        self.base_url: str = ""
        self.client = None
    
    def init(self, setting: dict) -> bool:
        """初始化客户端"""
        self.api_key = setting.get("api_key", "")
        self.base_url = setting.get("base_url", self.default_setting["base_url"])
        
        # 初始化 HTTP 客户端
        import httpx
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60.0
        )
        
        return True
    
    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """将 Message 列表转换为 API 格式"""
        result = []
        
        for msg in messages:
            if msg.role == Role.SYSTEM:
                result.append({
                    "role": "system",
                    "content": msg.content
                })
            elif msg.role == Role.USER:
                if msg.content:
                    result.append({
                        "role": "user",
                        "content": msg.content
                    })
                # 处理工具结果
                if msg.tool_results:
                    for tr in msg.tool_results:
                        result.append({
                            "role": "tool",
                            "tool_call_id": tr.id,
                            "content": tr.content
                        })
            elif msg.role == Role.ASSISTANT:
                msg_dict: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.content
                }
                # 处理工具调用
                if msg.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": str(tc.arguments)
                            }
                        }
                        for tc in msg.tool_calls
                    ]
                result.append(msg_dict)
        
        return result
    
    def invoke(self, request: Request) -> Response:
        """阻塞式调用"""
        # 构建请求体
        body = {
            "model": request.model,
            "messages": self._convert_messages(request.messages),
            "stream": False
        }
        
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.max_tokens is not None:
            body["max_tokens"] = request.max_tokens
        if request.tool_schemas:
            body["tools"] = [ts.get_schema() for ts in request.tool_schemas]
        
        # 发送请求
        response = self.client.post("/chat/completions", json=body)
        data = response.json()
        
        # 解析响应
        choice = data["choices"][0]
        message = choice["message"]
        
        return Response(
            id=data["id"],
            content=message.get("content", ""),
            usage=Usage(
                input_tokens=data["usage"]["prompt_tokens"],
                output_tokens=data["usage"]["completion_tokens"]
            ),
            finish_reason=self._parse_finish_reason(choice.get("finish_reason"))
        )
    
    def stream(self, request: Request) -> Generator[Delta, None, None]:
        """流式调用"""
        # 构建请求体
        body = {
            "model": request.model,
            "messages": self._convert_messages(request.messages),
            "stream": True
        }
        
        if request.temperature is not None:
            body["temperature"] = request.temperature
        if request.max_tokens is not None:
            body["max_tokens"] = request.max_tokens
        if request.tool_schemas:
            body["tools"] = [ts.get_schema() for ts in request.tool_schemas]
        
        # 发送流式请求
        with self.client.stream("POST", "/chat/completions", json=body) as response:
            response_id = ""
            
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                
                data_str = line[6:]  # 移除 "data: " 前缀
                if data_str == "[DONE]":
                    break
                
                import json
                data = json.loads(data_str)
                
                if not response_id:
                    response_id = data.get("id", "")
                
                choice = data["choices"][0]
                delta = choice.get("delta", {})
                
                # 解析内容
                content = delta.get("content")
                
                # 解析工具调用
                tool_calls = None
                if "tool_calls" in delta:
                    tool_calls = []
                    for tc in delta["tool_calls"]:
                        tool_calls.append(ToolCall(
                            id=tc.get("id", ""),
                            name=tc["function"]["name"],
                            arguments=tc["function"].get("arguments", {})
                        ))
                
                yield Delta(
                    id=response_id,
                    content=content,
                    calls=tool_calls,
                    finish_reason=self._parse_finish_reason(choice.get("finish_reason"))
                )
    
    def list_models(self) -> list[str]:
        """查询可用模型"""
        response = self.client.get("/models")
        data = response.json()
        
        return [model["id"] for model in data.get("data", [])]
    
    def _parse_finish_reason(self, reason: str | None) -> FinishReason | None:
        """解析结束原因"""
        if reason == "stop":
            return FinishReason.STOP
        elif reason == "tool_calls":
            return FinishReason.TOOL_CALLS
        elif reason == "length":
            return FinishReason.LENGTH
        return None
```

## 使用自定义网关

```python
from my_gateway import CustomGateway
from vnag.engine import AgentEngine

# 创建网关
gateway = CustomGateway()
gateway.init({
    "api_key": "your-api-key",
    "base_url": "https://api.example.com/v1"
})

# 使用引擎
engine = AgentEngine(gateway)
engine.init()
```

## 关键点说明

### 1. 消息转换

不同 API 的消息格式可能不同，需要在 `_convert_messages` 中处理：

- 角色映射（system/user/assistant）
- 工具调用格式
- 工具结果格式

### 2. 流式响应

流式响应需要：

- 处理 SSE（Server-Sent Events）格式
- 逐块解析并生成 Delta 对象
- 正确处理结束标记

### 3. 工具调用

如果 API 支持工具调用：

- 在请求中包含工具定义
- 解析响应中的工具调用
- 返回 ToolCall 对象

### 4. 错误处理

建议添加完善的错误处理：

```python
def stream(self, request: Request):
    try:
        # ... 请求逻辑
    except httpx.TimeoutException:
        yield Delta(id="error", content="请求超时")
    except httpx.HTTPError as e:
        yield Delta(id="error", content=f"HTTP 错误: {e}")
    except Exception as e:
        yield Delta(id="error", content=f"未知错误: {e}")
```

## 思维链支持

如果 API 支持思维链输出，在 Delta 中设置 `thinking` 字段：

```python
yield Delta(
    id=response_id,
    content=content,
    thinking=thinking_content,  # 思考过程
    ...
)
```

## 下一步

- [自定义工具](custom_tool.md) - 添加自定义工具
- [思维链集成](thinking.md) - 思维链的使用

