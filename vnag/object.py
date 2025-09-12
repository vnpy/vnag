from pydantic import BaseModel, Field

from .constant import Role, FinishReason


class Segment(BaseModel):
    """A unified structure for document chunks."""
    text: str
    metadata: dict[str, str]
    score: float = 0


class Message(BaseModel):
    """标准化的消息对象"""
    role: Role
    content: str


class Usage(BaseModel):
    """标准化的大模型用量统计"""
    input_tokens: int = 0
    output_tokens: int = 0


class Request(BaseModel):
    """标准化的LLM请求对象"""
    model: str
    messages: list[Message]
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)


class Response(BaseModel):
    """标准化的LLM阻塞式响应对象"""
    id: str
    content: str
    usage: Usage


class Delta(BaseModel):
    """标准化的LLM流式响应块"""

    id: str
    content: str | None = None
    finish_reason: FinishReason | None = None
    usage: Usage | None = None
