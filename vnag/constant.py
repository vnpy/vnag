from enum import Enum


class Role(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class FinishReason(str, Enum):
    """流式响应结束原因"""
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    UNKNOWN = "unknown"
    ERROR = "error"
