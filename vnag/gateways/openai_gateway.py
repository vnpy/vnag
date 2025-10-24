from typing import Any
from collections.abc import Generator
import json

from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from vnag.gateway import BaseGateway
from vnag.object import FinishReason, Request, Response, Delta, Usage, Message, ToolCall
from vnag.object import Role


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

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """
        将内部 Message 格式转换为 OpenAI API 格式

        内部格式支持 tool_results，需要拆分为多条 tool 角色消息
        """
        openai_messages: list[dict[str, Any]] = []

        for msg in messages:
            # 处理工具结果：拆分为多条 tool 消息
            if msg.tool_results:
                for tool_result in msg.tool_results:
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_result.id,
                        "content": tool_result.content
                    })

            # 处理普通消息或带 tool_calls 的消息
            else:
                message_dict: dict[str, Any] = {"role": msg.role.value}

                if msg.content:
                    message_dict["content"] = msg.content

                if msg.tool_calls:
                    # 转换 tool_calls 为 OpenAI 格式
                    message_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments)
                            }
                        }
                        for tc in msg.tool_calls
                    ]

                openai_messages.append(message_dict)

        return openai_messages

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

        # 转换消息格式
        openai_messages: list[dict[str, Any]] = self._convert_messages(request.messages)

        # 准备请求参数
        create_params: dict[str, Any] = {
            "model": request.model,
            "messages": openai_messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        # 添加工具定义（如果有）
        if request.tools_schemas:
            create_params["tools"] = [t.get_schema() for t in request.tools_schemas]

        response: ChatCompletion = self.client.chat.completions.create(**create_params)

        usage: Usage = Usage()
        if response.usage:
            usage.input_tokens = response.usage.prompt_tokens
            usage.output_tokens = response.usage.completion_tokens

        choice = response.choices[0]
        finish_reason: FinishReason = FINISH_REASON_MAP.get(
            choice.finish_reason, FinishReason.UNKNOWN
        )

        # 提取工具调用
        tool_calls: list[ToolCall] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    if hasattr(tc, "function"):
                        arguments: dict[str, Any] = json.loads(tc.function.arguments)
                        tool_calls.append(ToolCall(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=arguments
                        ))
                except json.JSONDecodeError:
                    pass

        # 构建返回的消息对象
        message = Message(
            role=Role.ASSISTANT,
            content=choice.message.content or "",
            tool_calls=tool_calls
        )

        return Response(
            id=response.id,
            content=choice.message.content or "",
            usage=usage,
            finish_reason=finish_reason,
            message=message
        )

    def stream(self, request: Request) -> Generator[Delta, None, None]:
        """流式调用接口"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return

        # 转换消息格式
        openai_messages: list[dict[str, Any]] = self._convert_messages(request.messages)

        # 准备请求参数
        create_params: dict[str, Any] = {
            "model": request.model,
            "messages": openai_messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }

        # 添加工具定义（如果有）
        if request.tools_schemas:
            create_params["tools"] = [t.get_schema() for t in request.tools_schemas]

        stream: Stream[ChatCompletionChunk] = self.client.chat.completions.create(**create_params)

        response_id: str = ""
        # 用于累积 tool_calls（OpenAI 流式返回时可能分多次）
        accumulated_tool_calls: dict[int, dict[str, Any]] = {}

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

            # 检查 tool_calls 增量
            if chuck.choices[0].delta.tool_calls:
                for tc_chunk in chuck.choices[0].delta.tool_calls:
                    idx: int = tc_chunk.index

                    # 初始化或更新累积的 tool_call
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": "",
                            "name": "",
                            "arguments": ""
                        }

                    if tc_chunk.id:
                        accumulated_tool_calls[idx]["id"] = tc_chunk.id

                    if tc_chunk.function:
                        if tc_chunk.function.name:
                            accumulated_tool_calls[idx]["name"] = tc_chunk.function.name
                        if tc_chunk.function.arguments:
                            accumulated_tool_calls[idx]["arguments"] += tc_chunk.function.arguments

            # 检查结束原因
            openai_finish_reason = chuck.choices[0].finish_reason
            if openai_finish_reason:
                vnag_finish_reason: FinishReason = FINISH_REASON_MAP.get(
                    openai_finish_reason, FinishReason.UNKNOWN
                )
                delta.finish_reason = vnag_finish_reason
                should_yield = True

                # 如果是 tool_calls 结束，转换累积的 tool_calls
                if vnag_finish_reason == FinishReason.TOOL_CALLS and accumulated_tool_calls:
                    tool_calls: list[ToolCall] = []
                    for tc_data in accumulated_tool_calls.values():
                        try:
                            arguments: dict[str, Any] = json.loads(tc_data["arguments"])
                        except json.JSONDecodeError:
                            arguments = {}

                        tool_calls.append(ToolCall(
                            id=tc_data["id"],
                            name=tc_data["name"],
                            arguments=arguments
                        ))

                    delta.calls = tool_calls

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

        models = self.client.models.list()
        return sorted([model.id for model in models])
