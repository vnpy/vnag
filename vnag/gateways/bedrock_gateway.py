import os
import json
import base64
from typing import Any
from pathlib import Path
from collections.abc import Generator
import mimetypes

import boto3
from botocore.config import Config as BotoConfig

from vnag.constant import FinishReason, Role, AttachmentKind
from vnag.gateway import BaseGateway
from vnag.object import Request, Response, Delta, Usage, Message, ToolCall, Attachment, ModelInfo


BEDROCK_FINISH_REASON_MAP: dict[str, FinishReason] = {
    "end_turn": FinishReason.STOP,
    "max_tokens": FinishReason.LENGTH,
    "stop_sequence": FinishReason.STOP,
    "tool_use": FinishReason.TOOL_CALLS,
}

# 这些模型只接受 adaptive thinking；budget_tokens 会被拒绝。
# 子串同时覆盖 4.6/4.7/4.8 以及 5、5.1、5.5。
_ADAPTIVE_THINKING_MARKERS: tuple[str, ...] = (
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-haiku-5",
    "claude-fable-5",
    "claude-mythos-5",
)

# Fable / Mythos 连 disabled 也不接受，请求里仍要发 adaptive。
_ADAPTIVE_ONLY_MARKERS: tuple[str, ...] = (
    "claude-fable-5",
    "claude-mythos-5",
)


