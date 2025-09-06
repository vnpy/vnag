from typing import Any

from anthropic import Anthropic
from anthropic.types import Message as AnthropicMessage

from vnag.gateway import BaseGateway
from vnag.object import Request, Response, Usage


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
        base_url: str = setting.get("base_url", "")
        api_key: str = setting.get("api_key", "")

        if not base_url or not api_key:
            self.write_log("配置不完整，请检查以下配置项：")
            if not base_url:
                self.write_log("  - base_url: API地址未设置")
            if not api_key:
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

        params: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
        }
        if system_prompt:
            params["system"] = system_prompt
        if request.temperature is not None:
            params["temperature"] = request.temperature

        try:
            response: AnthropicMessage = self.client.messages.create(**params)

            usage = Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

            return Response(
                id=response.id,
                content=content,
                usage=usage,
            )
        except Exception as e:
            error_msg = f"请求错误: {str(e)}"
            self.write_log(error_msg)
            return Response(id="", content=error_msg, usage=Usage())
