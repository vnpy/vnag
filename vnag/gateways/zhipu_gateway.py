from typing import Any

from .completion_gateway import CompletionGateway


class ZhipuGateway(CompletionGateway):
    """
    智谱 (Zhipu) 网关

    继承自 CompletionGateway，覆盖钩子方法以支持：
    - reasoning_content 格式的 thinking 提取
    - 请求中启用 thinking 参数（始终开启保留式思考）
    - 回传 thinking 内容到后续请求（交错式思考）

    参考文档：
    - https://docs.bigmodel.cn/cn/guide/capabilities/thinking
    - https://docs.bigmodel.cn/cn/guide/capabilities/thinking-mode
    - https://docs.bigmodel.cn/cn/guide/develop/openai/introduction

    注意事项：
    - 智谱使用 reasoning_content 字段（字符串），与 DeepSeek 格式相同
    - 工具调用过程中必须回传 reasoning_content 以保持推理连贯性（交错式思考）
    - 始终使用 clear_thinking=false（保留式思考）：服务端跨轮保留推理上下文，
      有助于提高缓存命中率和推理连贯性，适合 Agent 和编码场景
    """

    default_name: str = "ZhiPu"

    default_setting: dict = {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": "",
        "proxy": "",
    }

    def _extract_thinking(self, message: Any) -> str:
        """
        从消息对象中提取 thinking 内容

        智谱使用 reasoning_content 字段（字符串，与 content 同级），
        格式与 DeepSeek 完全相同。
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

    def _get_extra_body(self) -> dict[str, Any]:
        """
        获取请求的额外参数

        始终启用 thinking，并固定使用保留式思考（clear_thinking=False），
        服务端跨轮保留推理上下文，提高缓存命中率和推理连贯性。
        """
        return {
            "thinking": {
                "type": "enabled",
                "clear_thinking": False,
            }
        }

    def _convert_thinking_for_request(self, thinking: str) -> dict[str, Any] | None:
        """
        将 thinking 转换为请求格式

        使用智谱的 reasoning_content 格式回传 thinking 内容。

        这对于交错式思考（Interleaved Thinking）多轮对话至关重要：
        - 工具调用完成后，必须把上一轮的 reasoning_content 完整回传
        - 智谱服务端会在工具结果基础上继续推理，保持思维链连贯性
        - 回传内容不可修改或重排，否则影响推理效果和缓存命中
        """
        if not thinking:
            return None
        return {"reasoning_content": thinking}