class BedrockGateway(BaseGateway):
    """连接 AWS Bedrock Converse API 的网关，提供统一接口"""

    default_name: str = "Bedrock"

    default_setting: dict = {
        "region_name": "us-east-1",
        "api_key": "",
        "proxy": "",
        "thinking_mode": ["adaptive", "enabled", "disabled"],
        "thinking_effort": ["max", "xhigh", "high", "medium", "low"],
        "thinking_budget_tokens": 2000,
    }

    def __init__(self, gateway_name: str = "") -> None:
        """构造函数"""
        if not gateway_name:
            gateway_name = self.default_name
        self.gateway_name = gateway_name
        self.client: Any | None = None
        self.meta_client: Any | None = None
        self.thinking_mode: str = "adaptive"
        self.thinking_effort: str = "medium"
        self.thinking_budget_tokens: int = 2000

    def _read_attachment_bytes(self, attachment: Attachment) -> tuple[bytes, str]:
        """读取 Bedrock 本地附件并返回 (bytes, mime)。"""
        if attachment.url:
            raise ValueError("Bedrock 网关当前仅支持本地 path 附件")
        if not attachment.path:
            raise ValueError("附件必须设置 path")

        file_path: Path = Path(attachment.path)
        if not file_path.is_file():
            raise FileNotFoundError(f"附件文件不存在: {attachment.path}")

        mime: str = attachment.mime or mimetypes.guess_type(file_path.name)[0] or ""
        if not mime:
            raise ValueError(f"无法推断附件 MIME 类型: {attachment.path}")

        return file_path.read_bytes(), mime

    def _resolve_attachment_name(self, attachment: Attachment) -> str:
        """推断 Bedrock 文档名称。"""
        if attachment.name:
            return attachment.name
        if attachment.path:
            return Path(attachment.path).stem or "attachment"
        return "attachment"

    def _build_user_content(self, msg: Message) -> list[dict[str, Any]]:
        """构造 Bedrock user content blocks。"""
        content_blocks: list[dict[str, Any]] = []
        if msg.content:
            content_blocks.append({"text": msg.content})

        has_document: bool = False
        for attachment in msg.attachments:
            raw_bytes, mime = self._read_attachment_bytes(attachment)

            if attachment.kind == AttachmentKind.IMAGE:
                if not mime.startswith("image/"):
                    raise ValueError(f"Bedrock 不支持的图片 MIME 类型: {mime}")
                content_blocks.append({
                    "image": {
                        "format": mime.split("/", maxsplit=1)[1],
                        "source": {"bytes": raw_bytes},
                    }
                })
                continue

            if attachment.kind == AttachmentKind.FILE:
                if mime != "application/pdf":
                    raise ValueError("Bedrock 网关当前仅支持 PDF 文件附件")
                has_document = True
                content_blocks.append({
                    "document": {
                        "format": "pdf",
                        "name": self._resolve_attachment_name(attachment),
                        "source": {"bytes": raw_bytes},
                    }
                })
                continue

            raise ValueError(f"当前网关暂不支持附件类型: {attachment.kind.value}")

        if has_document and not any("text" in block for block in content_blocks):
            content_blocks.insert(0, {"text": "请分析该文档。"})

        return content_blocks

    def _convert_messages(
        self, messages: list[Message]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        将内部格式转换为 Bedrock Converse 格式

        返回 (system_prompts, bedrock_messages)。
        system 消息单独提取；其余转换为 content block 数组。
        """
        system_prompts: list[dict[str, Any]] = []
        bedrock_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system_prompts.append({"text": msg.content})
                continue

            # 工具结果：合并为一条 user 消息
            if msg.tool_results:
                content_blocks: list[dict[str, Any]] = []
                for tr in msg.tool_results:
                    tool_result_block: dict[str, Any] = {
                        "toolUseId": tr.id,
                        "content": [{"text": tr.content}],
                    }
                    if tr.is_error:
                        tool_result_block["status"] = "error"
                    content_blocks.append({"toolResult": tool_result_block})

                bedrock_messages.append({
                    "role": "user",
                    "content": content_blocks,
                })
                continue

            # assistant 消息（可能同时包含 reasoning、text、toolUse）
            if msg.role == Role.ASSISTANT:
                content_blocks = []

                # 回传 reasoningContent（优先使用结构化 reasoning）
                if msg.reasoning:
                    for item in msg.reasoning:
                        reasoning_block = self._build_reasoning_content_block(
                            item
                        )
                        if reasoning_block:
                            content_blocks.append(reasoning_block)

                if msg.content:
                    content_blocks.append({"text": msg.content})

                for tc in msg.tool_calls:
                    content_blocks.append({
                        "toolUse": {
                            "toolUseId": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        }
                    })

                if content_blocks:
                    bedrock_messages.append({
                        "role": "assistant",
                        "content": content_blocks,
                    })
                continue

            # user 消息
            bedrock_messages.append({
                "role": msg.role.value,
                "content": self._build_user_content(msg),
            })

        return system_prompts, bedrock_messages

    def _build_reasoning_content_block(
        self, item: dict[str, Any]
    ) -> dict[str, Any] | None:
        """把内部 reasoning item 还原成一个 Converse content block。

        reasoningText.text 在请求侧必填。扩展思考模型会返回只有 signature、
        或 text 为空的块；回放时补上空字符串，否则 botocore 会拒绝。
        redactedContent 与 reasoningText 是 tagged union，密文块不能再带 text。
        """
        has_signature: bool = bool(item.get("signature"))
        has_text: bool = "text" in item
        redacted: Any = item.get("redacted_content")
        has_redacted: bool = redacted is not None

        if has_redacted and not has_text and not has_signature:
            return {
                "reasoningContent": {
                    "redactedContent": self._decode_redacted(redacted),
                }
            }

        if not has_text and not has_signature:
            return None

        reasoning_text: dict[str, Any] = {"text": item.get("text") or ""}
        if has_signature:
            reasoning_text["signature"] = item["signature"]
        return {"reasoningContent": {"reasoningText": reasoning_text}}

    def _extract_reasoning_from_blocks(
        self, content_blocks: list[dict[str, Any]]
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        从 Bedrock 响应的 content blocks 中提取 reasoning 信息

        返回 (thinking_text, reasoning_list)。
        thinking_text 用于 UI 展示；reasoning_list 保留完整结构供跨轮回传。
        """
        thinking: str = ""
        reasoning: list[dict[str, Any]] = []

        for idx, block in enumerate(content_blocks):
            if "reasoningContent" not in block:
                continue

            rc: dict[str, Any] = block["reasoningContent"]
            item: dict[str, Any] = {"index": idx, "type": "reasoning"}

            reasoning_text: dict[str, Any] | None = rc.get("reasoningText")
            if reasoning_text:
                text: str = reasoning_text.get("text", "")
                if text:
                    item["text"] = text
                    thinking += text

                signature: str = reasoning_text.get("signature", "")
                if signature:
                    item["signature"] = signature

            redacted: Any = rc.get("redactedContent")
            if redacted is not None:
                item["redacted_content"] = self._encode_redacted(redacted)

            reasoning.append(item)

        return thinking, reasoning

    def _encode_redacted(self, raw: Any) -> str:
        """密文存成可写入 JSON 的 ASCII 字符串。"""
        if isinstance(raw, str):
            return raw
        return base64.b64encode(bytes(raw)).decode("ascii")

    def _decode_redacted(self, value: Any) -> bytes:
        """回放时把 base64 还原成 Bedrock 要求的字节。"""
        if isinstance(value, str):
            return base64.b64decode(value)
        return bytes(value)

    def _append_reasoning_delta(
        self,
        pending: dict[int, dict[str, Any]],
        block_index: int,
        rc_delta: dict[str, Any],
    ) -> str:
        """把一段 reasoning 增量攒进未完成的块，并返回需要展示的文本。"""
        item: dict[str, Any] = pending.setdefault(
            block_index,
            {"index": block_index, "type": "reasoning"},
        )
        text: str = rc_delta.get("text", "")
        if text:
            item["text"] = item.get("text", "") + text

        signature: str = rc_delta.get("signature", "")
        if signature:
            item["signature"] = signature

        redacted: Any = rc_delta.get("redactedContent")
        if redacted is not None:
            raw: bytes = redacted.encode("utf-8") if isinstance(redacted, str) else bytes(redacted)
            buffer: bytearray = item.setdefault("_redacted", bytearray())
            buffer.extend(raw)
        return text

    def _finish_reasoning_block(
        self,
        pending: dict[int, dict[str, Any]],
        block_index: int,
    ) -> dict[str, Any] | None:
        """停块时交出完整推理项。密文只编码一次。"""
        item: dict[str, Any] | None = pending.pop(block_index, None)
        if item is None:
            return None

        raw: Any = item.pop("_redacted", None)
        if raw is not None:
            item["redacted_content"] = self._encode_redacted(raw)
        if any(key in item for key in ("text", "signature", "redacted_content")):
            return item
        return None

    def _model_has_marker(self, model_id: str, markers: tuple[str, ...]) -> bool:
        """判断模型 ID 是否命中任一能力标记。"""
        normalized_model_id: str = model_id.lower()
        return any(marker in normalized_model_id for marker in markers)

    def _supports_adaptive_thinking(self, model_id: str) -> bool:
        """判断模型是否支持 Claude adaptive thinking。"""
        return self._model_has_marker(model_id, _ADAPTIVE_THINKING_MARKERS)

    def _adaptive_only_thinking(self, model_id: str) -> bool:
        """Fable / Mythos 不接受 budget_tokens，也不接受 disabled。"""
        return self._model_has_marker(model_id, _ADAPTIVE_ONLY_MARKERS)

    def _adaptive_request_fields(self, thinking_type: str) -> dict[str, Any]:
        """构造 adaptive 代际的 thinking 与 effort。effort 必须放在 output_config。"""
        fields: dict[str, Any] = {"thinking": {"type": thinking_type}}
        if self.thinking_effort:
            fields["output_config"] = {"effort": self.thinking_effort}
        return fields

    def _get_additional_model_request_fields(
        self, model_id: str
    ) -> dict[str, Any] | None:
        """按模型能力构造 Bedrock 的 thinking 配置。"""
        normalized_model_id: str = model_id.lower()
        if "anthropic" not in normalized_model_id:
            return None

        if self._adaptive_only_thinking(normalized_model_id):
            return self._adaptive_request_fields("adaptive")

        if self._supports_adaptive_thinking(normalized_model_id):
            if self.thinking_mode == "disabled":
                return self._adaptive_request_fields("disabled")
            return self._adaptive_request_fields("adaptive")

        if self.thinking_mode == "disabled":
            return None

        return {
            "thinking": {
                "type": "enabled",
                "budget_tokens": self.thinking_budget_tokens,
            }
        }

    def init(self, setting: dict[str, Any]) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""
        region_name: str = setting.get("region_name", "us-east-1")
        api_key: str = setting.get("api_key", "")
        proxy: str = setting.get("proxy", "")
        self.thinking_mode = setting.get("thinking_mode", "adaptive")
        self.thinking_effort = setting.get("thinking_effort", "medium")
        self.thinking_budget_tokens = int(setting.get("thinking_budget_tokens", 2000))

        if not region_name:
            self.write_log("配置不完整，请检查以下配置项：")
            self.write_log("  - region_name: 区域未设置")
            return False

        # 通过环境变量注入 API Key 认证
        if api_key:
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = api_key

        # 思考模型可能在首个 token 前思考数分钟，默认 60 秒读超时会中断流式响应。
        config_kwargs: dict[str, Any] = {
            "connect_timeout": 60,
            "read_timeout": 600,
        }
        if proxy:
            config_kwargs["proxies"] = {"https": proxy}
        boto_config = BotoConfig(**config_kwargs)

        try:
            self.client = boto3.client(
                service_name="bedrock-runtime",
                region_name=region_name,
                config=boto_config,
            )
            self.meta_client = boto3.client(
                service_name="bedrock",
                region_name=region_name,
                config=boto_config,
            )
        except Exception as e:
            self.write_log(f"创建 Bedrock 客户端失败: {e}")
            return False

        return True

    def invoke(self, request: Request) -> Response:
        """常规调用接口：将已准备好的消息发送给模型并一次性产出文本。"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return Response(id="", content="", usage=Usage())

        system_prompts, bedrock_messages = self._convert_messages(
            request.messages
        )

        converse_params: dict[str, Any] = {
            "modelId": request.model,
            "messages": bedrock_messages,
        }

        if system_prompts:
            converse_params["system"] = system_prompts

        additional_fields: dict[str, Any] | None = (
            self._get_additional_model_request_fields(request.model)
        )
        if additional_fields:
            converse_params["additionalModelRequestFields"] = additional_fields

        # 推理参数
        inference_config: dict[str, Any] = {}
        if request.max_tokens:
            inference_config["maxTokens"] = request.max_tokens
        if request.temperature is not None:
            inference_config["temperature"] = request.temperature
        if request.top_p is not None:
            inference_config["topP"] = request.top_p
        if inference_config:
            converse_params["inferenceConfig"] = inference_config

        # 工具定义
        if request.tool_schemas:
            tool_config: dict[str, Any] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": schema.name,
                            "description": schema.description,
                            "inputSchema": {
                                "json": schema.parameters,
                            },
                        }
                    }
                    for schema in request.tool_schemas
                ]
            }
            converse_params["toolConfig"] = tool_config

        response: dict[str, Any] = self.client.converse(**converse_params)

        # 提取 usage
        response_usage: dict[str, Any] = response.get("usage", {})
        usage: Usage = Usage(
            input_tokens=response_usage.get("inputTokens", 0),
            output_tokens=response_usage.get("outputTokens", 0),
        )

        # 提取 finish reason
        stop_reason: str = response.get("stopReason", "")
        finish_reason: FinishReason = BEDROCK_FINISH_REASON_MAP.get(
            stop_reason, FinishReason.UNKNOWN
        )

        # 提取响应内容
        output_message: dict[str, Any] = response.get("output", {}).get(
            "message", {}
        )
        content_blocks: list[dict[str, Any]] = output_message.get(
            "content", []
        )

        content: str = ""
        tool_calls: list[ToolCall] = []

        # 提取 reasoning
        thinking, reasoning = self._extract_reasoning_from_blocks(
            content_blocks
        )

        for block in content_blocks:
            if "text" in block:
                content += block["text"]
            elif "toolUse" in block:
                tu: dict[str, Any] = block["toolUse"]
                tool_calls.append(ToolCall(
                    id=tu.get("toolUseId", ""),
                    name=tu.get("name", ""),
                    arguments=tu.get("input", {}),
                ))

        # 构建消息对象
        response_id: str = response.get(
            "ResponseMetadata", {}
        ).get("RequestId", "")

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

        system_prompts, bedrock_messages = self._convert_messages(
            request.messages
        )

        converse_params: dict[str, Any] = {
            "modelId": request.model,
            "messages": bedrock_messages,
        }

        if system_prompts:
            converse_params["system"] = system_prompts

        additional_fields: dict[str, Any] | None = (
            self._get_additional_model_request_fields(request.model)
        )
        if additional_fields:
            converse_params["additionalModelRequestFields"] = additional_fields

        # 推理参数
        inference_config: dict[str, Any] = {}
        if request.max_tokens:
            inference_config["maxTokens"] = request.max_tokens
        if request.temperature is not None:
            inference_config["temperature"] = request.temperature
        if request.top_p is not None:
            inference_config["topP"] = request.top_p
        if inference_config:
            converse_params["inferenceConfig"] = inference_config

        # 工具定义
        if request.tool_schemas:
            tool_config: dict[str, Any] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": schema.name,
                            "description": schema.description,
                            "inputSchema": {
                                "json": schema.parameters,
                            },
                        }
                    }
                    for schema in request.tool_schemas
                ]
            }
            converse_params["toolConfig"] = tool_config

        response: dict[str, Any] = self.client.converse_stream(
            **converse_params
        )

        response_id: str = response.get(
            "ResponseMetadata", {}
        ).get("RequestId", "")

        # 按 contentBlockIndex 累积工具调用和未完成的推理块
        accumulated_tool_calls: dict[int, dict[str, Any]] = {}
        pending_reasoning: dict[int, dict[str, Any]] = {}

        event_stream: Any = response.get("stream", [])

        for event in event_stream:
            # contentBlockStart：记录工具调用和 reasoning 块的起始
            if "contentBlockStart" in event:
                start_data: dict[str, Any] = event["contentBlockStart"]
                block_index: int = start_data.get("contentBlockIndex", 0)
                start_block: dict[str, Any] = start_data.get("start", {})

                if "toolUse" in start_block:
                    tu_start: dict[str, Any] = start_block["toolUse"]
                    accumulated_tool_calls[block_index] = {
                        "id": tu_start.get("toolUseId", ""),
                        "name": tu_start.get("name", ""),
                        "input": "",
                    }

            # contentBlockDelta：处理文本、reasoning、工具调用增量
            elif "contentBlockDelta" in event:
                delta_data: dict[str, Any] = event["contentBlockDelta"]
                block_index = delta_data.get("contentBlockIndex", 0)
                delta_block: dict[str, Any] = delta_data.get("delta", {})

                # 文本增量
                if "text" in delta_block:
                    yield Delta(
                        id=response_id,
                        content=delta_block["text"],
                    )

                # reasoning 增量先攒在块内，文本仍实时交给界面
                elif "reasoningContent" in delta_block:
                    thinking_text: str = self._append_reasoning_delta(
                        pending_reasoning,
                        block_index,
                        delta_block["reasoningContent"],
                    )
                    if thinking_text:
                        yield Delta(id=response_id, thinking=thinking_text)

                # 工具调用输入增量
                elif "toolUse" in delta_block:
                    tu_delta: dict[str, Any] = delta_block["toolUse"]
                    if block_index in accumulated_tool_calls:
                        accumulated_tool_calls[block_index][
                            "input"
                        ] += tu_delta.get("input", "")

            # 推理块结束才交出完整项。未收到 stop 的半截块不回放。
            elif "contentBlockStop" in event:
                stop_index: int = event["contentBlockStop"].get(
                    "contentBlockIndex",
                    0,
                )
                finished: dict[str, Any] | None = self._finish_reasoning_block(
                    pending_reasoning,
                    stop_index,
                )
                if finished:
                    yield Delta(id=response_id, reasoning=[finished])

            # messageStop：包含结束原因
            elif "messageStop" in event:
                stop_data: dict[str, Any] = event["messageStop"]
                stop_reason: str = stop_data.get("stopReason", "")
                finish_reason: FinishReason = BEDROCK_FINISH_REASON_MAP.get(
                    stop_reason, FinishReason.UNKNOWN
                )

                delta = Delta(
                    id=response_id,
                    finish_reason=finish_reason,
                )

                # 如果是工具调用结束，转换累积的工具调用
                if (
                    finish_reason == FinishReason.TOOL_CALLS
                    and accumulated_tool_calls
                ):
                    tool_calls: list[ToolCall] = []
                    for tc_data in accumulated_tool_calls.values():
                        try:
                            arguments: dict[str, Any] = json.loads(
                                tc_data["input"]
                            )
                        except json.JSONDecodeError:
                            arguments = {}

                        tool_calls.append(ToolCall(
                            id=tc_data["id"],
                            name=tc_data["name"],
                            arguments=arguments,
                        ))

                    delta.tool_calls = tool_calls

                yield delta

            # metadata：包含 usage 信息
            elif "metadata" in event:
                meta: dict[str, Any] = event["metadata"]
                meta_usage: dict[str, Any] = meta.get("usage", {})

                yield Delta(
                    id=response_id,
                    usage=Usage(
                        input_tokens=meta_usage.get("inputTokens", 0),
                        output_tokens=meta_usage.get("outputTokens", 0),
                    ),
                )

    def list_models(self) -> list[ModelInfo]:
        """通过 Bedrock ListFoundationModels 查询支持文本输出的模型列表"""
        if not self.meta_client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return []

        try:
            response: dict[str, Any] = self.meta_client.list_foundation_models(
                byOutputModality="TEXT",
            )
        except Exception as e:
            self.write_log(f"查询模型列表失败: {e}")
            return []

        summaries: list[dict[str, Any]] = response.get("modelSummaries", [])
        infos: list[ModelInfo] = []

        for s in summaries:
            model_id: str = s.get("modelId", "")
            if not model_id:
                continue

            lifecycle: dict[str, Any] = s.get("modelLifecycle") or {}
            if lifecycle.get("status") == "LEGACY":
                continue

            provider: str = (s.get("providerName") or "").lower()
            infos.append(ModelInfo(id=model_id, provider=provider, name=model_id))

        return sorted(infos, key=lambda x: x.id)
