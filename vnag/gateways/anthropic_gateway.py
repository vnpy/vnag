from typing import Any
import json
from collections.abc import Generator

from anthropic import Anthropic, Stream
from anthropic.types import Message as AnthropicMessage, MessageStreamEvent

from vnag.constant import FinishReason
from vnag.gateway import BaseGateway
from vnag.object import Request, Response, Delta, Usage


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

    def invoke(
        self,
        request: Request,
        use_tools: bool = False,
        tool_schemas: list[dict[str, Any]] | None = None,
        tool_registry: dict[str, Any] | None = None,
    ) -> Response:
        """常规调用：一次性返回文本。
        规则：循环判定 tool_use，直到没有为止；最后一轮直接返回，不再追加请求。
        """
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return Response(id="", content="LLM客户端未初始化", usage=Usage())

        if not request.max_tokens:
            self.write_log("max_tokens 为 Anthropic 必传参数")
            return Response(id="", content="max_tokens 不能为空", usage=Usage())

        messages = [msg.model_dump() for msg in request.messages]
        # 提取首条 system 提示并作为单独参数传入（保留原有写法）
        system_prompt = ""
        if messages and messages[0]["role"] == "system":
            system_prompt = messages.pop(0)["content"]

        if use_tools:
            # 工具模式：循环处理所有 tool_use，直到模型不再请求工具
            while True:
                resp: AnthropicMessage = self.client.messages.create(
                    model=request.model,
                    messages=messages,
                    max_tokens=request.max_tokens,
                    system=system_prompt,
                    temperature=request.temperature,
                    tools=tool_schemas,
                )
                # 统一提取文本块为 assistant_content（本轮模型的纯文本回答）
                assistant_content: str = ""

                # 遍历文本块
                if resp.content is not None:
                    for block in resp.content:
                        # 检查是否为 text 块
                        if hasattr(block, "type") and block.type == "text":
                            assistant_content += block.text

                # 收集本轮模型返回的 tool_use 块（对象块）
                tool_uses: list = []
                if resp.content is not None:
                    for block in resp.content:
                        if hasattr(block, "type") and block.type == "tool_use":
                            tool_uses.append(block)

                # 若没有工具调用，则本轮即最终答案，不再追加请求
                if not tool_uses:

                    usage: Usage = Usage(
                        input_tokens=resp.usage.input_tokens,
                        output_tokens=resp.usage.output_tokens,
                    )
                    return Response(id=resp.id, content=assistant_content, usage=usage)

                # 将本轮 tool_use 合并为一条 assistant(tool_use) 消息并插入对话
                # 说明：Anthropic 协议要求先出现 assistant(tool_use)，随后才出现 user(tool_result)
                assistant_tool_content: list[dict] = []
                for tu in tool_uses:
                    assistant_tool_content.append(
                        {
                            "type": "tool_use",
                            "id": getattr(tu, "id", ""),
                            "name": getattr(tu, "name", ""),
                            "input": getattr(tu, "input", {}),
                        }
                    )
                if assistant_tool_content:
                    messages.append({"role": "assistant", "content": assistant_tool_content})

                # 逐个执行工具并回填 user(tool_result)，然后继续下一轮
                for tool_use in tool_uses:
                    function_name: str = getattr(tool_use, "name", "")
                    function_args: dict[str, Any] = getattr(tool_use, "input", {})
                    self.write_log(f"[TOOLS] name={function_name}")
                    tool_result: dict[str, Any] = tool_registry[function_name](function_args)  # type: ignore[index]

                    # 追加工具结果消息
                    append_tool_result(messages, getattr(tool_use, "id", ""), tool_result)
        else:
            # 非工具模式：一次性生成后返回
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

            # 统一提取文本块为 assistant_content
            assistant_content: str = ""
            if response.content is not None:
                for block in response.content:
                    if hasattr(block, "type") and block.type == "text":
                        assistant_content += block.text

        return Response(
            id=response.id,
            content=assistant_content,
            usage=usage,
        )

    def stream(
        self,
        request: Request,
        use_tools: bool = False,
        tool_schemas: list[dict[str, Any]] | None = None,
        tool_registry: dict[str, Any] | None = None,
    ) -> Generator[Delta, None, None]:
        """流式调用：
        - 先用非流式循环判定/执行工具（便于拿到完整 tool_use）
        - 若全程未使用工具：不追加请求，直接一次性输出本轮文本并结束
        - 若使用过工具：将文本并入上下文后，发起“最终流式生成”，逐 token 输出
        """
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

        # 若开启工具，先做一次同步工具轮询（避免流式拆块处理 tool_use 复杂度）
        if use_tools:
            while True:
                resp: AnthropicMessage = self.client.messages.create(
                    model=request.model,
                    messages=messages,
                    max_tokens=request.max_tokens,
                    system=system_prompt,
                    temperature=request.temperature,
                    tools=tool_schemas,
                )

                # 统一提取文本块为 assistant_content
                assistant_content: str = ""
                if resp.content is not None:
                    for block in resp.content:
                        if hasattr(block, "type") and block.type == "text":
                            assistant_content += block.text

                # 收集 tool_use 块（对象块）
                tool_uses: list = []
                if resp.content is not None:
                    for block in resp.content:
                        if hasattr(block, "type") and block.type == "tool_use":
                            tool_uses.append(block)

                if not tool_uses:
                    # 未使用工具：直接输出本轮文本并结束（不追加请求）
                    if assistant_content:
                        yield Delta(id=resp.id, content=assistant_content)

                    end_delta = Delta(id=resp.id)
                    end_delta.finish_reason = FinishReason.STOP
                    end_delta.usage = Usage(
                        input_tokens=resp.usage.input_tokens,
                        output_tokens=resp.usage.output_tokens,
                    )
                    yield end_delta

                    return

                # 按 Anthropic 规范：先把本轮的 tool_use 块作为一条 assistant 消息加入对话
                assistant_tool_content: list[dict] = []
                for tu in tool_uses:
                    assistant_tool_content.append(
                        {
                            "type": "tool_use",
                            "id": getattr(tu, "id", ""),
                            "name": getattr(tu, "name", ""),
                            "input": getattr(tu, "input", {}),
                        }
                    )
                if assistant_tool_content:
                    messages.append({"role": "assistant", "content": assistant_tool_content})

                # 逐个执行工具并回填 tool_result
                for tool_use in tool_uses:
                    function_name: str = getattr(tool_use, "name", "")
                    function_args: dict[str, Any] = getattr(tool_use, "input", {})
                    self.write_log(f"[TOOLS] name={function_name}")
                    tool_result: dict[str, Any] = tool_registry[function_name](function_args)  # type: ignore[index]

                    # 追加工具结果消息
                    append_tool_result(messages, getattr(tool_use, "id", ""), tool_result)

                # 执行过工具后，跳出循环，进入最终流式输出
                break

        # 工具轮询结束后，进入最终流式输出
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

        # 遍历流式事件
        for stream_event in stream:

            # 检查消息开始事件
            if stream_event.type == "message_start":
                response_id = stream_event.message.id
                input_tokens = stream_event.message.usage.input_tokens

            # 检查内容增量
            elif (
                stream_event.type == "content_block_delta"
                and stream_event.delta.type == "text_delta"
            ):
                yield Delta(
                    id=response_id,
                    content=stream_event.delta.text,
                )

            # 检查消息结束事件
            elif stream_event.type == "message_delta":
                finish_reason: FinishReason = ANTHROPIC_FINISH_REASON_MAP.get(
                    stream_event.delta.stop_reason, FinishReason.UNKNOWN
                )

                # 追加用量信息
                yield Delta(
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


def append_tool_result(messages: list[dict], tool_use_id: str, result: dict[str, Any]) -> None:
    """追加 Anthropic 规范的工具结果消息（role=user, content 中 type=tool_result）。"""
    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            ],
        }
    )
