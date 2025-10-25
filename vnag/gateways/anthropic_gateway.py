import json
from typing import Any
from collections.abc import Generator

from anthropic import Anthropic, Stream
from anthropic.types import Message as AnthropicMessage, MessageStreamEvent

from vnag.constant import FinishReason, Role
from vnag.gateway import BaseGateway
from vnag.object import Request, Response, Delta, Usage, Message, ToolCall


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

    def _convert_messages(self, messages: list[Message]) -> tuple[str, list[dict[str, Any]]]:
        """将内部格式转换为 Anthropic 格式"""
        system_prompt: str = ""
        anthropic_messages: list[dict[str, Any]] = []

        for msg in messages:
            # 提取 system 消息
            if msg.role == Role.SYSTEM:
                system_prompt = msg.content
                continue

            # 处理工具结果：合并为一条 user 消息
            if msg.tool_results:
                content_blocks: list[dict[str, Any]] = [
                    {
                        "type": "tool_result",
                        "tool_use_id": tr.id,
                        "content": tr.content,
                        "is_error": tr.is_error
                    }
                    for tr in msg.tool_results
                ]
                anthropic_messages.append({
                    "role": "user",
                    "content": content_blocks
                })

            # 处理 assistant 的工具调用
            elif msg.tool_calls:
                content_blocks = []

                # 如果有文本内容，先添加文本块
                if msg.content:
                    content_blocks.append({
                        "type": "text",
                        "text": msg.content
                    })

                # 添加工具调用块
                for tc in msg.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments
                    })

                anthropic_messages.append({
                    "role": "assistant",
                    "content": content_blocks
                })

            # 普通消息
            else:
                anthropic_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        return system_prompt, anthropic_messages

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

        # 使用新的消息转换方法
        system_prompt, anthropic_messages = self._convert_messages(request.messages)

        # 准备请求参数
        create_params: dict[str, Any] = {
            "model": request.model,
            "messages": anthropic_messages,
            "max_tokens": request.max_tokens,
            "system": system_prompt,
            "temperature": request.temperature,
        }

        # 添加工具定义（如果有）
        if request.tools_schemas:
            # 转换为 Anthropic 格式
            tools: list[dict[str, Any]] = [
                {
                    "name": schema.name,
                    "description": schema.description,
                    "input_schema": schema.parameters
                }
                for schema in request.tools_schemas
            ]
            create_params["tools"] = tools

        response: AnthropicMessage = self.client.messages.create(**create_params)

        usage: Usage = Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        # 提取文本内容和工具调用
        content: str = ""
        tool_calls: list[ToolCall] = []

        if response.content:
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text
                elif hasattr(block, "type") and block.type == "tool_use":
                    arguments: dict[str, Any] = {}
                    if isinstance(block.input, dict):
                        arguments = block.input

                    tool_call: ToolCall = ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=arguments
                    )
                    tool_calls.append(tool_call)

        # 确定结束原因
        finish_reason: FinishReason = FinishReason.UNKNOWN
        if response.stop_reason:
            finish_reason = ANTHROPIC_FINISH_REASON_MAP.get(
                response.stop_reason, FinishReason.UNKNOWN
            )

        # 构建返回的消息对象
        message = Message(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=tool_calls
        )

        return Response(
            id=response.id,
            content=content,
            usage=usage,
            finish_reason=finish_reason,
            message=message
        )

    def stream(self, request: Request) -> Generator[Delta, None, None]:
        """流式调用接口"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return

        if not request.max_tokens:
            self.write_log("max_tokens 为 Anthropic 必传参数")
            return

        # 使用新的消息转换方法
        system_prompt, anthropic_messages = self._convert_messages(request.messages)

        # 准备请求参数
        create_params: dict[str, Any] = {
            "model": request.model,
            "messages": anthropic_messages,
            "max_tokens": request.max_tokens,
            "stream": True,
            "system": system_prompt,
            "temperature": request.temperature,
        }

        # 添加工具定义（如果有）
        if request.tools_schemas:
            # 转换为 Anthropic 格式
            tools: list[dict[str, Any]] = [
                {
                    "name": schema.name,
                    "description": schema.description,
                    "input_schema": schema.parameters
                }
                for schema in request.tools_schemas
            ]
            create_params["tools"] = tools

        stream: Stream[MessageStreamEvent] = self.client.messages.create(**create_params)

        response_id: str = ""
        input_tokens: int = 0
        # 用于累积工具调用
        accumulated_tool_calls: dict[int, dict[str, Any]] = {}
        current_block_index: int = -1

        for stream_event in stream:
            if stream_event.type == "message_start":
                response_id = stream_event.message.id
                input_tokens = stream_event.message.usage.input_tokens

            elif stream_event.type == "content_block_start":
                # 记录当前内容块的索引
                current_block_index = stream_event.index
                if stream_event.content_block.type == "tool_use":
                    accumulated_tool_calls[current_block_index] = {
                        "id": stream_event.content_block.id,
                        "name": stream_event.content_block.name,
                        "input": ""
                    }

            elif stream_event.type == "content_block_delta":
                if stream_event.delta.type == "text_delta":
                    yield Delta(
                        id=response_id,
                        content=stream_event.delta.text,
                    )
                elif stream_event.delta.type == "input_json_delta":
                    # 累积工具调用的参数
                    if stream_event.index in accumulated_tool_calls:
                        accumulated_tool_calls[stream_event.index]["input"] += stream_event.delta.partial_json

            elif stream_event.type == "message_delta":
                finish_reason: FinishReason = FinishReason.UNKNOWN
                if stream_event.delta.stop_reason:
                    finish_reason = ANTHROPIC_FINISH_REASON_MAP.get(
                        stream_event.delta.stop_reason, FinishReason.UNKNOWN
                    )

                delta = Delta(
                    id=response_id,
                    finish_reason=finish_reason,
                    usage=Usage(
                        input_tokens=input_tokens,
                        output_tokens=stream_event.usage.output_tokens,
                    ),
                )

                # 如果是工具调用结束，转换累积的工具调用
                if finish_reason == FinishReason.TOOL_CALLS and accumulated_tool_calls:
                    tool_calls: list[ToolCall] = []
                    for tc_data in accumulated_tool_calls.values():
                        try:
                            arguments: dict[str, Any] = json.loads(tc_data["input"])
                        except json.JSONDecodeError:
                            arguments = {}

                        tool_calls.append(ToolCall(
                            id=tc_data["id"],
                            name=tc_data["name"],
                            arguments=arguments
                        ))

                    delta.calls = tool_calls

                yield delta

    def list_models(self) -> list[str]:
        """查询可用模型列表"""
        self.write_log("Anthropic API 不支持查询模型列表")
        return []
