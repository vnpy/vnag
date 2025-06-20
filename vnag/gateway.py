from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion


class AgentGateway:
    """连接大模型API的网关，提供统一接口"""

    def __init__(self) -> None:
        """构造函数"""
        self.client: OpenAI | None = None
        self.model_name: str = ""

    def init(
        self,
        base_url: str,
        api_key: str,
        model_name: str
    ) -> None:
        """构造函数"""
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        self.model_name = model_name

    def invoke_model(self, messages: list[dict[str, str]]) -> str | None:
        """调用模型返回结果"""
        if not self.client:
            return None

        completion: ChatCompletion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages       # type: ignore
        )

        return completion.choices[0].message.content
