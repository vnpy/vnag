from typing import Any

from .openai_gateway import OpenaiGateway


class DeepseekGateway(OpenaiGateway):
    """
    DeepSeek 网关

    继承自 OpenaiGateway，覆盖钩子方法以支持：
    - reasoning_content 格式的 thinking 提取
    - 请求中启用 thinking 参数
    - 回传 thinking 内容到后续请求（工具调用场景）

    参考文档：https://api-docs.deepseek.com/zh-cn/guides/thinking_mode

    注意事项：
    - DeepSeek 使用 reasoning_content 字段（字符串），而非 reasoning_details（数组）
    - 工具调用过程中必须回传 reasoning_content，否则 API 返回 400 错误
    - 普通多轮对话中，API 会自动忽略回传的 reasoning_content
    """

    default_name: str = "DeepSeek"

    default_setting: dict = {
        "base_url": "https://api.deepseek.com",
        "api_key": "",
    }

    def _extract_thinking(self, message: Any) -> str:
        """
        从消息对象中提取 thinking 内容

        DeepSeek 使用 reasoning_content 字段（与 content 同级）
        """
        if hasattr(message, "reasoning_content") and message.reasoning_content:
            return str(message.reasoning_content)
        return ""

    def _extract_thinking_delta(self, delta: Any) -> str:
        """
        从流式 delta 对象中提取 thinking 增量

        处理流式响应中的 reasoning_content 增量数据
        """
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            return str(delta.reasoning_content)
        return ""

    def _get_extra_body(self) -> dict[str, Any]:
        """
        获取请求的额外参数

        启用 DeepSeek 的 thinking 模式
        也可以直接使用 model="deepseek-reasoner" 启用
        """
        return {"thinking": {"type": "enabled"}}

    def _convert_thinking_for_request(self, thinking: str) -> dict[str, Any]:
        """
        将 thinking 转换为请求格式

        使用 DeepSeek 的 reasoning_content 格式回传 thinking 内容。

        重要说明（来自官方文档）：
        - 工具调用过程中：必须回传 reasoning_content，否则 API 返回 400 错误
        - 普通多轮对话：API 会自动忽略回传的 reasoning_content
        - 因此可以统一回传，让 API 自行决定是否使用
        """
        return {"reasoning_content": thinking}
