from typing import Any

from .openai_gateway import OpenaiGateway


class BailianGateway(OpenaiGateway):
    """
    阿里云百炼网关

    继承自 OpenaiGateway，覆盖钩子方法以支持：
    - reasoning_content 格式的 thinking 提取（Qwen3/QwQ 等模型）
    - 请求中启用 enable_thinking 参数
    - 回传 thinking 内容到后续请求
    """

    default_name: str = "Bailian"

    default_setting: dict = {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": ""
    }

    def _extract_thinking(self, message: Any) -> str:
        """
        从消息对象中提取 thinking 内容

        百炼平台使用 reasoning_content 字段返回推理思考内容，
        适用于 Qwen3、QwQ 等支持深度思考的模型。
        """
        if hasattr(message, "reasoning_content") and message.reasoning_content:
            return message.reasoning_content
        return ""

    def _extract_thinking_delta(self, delta: Any) -> str:
        """
        从流式 delta 对象中提取 thinking 增量

        处理流式响应中的 reasoning_content 增量数据
        """
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            return delta.reasoning_content
        return ""

    def _get_extra_body(self) -> dict[str, Any] | None:
        """
        获取请求的额外参数

        启用百炼平台的思考模式
        """
        return {"enable_thinking": True}

    def _convert_thinking_for_request(self, thinking: str) -> dict[str, Any] | None:
        """
        将 thinking 转换为请求格式

        百炼平台在多轮对话中需要回传 reasoning_content 字段
        """
        return {"reasoning_content": thinking}

