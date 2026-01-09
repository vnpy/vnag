from typing import Any, cast
import json

from .openai_gateway import OpenaiGateway
from vnag.object import Message
from vnag.constant import Role


class LitellmGateway(OpenaiGateway):
    """
    LiteLLM 网关

    继承自 OpenaiGateway，覆盖钩子方法以支持：
    - reasoning_content 格式的 thinking 提取（所有模型）
    - thinking_blocks 格式的 thinking 提取（Anthropic 模型）
    - 请求中启用 reasoning_effort 参数
    - 回传 thinking_blocks 内容到后续请求（Interleaved Thinking）

    LiteLLM 会将不同模型的 reasoning 输出标准化为：
    - reasoning_content: str - 所有支持 reasoning 的模型都返回
    - thinking_blocks: list - 仅 Anthropic 模型返回，包含 type、thinking、signature
    """

    default_name: str = "LiteLLM"

    default_setting: dict = {
        "base_url": "http://47.117.247.211:4000/",
        "api_key": "",
        "reasoning_effort": ["high", "medium", "low"],
    }

    def init(self, setting: dict[str, Any]) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""
        self.reasoning_effort: str = setting.get("reasoning_effort", "medium")
        return super().init(setting)

    def _extract_thinking(self, message: Any) -> str:
        """
        从消息对象中提取 thinking 内容

        LiteLLM 标准化输出：
        1. thinking_blocks - Anthropic 模型，包含 type、thinking、signature
        2. reasoning_content - 其他模型（DeepSeek 等），直接是字符串
        """
        # 优先从 thinking_blocks 提取（Anthropic 模型）
        if hasattr(message, "thinking_blocks") and message.thinking_blocks:
            thinking: str = ""
            for block in message.thinking_blocks:
                if isinstance(block, dict) and block.get("thinking"):
                    thinking += block["thinking"]
            if thinking:
                return thinking

        # 否则从 reasoning_content 提取（DeepSeek 等）
        if hasattr(message, "reasoning_content") and message.reasoning_content:
            return cast(str, message.reasoning_content)

        return ""

    def _extract_reasoning(self, message: Any) -> list[dict[str, Any]]:
        """
        从消息对象中提取 reasoning 数据

        返回 thinking_blocks 用于后续回传（Anthropic Interleaved Thinking）
        """
        if hasattr(message, "thinking_blocks") and message.thinking_blocks:
            return list(message.thinking_blocks)
        return []

    def _extract_thinking_delta(self, delta: Any) -> str:
        """
        从流式 delta 对象中提取 thinking 增量

        处理流式响应中的 reasoning_content 或 thinking_blocks 增量数据
        """
        # 优先从 thinking_blocks 提取（Anthropic 模型）
        if hasattr(delta, "thinking_blocks") and delta.thinking_blocks:
            thinking: str = ""
            for block in delta.thinking_blocks:
                if isinstance(block, dict) and block.get("thinking"):
                    thinking += block["thinking"]
            if thinking:
                return thinking

        # 否则从 reasoning_content 提取（DeepSeek 等）
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            return cast(str, delta.reasoning_content)

        return ""

    def _extract_reasoning_delta(self, delta: Any) -> list[dict[str, Any]]:
        """
        从流式 delta 对象中提取 reasoning 增量数据

        返回 thinking_blocks 增量用于累积
        """
        if hasattr(delta, "thinking_blocks") and delta.thinking_blocks:
            return list(delta.thinking_blocks)
        return []

    def _get_extra_body(self) -> dict[str, Any]:
        """
        获取请求的额外参数

        启用 LiteLLM 的 reasoning_effort 功能
        """
        return {"reasoning_effort": self.reasoning_effort}

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """
        将内部 Message 格式转换为 LiteLLM API 格式

        支持回传 thinking_blocks（Anthropic Interleaved Thinking）：
        - 如果消息有 reasoning 数据（thinking_blocks），需要回传
        - 这对于 Anthropic 模型的多轮对话至关重要
        """
        openai_messages: list[dict[str, Any]] = []

        for msg in messages:
            # 处理工具结果：拆分为多条 tool 消息
            if msg.tool_results:
                for tool_result in msg.tool_results:
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_result.id,
                        "content": tool_result.content
                    })
                continue

            message_dict: dict[str, Any] = {"role": msg.role.value}

            # 处理内容
            if msg.content:
                message_dict["content"] = msg.content

            # 处理 tool_calls
            if msg.tool_calls:
                message_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in msg.tool_calls
                ]

            # 对于 assistant 消息，回传 thinking_blocks（Anthropic Interleaved Thinking）
            if msg.role == Role.ASSISTANT and msg.reasoning:
                message_dict["thinking_blocks"] = msg.reasoning

            openai_messages.append(message_dict)

        return openai_messages
