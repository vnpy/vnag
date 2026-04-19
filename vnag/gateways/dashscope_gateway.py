from typing import Any
from pathlib import Path
from collections.abc import Generator

import dashscope
from dashscope import Generation, Models, MultiModalConversation
from dashscope.api_entities.dashscope_response import (
    DashScopeAPIResponse,
    Choice,
    MultiModalConversationResponse,
)

from vnag.gateway import BaseGateway
from vnag.object import FinishReason, Request, Response, Delta, Usage, Message
from vnag.object import Role
from vnag.constant import AttachmentKind


FINISH_REASON_MAP = {
    "stop": FinishReason.STOP,
    "length": FinishReason.LENGTH,
}


class DashscopeGateway(BaseGateway):
    """连接 DashScope SDK 的网关，提供统一接口"""

    default_name: str = "DashScope"

    default_setting: dict = {
        "api_key": "",
    }

    def __init__(self, gateway_name: str = "") -> None:
        """构造函数"""
        if not gateway_name:
            gateway_name = self.default_name
        self.gateway_name = gateway_name

        self.api_key: str = ""

    def _use_multimodal_api(self, messages: list[Message]) -> bool:
        """判断是否需要切换到多模态 API。"""
        return any(msg.attachments for msg in messages)

    def _extract_text_content(self, content: Any) -> str:
        """从 DashScope content 中提取文本。"""
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("text"):
                    text_parts.append(str(item["text"]))
            return "".join(text_parts)

        return ""

    def _convert_multimodal_messages(
        self, messages: list[Message]
    ) -> list[dict[str, Any]]:
        """将内部格式转换为 DashScope 多模态消息格式。"""
        dashscope_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.attachments and msg.role != Role.USER:
                raise ValueError("DashScope 网关当前仅支持用户消息携带附件")

            content_parts: list[dict[str, Any]] = []
            if msg.content:
                content_parts.append({"text": msg.content})

            for attachment in msg.attachments:
                if attachment.kind != AttachmentKind.IMAGE:
                    raise ValueError("DashScope 网关当前仅支持图片附件")

                if attachment.url:
                    content_parts.append({"image": attachment.url})
                    continue

                if not attachment.path:
                    raise ValueError("附件必须设置 url 或 path")

                image_uri: str = Path(attachment.path).resolve().as_uri()
                content_parts.append({"image": image_uri})

            if content_parts:
                dashscope_messages.append({
                    "role": msg.role.value,
                    "content": content_parts,
                })

        return dashscope_messages

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """将内部格式转换为 Dashscope (OpenAI兼容) 格式"""
        dashscope_messages = []

        for msg in messages:
            message_dict: dict[str, Any] = {"role": msg.role.value}

            if msg.content:
                message_dict["content"] = msg.content

            dashscope_messages.append(message_dict)

        return dashscope_messages

    def init(self, setting: dict[str, Any]) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""
        self.api_key = setting.get("api_key", "")

        if not self.api_key:
            self.write_log("配置不完整，请检查以下配置项：")
            self.write_log("  - api_key: API密钥未设置")
            return False

        dashscope.api_key = self.api_key
        return True

    def invoke(self, request: Request) -> Response:
        """常规调用接口：将已准备好的消息发送给模型并一次性产出文本。"""
        if not self.api_key:
            self.write_log("LLM客户端未初始化，请检查配置")
            return Response(id="", content="LLM客户端未初始化", usage=Usage())

        # 使用新的消息转换方法
        dashscope_messages = self._convert_messages(request.messages)

        # 准备请求参数
        if self._use_multimodal_api(request.messages):
            call_params: dict[str, Any] = {
                "model": request.model,
                "messages": self._convert_multimodal_messages(request.messages),
                "stream": False,
            }
            if request.temperature is not None:
                call_params["temperature"] = request.temperature
            if request.max_tokens is not None:
                call_params["max_length"] = request.max_tokens
            if request.top_p is not None:
                call_params["top_p"] = request.top_p

            response: MultiModalConversationResponse = (
                MultiModalConversation.call(**call_params)
            )
        else:
            call_params = {
                "model": request.model,
                "messages": dashscope_messages,
                "result_format": "message",
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
            }

            response = Generation.call(**call_params)

        if response.status_code != 200:
            return Response(
                id=response.request_id,
                content=f"请求失败: {response.message}",
                usage=Usage(),
            )

        usage: Usage = Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        choice: Choice = response.output.choices[0]
        finish_reason: FinishReason = FINISH_REASON_MAP.get(
            choice.finish_reason, FinishReason.UNKNOWN
        )
        content: str = self._extract_text_content(choice.message.content)

        # 构建返回的消息对象
        message: Message = Message(
            role=Role.ASSISTANT,
            content=content
        )

        return Response(
            id=response.request_id,
            content=content,
            usage=usage,
            finish_reason=finish_reason,
            message=message
        )

    def stream(self, request: Request) -> Generator[Delta, None, None]:
        """流式调用接口"""
        if not self.api_key:
            self.write_log("LLM客户端未初始化，请检查配置")
            return

        # 使用新的消息转换方法
        dashscope_messages = self._convert_messages(request.messages)

        # 准备请求参数
        if self._use_multimodal_api(request.messages):
            call_params: dict[str, Any] = {
                "model": request.model,
                "messages": self._convert_multimodal_messages(request.messages),
                "stream": True,
            }
            if request.temperature is not None:
                call_params["temperature"] = request.temperature
            if request.max_tokens is not None:
                call_params["max_length"] = request.max_tokens
            if request.top_p is not None:
                call_params["top_p"] = request.top_p

            stream: Generator[MultiModalConversationResponse, None, None] = (
                MultiModalConversation.call(**call_params)
            )
        else:
            call_params = {
                "model": request.model,
                "messages": dashscope_messages,
                "result_format": "message",
                "stream": True,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
            }

            stream = Generation.call(**call_params)

        response_id: str = ""
        full_content: str = ""

        for response in stream:
            if response.status_code != 200:
                self.write_log(f"请求发生错误: {response.message}")
                yield Delta(
                    id=response.request_id,
                    content=f"请求发生错误: {response.message}",
                    finish_reason=FinishReason.ERROR,
                )
                break

            if not response_id:
                response_id = response.request_id

            delta: Delta = Delta(id=response_id)
            should_yield: bool = False
            choice: Choice = response.output.choices[0]

            # 检查内容增量
            new_content = self._extract_text_content(choice.message.content)
            delta_content = new_content[len(full_content):]
            if delta_content:
                full_content = new_content
                delta.content = delta_content
                should_yield = True

            # 检查结束原因
            if choice.finish_reason != "null":
                finish_reason: FinishReason = FINISH_REASON_MAP.get(
                    choice.finish_reason, FinishReason.UNKNOWN
                )
                delta.finish_reason = finish_reason
                delta.usage = Usage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )
                should_yield = True

            if should_yield:
                yield delta

    def list_models(self) -> list[str]:
        """查询可用模型列表"""
        if not self.api_key:
            self.write_log("LLM客户端未初始化，请检查配置")
            return []

        try:
            response: DashScopeAPIResponse = Models.list(
                page_size=100,
                api_key=self.api_key
            )
        except Exception as err:
            self.write_log(f"查询模型列表失败: {err}")
            return []

        if response.status_code != 200:
            self.write_log(f"查询模型列表失败: {response.message}")
            return []

        model_names: list[str] = [d["name"] for d in response.output["models"]]
        return model_names
