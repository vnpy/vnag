from typing import Any
from collections.abc import Generator

from anthropic import Anthropic, Stream
from anthropic.types import Message as AnthropicMessage, MessageStreamEvent

from vnag.constant import FinishReason
from vnag.gateway import BaseGateway
from vnag.object import Request, Response, StreamChunk, Usage


ANTHROPIC_FINISH_REASON_MAP = {
    "end_turn": FinishReason.STOP,
    "max_tokens": FinishReason.LENGTH,
    "stop_sequence": FinishReason.STOP,
    "tool_use": FinishReason.TOOL_CALLS,
}


class AnthropicGateway(BaseGateway):
    """连接 Anthropic 官方 SDK 的网关，提供统一接口"""

    default_name: str = "Anthropic"

    default_setting: dict = {
        "base_url": "",
        "api_key": "",
    }

    def __init__(self, gateway_name: str = "") -> None:
        """构造函数"""
        if not gateway_name:
            gateway_name = self.default_name
        self.gateway_name = gateway_name
        self.client: Anthropic | None = None

    def init(self, setting: dict[str, Any]) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""
        base_url: str | None = setting.get("base_url", None)
        api_key: str = setting.get("api_key", "")

        if not api_key:
            self.write_log("配置不完整，请检查以下配置项：")
            self.write_log("  - api_key: API密钥未设置")
            return False

        self.client = Anthropic(api_key=api_key, base_url=base_url)

        return True

    def invoke(self, request: Request) -> Response:
        """常规调用接口：将已准备好的消息发送给模型并一次性产出文本。"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return Response(id="", content="LLM客户端未初始化", usage=Usage())

        if not request.max_tokens:
            self.write_log("max_tokens 为 Anthropic 必传参数")
            return Response(id="", content="max_tokens 不能为空", usage=Usage())

        messages = [msg.model_dump() for msg in request.messages]
        system_prompt = ""
        if messages and messages[0]["role"] == "system":
            system_prompt = messages.pop(0)["content"]

        response: AnthropicMessage = self.client.messages.create(
            model=request.model,
            messages=messages,
            max_tokens=request.max_tokens,
            system=system_prompt,
            temperature=request.temperature,
        )

        usage: Usage = Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        content: str = ""
        if response.content:
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

        return Response(
            id=response.id,
            content=content,
            usage=usage,
        )

    def stream(self, request: Request) -> Generator[StreamChunk, None, None]:
        """流式调用接口"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return

        if not request.max_tokens:
            self.write_log("max_tokens 为 Anthropic 必传参数")
            return

        messages: list[dict] = [msg.model_dump() for msg in request.messages]
        system_prompt = ""
        if messages and messages[0]["role"] == "system":
            system_prompt = messages.pop(0)["content"]

        stream: Stream[MessageStreamEvent] = self.client.messages.create(
            model=request.model,
            messages=messages,
            max_tokens=request.max_tokens,
            stream=True,
            system=system_prompt,
            temperature=request.temperature,
        )

        response_id: str = ""
        input_tokens: int = 0

        for stream_event in stream:
            if stream_event.type == "message_start":
                response_id = stream_event.message.id
                input_tokens = stream_event.message.usage.input_tokens

            elif (
                stream_event.type == "content_block_delta"
                and stream_event.delta.type == "text_delta"
            ):
                yield StreamChunk(
                    id=response_id,
                    content=stream_event.delta.text,
                )

            elif stream_event.type == "message_delta":
                finish_reason: FinishReason = ANTHROPIC_FINISH_REASON_MAP.get(
                    stream_event.delta.stop_reason, FinishReason.UNKNOWN
                )

                yield StreamChunk(
                    id=response_id,
                    finish_reason=finish_reason,
                    usage=Usage(
                        input_tokens=input_tokens,
                        output_tokens=stream_event.usage.output_tokens,
                    ),
                )

    def list_models(self) -> list[str]:
        """查询可用模型列表"""
        self.write_log("Anthropic API 不支持查询模型列表")
        return []
