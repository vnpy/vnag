from typing import Any
from collections.abc import Generator

from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.model import Model

from vnag.gateway import BaseGateway
from vnag.object import FinishReason, Request, Response, Delta, Usage


FINISH_REASON_MAP = {
    "stop": FinishReason.STOP,
    "length": FinishReason.LENGTH,
    "tool_calls": FinishReason.TOOL_CALLS,
}


class OpenaiGateway(BaseGateway):
    """OpenAI风格的AI大模型网关"""

    default_name: str = "OpenAI"

    default_setting: dict = {
        "base_url": "",
        "api_key": "",
    }

    def __init__(self, gateway_name: str = "") -> None:
        """构造函数"""
        if not gateway_name:
            gateway_name = self.default_name
        self.gateway_name = gateway_name

        self.client: OpenAI | None = None

    def init(self, setting: dict[str, Any]) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""
        base_url: str = setting.get("base_url", "")
        api_key: str = setting.get("api_key", "")

        if not base_url or not api_key:
            self.write_log("配置不完整，请检查以下配置项：")
            if not base_url:
                self.write_log("  - base_url: API地址未设置")
            if not api_key:
                self.write_log("  - api_key: API密钥未设置")
            return False

        self.client = OpenAI(api_key=api_key, base_url=base_url)

        return True

    def invoke(self, request: Request) -> Response:
        """常规调用接口：将已准备好的消息发送给模型并一次性产出文本。"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return Response(id="", content="", usage=Usage())

        response: ChatCompletion = self.client.chat.completions.create(
            model=request.model,
            messages=[msg.model_dump() for msg in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        usage: Usage = Usage()
        if response.usage:
            usage.input_tokens = response.usage.prompt_tokens
            usage.output_tokens = response.usage.completion_tokens

        return Response(
            id=response.id,
            content=response.choices[0].message.content or "",
            usage=usage,
        )

    def stream(self, request: Request) -> Generator[Delta, None, None]:
        """流式调用接口"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return

        stream: Stream[ChatCompletionChunk] = self.client.chat.completions.create(
            model=request.model,
            messages=[msg.model_dump() for msg in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )

        response_id: str = ""
        for chuck in stream:
            if not response_id:
                response_id = chuck.id

            delta: Delta = Delta(id=response_id)
            should_yield: bool = False

            # 检查内容增量
            delta_content: str | None = chuck.choices[0].delta.content
            if delta_content:
                delta.content = delta_content
                should_yield = True

            # 检查结束原因
            openai_finish_reason = chuck.choices[0].finish_reason
            if openai_finish_reason:
                vnag_finish_reason: FinishReason = FINISH_REASON_MAP.get(
                    openai_finish_reason, FinishReason.UNKNOWN
                )
                delta.finish_reason = vnag_finish_reason
                should_yield = True

            # 检查用量信息（通常在最后一个数据块中）
            if chuck.usage:
                delta.usage = Usage(
                    input_tokens=chuck.usage.prompt_tokens,
                    output_tokens=chuck.usage.completion_tokens,
                )
                should_yield = True

            if should_yield:
                yield delta

    def list_models(self) -> list[str]:
        """查询可用模型列表"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return []

        models: list[Model] = self.client.models.list()
        return sorted([model.id for model in models])
