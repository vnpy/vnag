from typing import Any

from .openai_gateway import OpenaiGateway


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
        "reasoning_effort": "medium",
    }

    def init(self, setting: dict[str, Any]) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""
        self.reasoning_effort: str = setting.get("reasoning_effort", "medium")

        return super().init(setting)

    def _extract_thinking(self, message: Any) -> str:
        """
        从消息对象中提取 thinking 内容

        OpenRouter 使用 reasoning_details 数组格式，包含：
        - reasoning.text 类型：详细推理内容
        - reasoning.summary 类型：推理摘要
        """
        thinking: str = ""

        if not hasattr(message, "reasoning_details") or not message.reasoning_details:
            return thinking

        for detail in message.reasoning_details:
            # 对象格式（常见）
            if hasattr(detail, "text") and detail.text:
                thinking += detail.text
            elif hasattr(detail, "summary") and detail.summary:
                thinking += detail.summary
            # 字典格式（某些情况下 API 返回 dict）
            elif isinstance(detail, dict):
                if detail.get("text"):
                    thinking += detail["text"]
                elif detail.get("summary"):
                    thinking += detail["summary"]

        return thinking

    def _extract_thinking_delta(self, delta: Any) -> str:
        """
        从流式 delta 对象中提取 thinking 增量

        处理流式响应中的 reasoning_details 增量数据
        """
        thinking: str = ""

        if not hasattr(delta, "reasoning_details") or not delta.reasoning_details:
            return thinking

        for detail in delta.reasoning_details:
            # 对象格式
            if hasattr(detail, "text") and detail.text:
                thinking += detail.text
            elif hasattr(detail, "summary") and detail.summary:
                thinking += detail.summary
            # 字典格式
            elif isinstance(detail, dict):
                if detail.get("text"):
                    thinking += detail["text"]
                elif detail.get("summary"):
                    thinking += detail["summary"]

        return thinking

    def _get_extra_body(self) -> dict[str, Any]:
        """
        获取请求的额外参数

        启用 OpenRouter 的 reasoning 功能
        """
        return {
            "reasoning": {"effort": self.reasoning_effort},
        }

    def _convert_thinking_for_request(self, thinking: str) -> dict[str, Any]:
        """
        将 thinking 转换为请求格式

        使用 OpenRouter 的 reasoning_details 格式回传 thinking 内容，
        对于 Extended Thinking 多轮对话至关重要。
        """
        return {
            "reasoning_details": [
                {
                    "type": "reasoning.text",
                    "text": thinking,
                }
            ]
        }
