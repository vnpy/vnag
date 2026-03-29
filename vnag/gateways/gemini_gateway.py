import base64
import json
from typing import Any
from uuid import uuid4
from collections.abc import Generator

from google import genai
from google.genai import types

from vnag.constant import FinishReason, Role
from vnag.gateway import BaseGateway
from vnag.object import Request, Response, Delta, Usage, Message, ToolCall


GEMINI_STATIC_MODELS: list[str] = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
]

GEMINI_FINISH_REASON_MAP: dict[str, FinishReason] = {
    "STOP": FinishReason.STOP,
    "MAX_TOKENS": FinishReason.LENGTH,
    "SAFETY": FinishReason.STOP,
    "RECITATION": FinishReason.STOP,
}

GEMINI_MODEL_EXCLUDE_KEYWORDS: list[str] = [
    "embedding",
    "imagen",
    "veo",
    "aqa",
    "bisheng",
]


class GeminiGateway(BaseGateway):
    """连接 Google AI Studio Gemini API 的网关，提供统一接口"""

    default_name: str = "Gemini"

    default_setting: dict = {
        "api_key": "",
        "proxy": "",
    }

    def __init__(self, gateway_name: str = "") -> None:
        """构造函数"""
        if not gateway_name:
            gateway_name = self.default_name
        self.gateway_name = gateway_name
        self.client: genai.Client | None = None

    def _convert_messages(
        self, messages: list[Message]
    ) -> tuple[str, list[Any]]:
        """
        将内部格式转换为 Gemini 格式

        返回 (system_instruction, contents)。
        system 消息合并为单个字符串；其余转换为 Content 列表。
        """
        system_parts: list[str] = []
        contents: list[Any] = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                if msg.content:
                    system_parts.append(msg.content)
                continue

            # 工具结果：转为 user 角色的 function_response parts
            if msg.tool_results:
                parts: list[types.Part] = []
                for tr in msg.tool_results:
                    response_data: dict[str, Any] = (
                        {"error": tr.content}
                        if tr.is_error
                        else {"result": tr.content}
                    )
                    parts.append(types.Part.from_function_response(
                        name=tr.name,
                        response=response_data,
                    ))
                contents.append(types.Content(role="user", parts=parts))
                continue

            # assistant 消息：两级恢复策略
            if msg.role == Role.ASSISTANT:
                parts = self._restore_assistant_parts(msg)
                if parts:
                    contents.append(types.Content(
                        role="model", parts=parts
                    ))
                continue

            # user 消息
            if msg.content:
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=msg.content)],
                ))

        system_instruction: str = "\n\n".join(system_parts)
        return system_instruction, contents

    def _restore_assistant_parts(
        self, msg: Message
    ) -> list[types.Part]:
        """
        从 Message 恢复 assistant 的 Gemini parts

        优先从 msg.reasoning 中恢复结构化 parts；
        若无则降级从 content / tool_calls 恢复。
        """
        # 检查是否存在 Gemini 结构化 parts
        gemini_items: list[dict[str, Any]] = [
            item for item in msg.reasoning
            if item.get("type") == "gemini_part"
        ]

        if gemini_items:
            gemini_items.sort(key=lambda x: x.get("index", 0))
            parts: list[types.Part] = []

            for item in gemini_items:
                part_type: str = item.get("part_type", "")

                if part_type == "text":
                    text: str = item.get("text", "")
                    if text:
                        part = types.Part.from_text(text=text)
                        sig_str: str = item.get("thought_signature", "")
                        if sig_str:
                            part.thought_signature = base64.b64decode(
                                sig_str
                            )
                        parts.append(part)

                elif part_type == "function_call":
                    args: dict[str, Any] = item.get("arguments", {})
                    part = types.Part.from_function_call(
                        name=item.get("name", ""),
                        args=args,
                    )
                    if item.get("id") and part.function_call:
                        part.function_call.id = item["id"]
                    sig_str = item.get("thought_signature", "")
                    if sig_str:
                        part.thought_signature = base64.b64decode(sig_str)
                    parts.append(part)

            return parts

        # 降级恢复
        parts = []
        if msg.content:
            parts.append(types.Part.from_text(text=msg.content))

        for tc in msg.tool_calls:
            part = types.Part.from_function_call(
                name=tc.name,
                args=tc.arguments,
            )
            if part.function_call:
                part.function_call.id = tc.id
            parts.append(part)

        return parts

    def _convert_tools(
        self, tool_schemas: list[Any]
    ) -> list[types.Tool] | None:
        """将内部工具 schema 转换为 Gemini Tool 定义"""
        if not tool_schemas:
            return None

        declarations: list[types.FunctionDeclaration] = []
        for schema in tool_schemas:
            declarations.append(types.FunctionDeclaration(
                name=schema.name,
                description=schema.description,
                parameters=schema.parameters,
            ))

        return [types.Tool(function_declarations=declarations)]

    def _build_config(
        self,
        request: Request,
        system_instruction: str,
        tools: list[types.Tool] | None,
        enable_thinking: bool = True,
    ) -> types.GenerateContentConfig:
        """构造 GenerateContentConfig"""
        config_params: dict[str, Any] = {}

        if system_instruction:
            config_params["system_instruction"] = system_instruction
        if request.temperature is not None:
            config_params["temperature"] = request.temperature
        if request.top_p is not None:
            config_params["top_p"] = request.top_p
        if request.max_tokens:
            config_params["max_output_tokens"] = request.max_tokens

        if tools:
            config_params["tools"] = tools
            config_params["automatic_function_calling"] = (
                types.AutomaticFunctionCallingConfig(disable=True)
            )

        if enable_thinking:
            config_params["thinking_config"] = types.ThinkingConfig(
                include_thoughts=True
            )

        return types.GenerateContentConfig(**config_params)

    def _extract_response_parts(
        self, response: types.GenerateContentResponse
    ) -> tuple[
        str, str, list[dict[str, Any]], list[ToolCall], FinishReason, Usage
    ]:
        """
        从非流式响应中提取结构化数据

        返回 (content, thinking, reasoning, tool_calls, finish_reason, usage)。
        """
        content: str = ""
        thinking: str = ""
        reasoning: list[dict[str, Any]] = []
        tool_calls: list[ToolCall] = []

        candidate: types.Candidate | None = (
            response.candidates[0] if response.candidates else None
        )

        if candidate and candidate.content and candidate.content.parts:
            for idx, part in enumerate(candidate.content.parts):
                item: dict[str, Any] = {
                    "index": idx,
                    "type": "gemini_part",
                }

                # 提取 thought_signature
                sig: bytes | None = getattr(
                    part, "thought_signature", None
                )
                if sig:
                    item["thought_signature"] = base64.b64encode(
                        sig
                    ).decode("ascii")

                if part.function_call:
                    fc = part.function_call
                    fc_id: str = getattr(fc, "id", "") or ""
                    args: dict[str, Any] = dict(fc.args) if fc.args else {}
                    args_json: str = json.dumps(args, ensure_ascii=False)

                    item["part_type"] = "function_call"
                    item["id"] = fc_id
                    item["name"] = fc.name or ""
                    item["arguments"] = args
                    item["data"] = args_json

                    tool_calls.append(ToolCall(
                        id=fc_id,
                        name=fc.name or "",
                        arguments=args,
                    ))
                elif part.text is not None:
                    # 判断是否为 thought 文本
                    is_thought: bool = getattr(part, "thought", False)
                    if is_thought:
                        thinking += part.text
                        item["part_type"] = "thought"
                        item["text"] = part.text
                    else:
                        content += part.text
                        item["part_type"] = "text"
                        item["text"] = part.text

                reasoning.append(item)

        # 结束原因
        finish_reason: FinishReason = FinishReason.UNKNOWN
        if tool_calls:
            finish_reason = FinishReason.TOOL_CALLS
        elif candidate:
            raw_reason: str = str(
                candidate.finish_reason or ""
            ).upper()
            finish_reason = GEMINI_FINISH_REASON_MAP.get(
                raw_reason, FinishReason.UNKNOWN
            )

        # usage
        usage: Usage = Usage()
        if response.usage_metadata:
            um = response.usage_metadata
            usage = Usage(
                input_tokens=um.prompt_token_count or 0,
                output_tokens=um.candidates_token_count or 0,
            )

        return content, thinking, reasoning, tool_calls, finish_reason, usage

    def init(self, setting: dict[str, Any]) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""
        api_key: str = setting.get("api_key", "")
        proxy: str = setting.get("proxy", "")

        if not api_key:
            self.write_log("配置不完整，请检查以下配置项：")
            self.write_log("  - api_key: API密钥未设置")
            return False

        try:
            if proxy:
                http_options = types.HttpOptions(
                    api_version="v1beta",
                    client_args={"proxy": proxy},
                    async_client_args={"proxy": proxy},
                )
                self.client = genai.Client(
                    api_key=api_key,
                    http_options=http_options,
                )
            else:
                self.client = genai.Client(
                    api_key=api_key,
                    http_options=types.HttpOptions(
                        api_version="v1beta",
                    ),
                )
        except Exception as e:
            self.write_log(f"创建 Gemini 客户端失败: {e}")
            return False

        return True

    def invoke(self, request: Request) -> Response:
        """常规调用接口：将已准备好的消息发送给模型并一次性产出文本。"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return Response(id="", content="", usage=Usage())

        system_instruction, contents = self._convert_messages(
            request.messages
        )
        tools: list[types.Tool] | None = self._convert_tools(
            request.tool_schemas
        )
        config: types.GenerateContentConfig = self._build_config(
            request, system_instruction, tools, enable_thinking=True
        )

        try:
            response: types.GenerateContentResponse = (
                self.client.models.generate_content(
                    model=request.model,
                    contents=contents,
                    config=config,
                )
            )
        except Exception:
            # 部分模型不支持 thinking，去掉后重试
            config = self._build_config(
                request, system_instruction, tools, enable_thinking=False
            )
            response = self.client.models.generate_content(
                model=request.model,
                contents=contents,
                config=config,
            )

        (
            content, thinking, reasoning,
            tool_calls, finish_reason, usage
        ) = self._extract_response_parts(response)

        response_id: str = str(uuid4())

        message = Message(
            role=Role.ASSISTANT,
            content=content,
            thinking=thinking,
            reasoning=reasoning,
            tool_calls=tool_calls,
        )

        return Response(
            id=response_id,
            content=content,
            thinking=thinking,
            usage=usage,
            finish_reason=finish_reason,
            message=message,
        )

    def stream(self, request: Request) -> Generator[Delta, None, None]:
        """流式调用接口"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return

        system_instruction, contents = self._convert_messages(
            request.messages
        )
        tools: list[types.Tool] | None = self._convert_tools(
            request.tool_schemas
        )
        config: types.GenerateContentConfig = self._build_config(
            request, system_instruction, tools, enable_thinking=True
        )

        try:
            stream_response = self.client.models.generate_content_stream(
                model=request.model,
                contents=contents,
                config=config,
            )
            # 尝试获取第一个 chunk 来确认 thinking 是否可用
            first_chunk: types.GenerateContentResponse | None = None
            try:
                first_chunk = next(iter(stream_response))
            except StopIteration:
                return
            except Exception:
                # thinking 不支持，去掉后重试
                config = self._build_config(
                    request, system_instruction, tools,
                    enable_thinking=False,
                )
                stream_response = (
                    self.client.models.generate_content_stream(
                        model=request.model,
                        contents=contents,
                        config=config,
                    )
                )
                first_chunk = None
        except Exception:
            # thinking 不支持，去掉后重试
            config = self._build_config(
                request, system_instruction, tools, enable_thinking=False
            )
            stream_response = (
                self.client.models.generate_content_stream(
                    model=request.model,
                    contents=contents,
                    config=config,
                )
            )
            first_chunk = None

        response_id: str = str(uuid4())
        accumulated_tool_calls: dict[int, dict[str, Any]] = {}
        seen_function_call: bool = False

        def _process_chunk(
            chunk: types.GenerateContentResponse,
        ) -> Generator[Delta, None, None]:
            nonlocal seen_function_call

            candidate: types.Candidate | None = (
                chunk.candidates[0] if chunk.candidates else None
            )
            if not candidate or not candidate.content:
                # 仅 usage 的尾块
                if chunk.usage_metadata:
                    um = chunk.usage_metadata
                    yield Delta(
                        id=response_id,
                        usage=Usage(
                            input_tokens=um.prompt_token_count or 0,
                            output_tokens=um.candidates_token_count or 0,
                        ),
                    )
                return

            parts = candidate.content.parts or []
            for idx, part in enumerate(parts):
                # thought_signature 序列化
                sig: bytes | None = getattr(
                    part, "thought_signature", None
                )
                sig_b64: str = ""
                if sig:
                    sig_b64 = base64.b64encode(sig).decode("ascii")

                if part.function_call:
                    seen_function_call = True
                    fc = part.function_call
                    fc_id: str = getattr(fc, "id", "") or ""
                    fc_name: str = fc.name or ""
                    fc_args_str: str = ""

                    if fc.args:
                        fc_args_str = json.dumps(
                            dict(fc.args), ensure_ascii=False
                        )

                    # 累积工具调用
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": fc_id,
                            "name": fc_name,
                            "data": fc_args_str,
                        }
                    else:
                        if fc_id:
                            accumulated_tool_calls[idx]["id"] = fc_id
                        if fc_name:
                            accumulated_tool_calls[idx]["name"] = fc_name
                        accumulated_tool_calls[idx]["data"] += fc_args_str

                    # 发送 reasoning 增量
                    reasoning_item: dict[str, Any] = {
                        "index": idx,
                        "type": "gemini_part",
                        "part_type": "function_call",
                        "id": fc_id,
                        "name": fc_name,
                        "data": fc_args_str,
                    }
                    if sig_b64:
                        reasoning_item["thought_signature"] = sig_b64

                    yield Delta(
                        id=response_id,
                        reasoning=[reasoning_item],
                    )

                elif part.text is not None:
                    is_thought: bool = getattr(part, "thought", False)

                    reasoning_item = {
                        "index": idx,
                        "type": "gemini_part",
                        "part_type": "thought" if is_thought else "text",
                        "text": part.text,
                    }
                    if sig_b64:
                        reasoning_item["thought_signature"] = sig_b64

                    if is_thought:
                        yield Delta(
                            id=response_id,
                            thinking=part.text,
                            reasoning=[reasoning_item],
                        )
                    else:
                        yield Delta(
                            id=response_id,
                            content=part.text,
                            reasoning=[reasoning_item],
                        )

            # usage
            if chunk.usage_metadata:
                um = chunk.usage_metadata
                yield Delta(
                    id=response_id,
                    usage=Usage(
                        input_tokens=um.prompt_token_count or 0,
                        output_tokens=um.candidates_token_count or 0,
                    ),
                )

        # 处理第一个 chunk（如果有）
        if first_chunk is not None:
            yield from _process_chunk(first_chunk)

        # 处理剩余 chunks
        for chunk in stream_response:
            yield from _process_chunk(chunk)

        # 尾事件：工具调用或结束原因
        if seen_function_call and accumulated_tool_calls:
            tool_calls: list[ToolCall] = []
            for tc_data in accumulated_tool_calls.values():
                try:
                    arguments: dict[str, Any] = json.loads(
                        tc_data["data"]
                    )
                except (json.JSONDecodeError, KeyError):
                    arguments = {}

                tool_calls.append(ToolCall(
                    id=tc_data.get("id", ""),
                    name=tc_data.get("name", ""),
                    arguments=arguments,
                ))

            yield Delta(
                id=response_id,
                finish_reason=FinishReason.TOOL_CALLS,
                tool_calls=tool_calls,
            )
        else:
            yield Delta(
                id=response_id,
                finish_reason=FinishReason.STOP,
            )

    def list_models(self) -> list[str]:
        """查询可用 Gemini 模型列表，失败时回退到静态列表"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return sorted(GEMINI_STATIC_MODELS)

        try:
            model_names: list[str] = []
            for model in self.client.models.list():
                name: str = (model.name or "").removeprefix("models/")
                if not name:
                    continue

                name_lower: str = name.lower()

                # 必须包含 gemini
                if "gemini" not in name_lower:
                    continue

                # 排除不适合的模型类型
                if any(kw in name_lower for kw in GEMINI_MODEL_EXCLUDE_KEYWORDS):
                    continue

                model_names.append(name)

            return sorted(model_names) if model_names else sorted(
                GEMINI_STATIC_MODELS
            )
        except Exception as e:
            self.write_log(f"查询模型列表失败: {e}")
            return sorted(GEMINI_STATIC_MODELS)
