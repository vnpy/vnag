from vnag.utility import load_json
from vnag.object import Message, Request, Response, Role
from vnag.gateways.openai_gateway import OpenaiGateway


def main() -> None:
    """"""
    # 直接写入配置
    # setting: dict = {
    #     "base_url": "https://openrouter.ai/api/v1",
    #     "api_key": "123456"
    # }

    # 读取配置文件
    setting: dict = load_json("connect_openai.json")

    # 创建接口实例
    gateway: OpenaiGateway = OpenaiGateway()

    # 初始化接口
    gateway.init(setting)

    # 创建请求对象
    request: Request = Request(
        model="gpt-4o",
        messages=[
            Message(role=Role.USER, content="Hello, World!"),
        ],
        temperature=0,
        max_tokens=100,
    )

    # 调用接口并输出结果
    response: Response = gateway.invoke(request)

    print(response.content)
    print(response.usage)


if __name__ == "__main__":
    main()
