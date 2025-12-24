from typing import Any
import json

from .openai_gateway import OpenaiGateway
from vnag.object import Message
from vnag.constant import Role


class OpenrouterGateway(OpenaiGateway):
    """
    OpenRouter 网关

    继承自 OpenaiGateway，覆盖钩子方法以支持：
    - reasoning_details 格式的 thinking 提取
    - 请求中启用 reasoning 参数
    - 回传 thinking 内容到后续请求
    """

    default_name: str = "OpenRouter"

    default_setting: dict = {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "",
        "reasoning_effort": ["high", "medium", "low"]
    }

    def init(self, setting: dict[str, Any]) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""
        self.reasoning_effort: str = setting.get("reasoning_effort", "medium")
        return super().init(setting)

    def _get_reasoning_data(self, obj: Any) -> list | None:
        """从对象中获取 reasoning_details 数据"""
        if hasattr(obj, "reasoning_details") and obj.reasoning_details:
            return obj.reasoning_details
        return None

    def _extract_thinking(self, message: Any) -> str:
        """从消息对象中提取 thinking 内容"""
        reasoning_data = self._get_reasoning_data(message)
        if not reasoning_data:
            return ""

        thinking: str = ""
        for detail in reasoning_data:
            if isinstance(detail, dict) and detail.get("text"):
                thinking += detail["text"]
        return thinking

    def _extract_thinking_delta(self, delta: Any) -> str:
        """从流式 delta 对象中提取 thinking 增量"""
        reasoning_data = self._get_reasoning_data(delta)
        if not reasoning_data:
            return ""

        thinking: str = ""
        for detail in reasoning_data:
            if isinstance(detail, dict) and detail.get("text"):
                thinking += detail["text"]
        return thinking

    def _get_extra_body(self) -> dict[str, Any]:
        """获取请求的额外参数，启用 OpenRouter 的 reasoning 功能"""
        return {"reasoning": {"effort": self.reasoning_effort}}

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """
        将内部 Message 格式转换为 OpenRouter API 格式

        覆盖父类方法，为 assistant 消息使用 content 数组格式，
        满足 Claude extended thinking 的要求。
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

            # 对于 assistant 消息，使用 content 数组格式
            if msg.role == Role.ASSISTANT:
                content_parts: list[dict[str, Any]] = []

                # 添加 thinking block（Claude 要求必须以此开头）
                if msg.thinking:
                    content_parts.append({
                        "type": "thinking",
                        "thinking": msg.thinking
                    })

                # 添加文本内容
                if msg.content:
                    content_parts.append({
                        "type": "text",
                        "text": msg.content
                    })

                if content_parts:
                    message_dict["content"] = content_parts
            elif msg.content:
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

            openai_messages.append(message_dict)

        return openai_messages
