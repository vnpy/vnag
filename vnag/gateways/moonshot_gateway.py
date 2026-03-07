from typing import Any

from .openai_gateway import OpenaiGateway


class MoonshotGateway(OpenaiGateway):
    """
    Moonshot AI 网关

    继承自 OpenaiGateway，覆盖钩子方法以支持：
    - reasoning_content 格式的 thinking 提取
    - 回传 thinking 内容到后续请求（工具调用场景）

    与 DeepSeek 的关键差异：
    - thinking 随模型默认启用，无需额外的 extra_body 参数
    - 使用 reasoning_content 字段（字符串），而非 reasoning_details（数组）

    参考文档：
    - https://platform.moonshot.cn/docs/guide/start-using-kimi-api
    - https://platform.moonshot.cn/docs/guide/use-kimi-k2-thinking-model
    """

    default_name: str = "Moonshot"

    default_setting: dict = {
        "base_url": "https://api.moonshot.cn/v1",
        "api_key": "",
        "proxy": "",
    }

    def _extract_thinking(self, message: Any) -> str:
        """
        从消息对象中提取 thinking 内容

        Moonshot 使用 reasoning_content 字段（字符串，与 content 同级）
        """
        if hasattr(message, "reasoning_content") and message.reasoning_content:
            return str(message.reasoning_content)
        return ""

    def _convert_thinking_for_request(self, thinking: str) -> dict[str, Any]:
        """
        将 thinking 转换为请求格式

        使用 reasoning_content 格式回传 thinking 内容。

        重要说明（来自官方文档）：
        - 工具调用过程中：必须回传 reasoning_content，否则 API 返回 400 错误
        - 普通多轮对话：API 会自动忽略回传的 reasoning_content
        - 因此可以统一回传，让 API 自行决定是否使用
        """
        return {"reasoning_content": thinking}

    def _extract_thinking_delta(self, delta: Any) -> str:
        """
        从流式 delta 对象中提取 thinking 增量

        处理流式响应中的 reasoning_content 增量数据。
        reasoning_content 必定先于 content 出现。
        """
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            return str(delta.reasoning_content)
        return ""
