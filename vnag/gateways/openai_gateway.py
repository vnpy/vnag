from typing import Any
import json
from collections.abc import Generator

from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.model import Model
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

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

    def invoke(
        self,
        request: Request,
        use_tools: bool = False,
        tool_schemas: list[dict[str, Any]] | None = None,
        tool_registry: dict[str, Any] | None = None,
    ) -> Response:
        """常规调用接口：将已准备好的消息发送给模型并一次性产出文本。"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return Response(id="", content="", usage=Usage())

        messages: list = [msg.model_dump() for msg in request.messages]

        if not use_tools:
            response: ChatCompletion = self.client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            usage = Usage()
            if response.usage:
                usage.input_tokens = response.usage.prompt_tokens
                usage.output_tokens = response.usage.completion_tokens

            return Response(
                id=response.id,
                content=response.choices[0].message.content or "",
                usage=usage,
            )

        # 工具模式：循环直到“无工具请求”为止
        # 规则（与官方一致）：
        # - 若本轮无 tool_calls：本轮即最终答案，不再追加请求
        # - 若本轮有 tool_calls：先把 assistant(tool_calls) 追加到消息 → 逐个执行工具并回填 role=tool → 继续下一轮
        while True:
            resp: ChatCompletion = self.client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=tool_schemas,
                tool_choice="auto",      # 自动选择工具
            )

            # 获取第一条选择
            choice: Choice = resp.choices[0]
            tool_calls: list[ChatCompletionMessageToolCall] = []
            if choice.message.tool_calls is not None:
                tool_calls = choice.message.tool_calls
            assistant_content: str = choice.message.content or ""

            # 若没有工具调用，则本轮即最终答案，不再追加请求
            if not tool_calls:

                usage = Usage()
                if resp.usage:
                    usage.input_tokens = resp.usage.prompt_tokens
                    usage.output_tokens = resp.usage.completion_tokens

                return Response(
                    id=resp.id,
                    content=assistant_content,
                    usage=usage,
                )

            # 先把包含 tool_calls 的 assistant 消息追加到消息队列
            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
            messages.append(assistant_message)

            # 逐个执行工具并追加对应的 tool 消息（本轮可能多个工具）
            for tc in tool_calls:
                name: str = tc.function.name
                args_raw: str = tc.function.arguments
                args: dict[str, Any] = json.loads(args_raw)
                # 仅打印工具名，避免冗余日志
                self.write_log(f"[TOOLS] name={name}")
                result: dict[str, Any] = tool_registry[name](args)  # type: ignore[index]

                # 追加工具结果消息
                append_tool_result(messages, tc.id, result)

    def stream(
        self,
        request: Request,
        use_tools: bool = False,
        tool_schemas: list[dict[str, Any]] | None = None,
        tool_registry: dict[str, Any] | None = None,
    ) -> Generator[Delta, None, None]:
        """流式调用接口"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return

        # 准备消息
        messages: list[dict] = [msg.model_dump() for msg in request.messages]

        # 工具判定阶段（非流式轮询）：
        # - 便于完整拿到 tool_calls 并逐一执行；
        # - tools_used=False 表示全程未触发工具（此时不再追加请求，直接一次性输出本轮文本）。
        if use_tools:
            tools_used: bool = False
            while True:
                resp: ChatCompletion = self.client.chat.completions.create(
                    model=request.model,
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    tools=tool_schemas,
                    tool_choice="auto",
                )

                choice: ChatCompletionChoice = resp.choices[0]
                tool_calls: list[ToolCall] = []
                if choice.message.tool_calls is not None:
                    tool_calls = choice.message.tool_calls

                assistant_content: str = choice.message.content or ""

                if not tool_calls:
                    # 若未使用过工具：不追加请求，直接一次性输出文本后结束
                    if not tools_used:

                        if assistant_content:
                            yield Delta(id=resp.id, content=assistant_content)

                        end_delta = Delta(id=resp.id)
                        end_delta.finish_reason = FinishReason.STOP
                        if resp.usage:
                            end_delta.usage = Usage(
                                input_tokens=resp.usage.prompt_tokens,
                                output_tokens=resp.usage.completion_tokens,
                            )
                        yield end_delta

                        return

                    # 若使用过工具：将本轮文本（若有）并入上下文，跳出循环进入“最终流式”
                    if assistant_content:
                        messages.append({"role": "assistant", "content": assistant_content})
                    break

                # 先追加包含 tool_calls 的 assistant 消息
                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": assistant_content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
                messages.append(assistant_message)

                # 再逐个执行工具并回填 tool 消息
                tools_used = True
                for tc in tool_calls:
                    name: str = tc.function.name
                    args_raw: str = tc.function.arguments
                    args: dict[str, Any] = json.loads(args_raw)
                    self.write_log(f"[TOOLS] name={name}")
                    result: dict[str, Any] = tool_registry[name](args)  # type: ignore[index]

                    append_tool_result(messages, tc.id, result)

        # 若判定阶段使用过工具：此处发起“最终流式输出”。
        # 若未使用工具：上面已直接输出并 return，不会走到这里。
        stream: Stream[ChatCompletionChunk] = self.client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
        )

        response_id: str = ""
        # 遍历流式事件
        for chuck in stream:

            # 检查消息开始事件
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


def append_tool_result(messages: list[dict], tool_call_id: str, result: dict[str, Any]) -> None:
    """追加 OpenAI 规范的工具结果消息（role=tool）。"""
    messages.append(
        {
            "role": "tool",
            "content": json.dumps(result, ensure_ascii=False),
            "tool_call_id": tool_call_id,
        }
    )
