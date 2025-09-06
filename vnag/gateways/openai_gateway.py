from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.model import Model

from vnag.gateway import BaseGateway
from vnag.object import Request, Response, Usage


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

    def invoke(self, request: Request) -> Response:
        """常规调用接口：将已准备好的消息发送给模型并一次性产出文本。"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return Response(id="", content="", usage=Usage())

        params: dict[str, Any] = {
            "model": request.model,
            "messages": [msg.model_dump() for msg in request.messages],
        }
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.max_tokens is not None:
            params["max_tokens"] = request.max_tokens

        response: ChatCompletion = self.client.chat.completions.create(**params)

        usage = Usage()
        if response.usage:
            usage.input_tokens = response.usage.prompt_tokens
            usage.output_tokens = response.usage.completion_tokens

        return Response(
            id=response.id,
            content=response.choices[0].message.content or "",
            usage=usage,
        )

    def list_models(self) -> list[str]:
        """查询可用模型列表"""
        if not self.client:
            self.write_log("LLM客户端未初始化，请检查配置")
            return []

        models: list[Model] = self.client.models.list()
        return sorted([model.id for model in models])
