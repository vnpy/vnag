from typing import Any

from pydantic import BaseModel, Field

from .constant import Role, FinishReason


class Segment(BaseModel):
    """统一文档片段结构"""
    text: str
    metadata: dict[str, str]
    score: float = 0


class Message(BaseModel):
    """标准化的消息对象"""
    role: Role
    content: str = ""
    thinking: str = ""
    tool_calls: list["ToolCall"] = Field(default_factory=list)
    tool_results: list["ToolResult"] = Field(default_factory=list)


class Usage(BaseModel):
    """标准化的大模型用量统计"""
    input_tokens: int = 0
    output_tokens: int = 0


class Request(BaseModel):
    """标准化的LLM请求对象"""
    model: str
    messages: list[Message]
    tool_schemas: list["ToolSchema"] = Field(default_factory=list)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, gt=0)


class Response(BaseModel):
    """标准化的LLM阻塞式响应对象"""
    id: str
    content: str
    thinking: str = ""
    usage: Usage
    finish_reason: FinishReason | None = None
    message: Message | None = None


class Delta(BaseModel):
    """标准化的LLM流式响应块"""

    id: str
    content: str | None = None
    thinking: str | None = None
    calls: list["ToolCall"] | None = None
    finish_reason: FinishReason | None = None
    usage: Usage | None = None


class ToolSchema(BaseModel):
    """统一的工具类（纯描述，不包含执行逻辑）"""
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)

    def get_schema(self) -> dict[str, Any]:
        """返回工具的 Schema 定义"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class ToolCall(BaseModel):
    """工具调用请求"""
    id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """工具执行结果（通用格式）"""
    id: str  # 工具调用ID，用于关联原始的工具调用
    name: str  # 工具名称，某些API（如Gemini）需要
    content: str  # 工具执行结果内容
    is_error: bool = False  # 标识是否为错误结果（Anthropic支持）


class Profile(BaseModel):
    """智能体配置数据"""
    name: str
    prompt: str
    tools: list[str]
    temperature: float | None = None
    max_tokens: int | None = None
    max_iterations: int = 10


class Session(BaseModel):
    """聊天交互会话历史"""
    id: str
    profile: str
    name: str
    model: str = ""
    messages: list[Message] = Field(default_factory=list)
