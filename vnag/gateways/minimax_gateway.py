from typing import Any

from .openai_gateway import OpenaiGateway


class MinimaxGateway(OpenaiGateway):
    """
    MiniMax 网关

    继承自 OpenaiGateway，覆盖钩子方法以支持：
    - reasoning_details 格式的 thinking 提取
    - 请求中启用 reasoning_split 参数
    - 回传 thinking 内容到后续请求（Interleaved Thinking）
    """

    default_name: str = "MiniMax"

    default_setting: dict = {
        "base_url": "https://api.minimaxi.com/v1",
        "api_key": "",
    }

    def _extract_thinking(self, message: Any) -> str:
        """
        从消息对象中提取 thinking 内容

        MiniMax 使用 reasoning_details 数组格式，每个元素包含 text 字段
        """
        thinking: str = ""

        if not hasattr(message, "reasoning_details") or not message.reasoning_details:
            return thinking

        for detail in message.reasoning_details:
            # 对象格式（常见）
            if hasattr(detail, "text") and detail.text:
                thinking += detail.text
            # 字典格式（某些情况下 API 返回 dict）
            elif isinstance(detail, dict) and detail.get("text"):
                thinking += detail["text"]

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
            # 字典格式
            elif isinstance(detail, dict) and detail.get("text"):
                thinking += detail["text"]

        return thinking

    def _get_extra_body(self) -> dict[str, Any]:
        """
        获取请求的额外参数

        启用 MiniMax 的 reasoning_split 功能，将 thinking 内容分离到 reasoning_details 中
        """
        return {"reasoning_split": True}

    def _convert_thinking_for_request(self, thinking: str) -> dict[str, Any]:
        """
        将 thinking 转换为请求格式

        使用 MiniMax 的 reasoning_details 格式回传 thinking 内容。
        这对于 Interleaved Thinking 多轮对话至关重要：
        完整的 response_message（包括 reasoning_details）必须保存在 Message History 中，
        并在下一轮传回模型，以确保模型的思维链不被中断。
        """
        return {"reasoning_details": [{"text": thinking}]}
