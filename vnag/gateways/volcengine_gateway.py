from typing import Any

from .openai_gateway import OpenaiGateway


class VolcengineGateway(OpenaiGateway):
    """
    火山引擎（火山方舟）网关

    继承自 OpenaiGateway，覆盖钩子方法以支持：
    - reasoning_content 格式的 thinking 提取
    - 请求中启用 thinking 参数
    - 回传 thinking 内容到后续请求（交错式思考 / 工具调用场景）

    参考文档：
    - https://www.volcengine.com/docs/82379/1330626  (兼容 OpenAI SDK)
    - https://www.volcengine.com/docs/82379/2123275  (流式输出)

    注意事项：
    - 火山方舟使用 reasoning_content 字段（字符串），与 DeepSeek/智谱格式相同
    - 工具调用过程中必须回传 reasoning_content 以保持推理连贯性
    - base_url 默认指向北京区接入点，如需其他区域请在配置中覆盖
    """

    default_name: str = "Volcengine"

    default_setting: dict = {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key": "",
        "proxy": "",
    }

    def _extract_thinking(self, message: Any) -> str:
        """
        从消息对象中提取 thinking 内容

        火山方舟使用 reasoning_content 字段（字符串，与 content 同级），
        格式与 DeepSeek / 智谱完全相同。
        """
        if hasattr(message, "reasoning_content") and message.reasoning_content:
            return str(message.reasoning_content)
        return ""

    def _extract_thinking_delta(self, delta: Any) -> str:
        """
        从流式 delta 对象中提取 thinking 增量

        处理流式响应中的 reasoning_content 增量数据。
        reasoning_content 必定先于 content 出现。
        """
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            return str(delta.reasoning_content)
        return ""

    def _get_extra_body(self) -> dict[str, Any] | None:
        """
        获取请求的额外参数

        启用火山方舟的深度思考模式。
        对于不支持思考的模型，此参数会被 API 自动忽略。
        """
        return {"thinking": {"type": "enabled"}}

    def _convert_thinking_for_request(self, thinking: str) -> dict[str, Any] | None:
        """
        将 thinking 转换为请求格式

        使用 reasoning_content 格式回传 thinking 内容。

        重要说明：
        - 工具调用过程中：必须回传 reasoning_content，否则推理链会中断
        - 普通多轮对话：API 会自动忽略回传的 reasoning_content
        - 因此可以统一回传，让 API 自行决定是否使用
        """
        if not thinking:
            return None
        return {"reasoning_content": thinking}
