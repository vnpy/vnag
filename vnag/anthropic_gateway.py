from collections.abc import Generator

from anthropic import Anthropic

from .gateway import BaseGateway


class AnthropicGateway(BaseGateway):
    """连接 Anthropic 官方 SDK 的网关，提供统一接口"""

    def __init__(self) -> None:
        """构造函数"""
        self.client: Anthropic | None = None

    def init(self, base_url: str, api_key: str) -> bool:
        """初始化连接和内部服务组件，返回是否成功。"""

        if not base_url or not api_key:
            print("配置不完整，请检查以下配置项：")
            if not base_url:
                print("  - base_url: API地址未设置")
            if not api_key:
                print("  - api_key: API密钥未设置")
            return False

        self.client = Anthropic(api_key=api_key, base_url=base_url)

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

        try:
            # Anthropic 官方 SDK 的流式接口
            with self.client.messages.stream(
                model=model_name,
                messages=messages,
                **kwargs,
            ) as stream:
                yield from stream.text_stream

        except Exception as e:
            yield f"请求错误: {str(e)}"
            return
