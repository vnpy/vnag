from typing import Any
from collections.abc import Generator

import dashscope
from dashscope import Generation, Models
from dashscope.api_entities.dashscope_response import (
    DashScopeAPIResponse,
    GenerationResponse,
    Choice
)

from vnag.gateway import BaseGateway
from vnag.object import FinishReason, Request, Response, Delta, Usage, Message
from vnag.object import Role


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
        call_params: dict[str, Any] = {
            "model": request.model,
            "messages": dashscope_messages,
            "result_format": "message",
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
        }

        response: GenerationResponse = Generation.call(**call_params)

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
        print(response)
        choice: Choice = response.output.choices[0]
        finish_reason: FinishReason = FINISH_REASON_MAP.get(
            choice.finish_reason, FinishReason.UNKNOWN
        )
        content: str = choice.message.content or ""

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
        call_params: dict[str, Any] = {
            "model": request.model,
            "messages": dashscope_messages,
            "result_format": "message",
            "stream": True,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
        }

        stream: Generator[GenerationResponse, None, None] = Generation.call(**call_params)

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
            new_content = choice.message.content or ""
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

        print(response)

        model_names: list[str] = [d["name"] for d in response.output["models"]]
        return model_names
