from collections.abc import Generator
from typing import Any

from openai import OpenAI

from .gateway import BaseGateway


class AgentGateway(BaseGateway):
    """连接大模型API的网关，提供统一接口"""

    def __init__(self) -> None:
        """构造函数"""
        self.client: OpenAI | None = None

    def init(self, base_url: str, api_key: str) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""

        if not base_url or not api_key:
            print("配置不完整，请检查以下配置项：")
            if not base_url:
                print("  - base_url: API地址未设置")
            if not api_key:
                print("  - api_key: API密钥未设置")
            return False

        self.client = OpenAI(api_key=api_key, base_url=base_url)

        return True

    def invoke_streaming(
        self,
        messages: list[dict[str, str]],
        model_name: str,
        **kwargs: object
    ) -> Generator[str, None, None]:
        """统一流式调用接口"""
        if not self.client:
            yield "LLM客户端未初始化，请检查配置"
            return

        # 使用关键字参数调用，确保类型匹配
        params: dict[str, object] = {"stream": True}
        max_tokens = kwargs.get("max_tokens", 0)
        temperature = kwargs.get("temperature", 0.0)
        if max_tokens:
            params["max_tokens"] = max_tokens
        if temperature:
            params["temperature"] = temperature

        try:
            stream: Any = self.client.chat.completions.create(  # type: ignore[call-overload]
                model=model_name,
                messages=messages,
                **params,
            )

            # 流式输出处理
            for chunk in stream:
                # 只处理内容部分（显式检查 None）
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"请求错误: {str(e)}"
            return
