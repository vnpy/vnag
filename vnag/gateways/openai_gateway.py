from typing import Any
from collections.abc import Generator
import json

import httpx
from openai import OpenAI
from openai.types.responses import Response as OAIResponse
from openai.types.responses.response_stream_event import ResponseStreamEvent

from vnag.gateway import BaseGateway
from vnag.object import FinishReason, Request, Response, Delta, Usage, Message, ToolCall
from vnag.constant import Role


class OpenaiGateway(BaseGateway):
    """
    OpenAI Responses API 网关

    调用 OpenAI /v1/responses 端点，支持纯文本、function calling、
    流式输出及 reasoning summary 透传。
    """

    default_name: str = "OpenAI"

    default_setting: dict = {
        "base_url": "",
        "api_key": "",
        "proxy": "",
    }

    def __init__(self, gateway_name: str = "") -> None:
        """构造函数"""
        if not gateway_name:
            gateway_name = self.default_name
        self.gateway_name = gateway_name

        self.client: OpenAI | None = None

    def _convert_input(
        self, messages: list[Message]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        将内部 Message 列表转换为 Responses API 的 input 列表和 instructions。

        返回 (input_items, instructions)。
        """
        input_items: list[dict[str, Any]] = []
        instructions: str | None = None

        for msg in messages:
            if msg.role == Role.SYSTEM:
                instructions = msg.content
                continue

            if msg.tool_results:
                for tr in msg.tool_results:
                    input_items.append({
                        "type": "function_call_output",
                        "call_id": tr.id,
                        "output": tr.content,
                    })
                continue

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    input_items.append({
                        "type": "function_call",
                        "call_id": tc.id,
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    })
                if msg.content:
                    input_items.append({
                        "role": msg.role.value,
                        "content": msg.content,
                    })
                continue

            input_items.append({
                "role": msg.role.value,
                "content": msg.content,
            })

        return input_items, instructions

    def _build_tools(self, request: Request) -> list[dict[str, Any]]:
        """将 ToolSchema 列表转换为 Responses API 工具格式。"""
        tools: list[dict[str, Any]] = []
        for ts in request.tool_schemas:
            tools.append({
                "type": "function",
                "name": ts.name,
                "description": ts.description,
                "parameters": ts.parameters,
            })
        return tools

    def _parse_response(self, oai_resp: OAIResponse) -> Response:
        """将 OAI Responses API 返回值解析为内部 Response 对象。"""
        content: str = ""
        thinking: str = ""
        tool_calls: list[ToolCall] = []

        for item in oai_resp.output:
            if item.type == "message":
                for part in item.content:
                    if part.type == "output_text":
                        content += part.text

            elif item.type == "function_call":
                try:
                    arguments: dict[str, Any] = json.loads(item.arguments)
                except json.JSONDecodeError:
                    arguments = {}
                tool_calls.append(ToolCall(
                    id=item.call_id,
                    name=item.name,
                    arguments=arguments,
                ))

            elif item.type == "reasoning":
                parts: list[str] = [s.text for s in item.summary]
                if parts:
                    thinking = "\n".join(parts)

        # 确定 finish_reason
        status = oai_resp.status or ""
        if status == "incomplete":
            finish_reason: FinishReason = FinishReason.LENGTH
        elif tool_calls:
            finish_reason = FinishReason.TOOL_CALLS
        elif status == "completed":
            finish_reason = FinishReason.STOP
        else:
            finish_reason = FinishReason.UNKNOWN

        usage: Usage = Usage()
        if oai_resp.usage:
            usage.input_tokens = oai_resp.usage.input_tokens
            usage.output_tokens = oai_resp.usage.output_tokens

        message = Message(
            role=Role.ASSISTANT,
            content=content,
            thinking=thinking,
            tool_calls=tool_calls,
        )

        return Response(
            id=oai_resp.id,
            content=content,
            thinking=thinking,
            usage=usage,
            finish_reason=finish_reason,
            message=message,
        )

    def init(self, setting: dict[str, Any]) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""
        base_url: str = setting.get("base_url", "")
        api_key: str = setting.get("api_key", "")
        proxy: str = setting.get("proxy", "")

        if not base_url or not api_key:
            self.write_log("配置不完整，请检查以下配置项：")
            if not base_url:
                self.write_log("  - base_url: API地址未设置")
            if not api_key:
                self.write_log("  - api_key: API密钥未设置")
            return False

        http_client: httpx.Client | None = httpx.Client(proxy=proxy) if proxy else None

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
        )

        return True

    def invoke(self, request: Request) -> Response:
        """常规调用接口：发送消息并一次性返回结果。"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return Response(id="", content="", usage=Usage())

        input_items, instructions = self._convert_input(request.messages)

        create_params: dict[str, Any] = {
            "model": request.model,
            "input": input_items,
        }

        if instructions:
            create_params["instructions"] = instructions

        if request.temperature is not None:
            create_params["temperature"] = request.temperature

        if request.max_tokens is not None:
            create_params["max_output_tokens"] = request.max_tokens

        if request.tool_schemas:
            create_params["tools"] = self._build_tools(request)

        oai_resp: OAIResponse = self.client.responses.create(**create_params)

        return self._parse_response(oai_resp)

    def stream(self, request: Request) -> Generator[Delta, None, None]:
        """流式调用接口。"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return

        input_items, instructions = self._convert_input(request.messages)

        create_params: dict[str, Any] = {
            "model": request.model,
            "input": input_items,
            "stream": True,
        }

        if instructions:
            create_params["instructions"] = instructions

        if request.temperature is not None:
            create_params["temperature"] = request.temperature

        if request.max_tokens is not None:
            create_params["max_output_tokens"] = request.max_tokens

        if request.tool_schemas:
            create_params["tools"] = self._build_tools(request)

        response_id: str = ""

        with self.client.responses.create(**create_params) as stream:
            for event in stream:  # type: ResponseStreamEvent
                etype: str = event.type

                if etype == "response.created":
                    response_id = event.response.id
                    continue

                if not response_id and hasattr(event, "item_id"):
                    pass

                if etype == "response.output_text.delta":
                    delta: Delta = Delta(id=response_id, content=event.delta)
                    yield delta

                elif etype == "response.reasoning_summary_text.delta":
                    delta = Delta(id=response_id, thinking=event.delta)
                    yield delta

                elif etype == "response.output_item.done":
                    item = event.item
                    if item.type == "function_call":
                        try:
                            arguments: dict[str, Any] = json.loads(item.arguments)
                        except json.JSONDecodeError:
                            arguments = {}
                        tc = ToolCall(
                            id=item.call_id,
                            name=item.name,
                            arguments=arguments,
                        )
                        delta = Delta(
                            id=response_id,
                            tool_calls=[tc],
                            finish_reason=FinishReason.TOOL_CALLS,
                        )
                        yield delta

                elif etype == "response.completed":
                    oai_resp: OAIResponse = event.response
                    status: str = oai_resp.status or ""
                    has_function_calls: bool = any(
                        item.type == "function_call" for item in oai_resp.output
                    )

                    if status == "incomplete":
                        finish_reason: FinishReason = FinishReason.LENGTH
                    elif has_function_calls:
                        finish_reason = FinishReason.TOOL_CALLS
                    else:
                        finish_reason = FinishReason.STOP

                    usage: Usage = Usage()
                    if oai_resp.usage:
                        usage.input_tokens = oai_resp.usage.input_tokens
                        usage.output_tokens = oai_resp.usage.output_tokens

                    delta = Delta(
                        id=response_id,
                        finish_reason=finish_reason,
                        usage=usage,
                    )
                    yield delta

    def list_models(self) -> list[str]:
        """查询可用模型列表"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return []

        models = self.client.models.list()
        return sorted([model.id for model in models])
