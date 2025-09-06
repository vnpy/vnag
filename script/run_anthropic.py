from vnag.utility import load_json
from vnag.object import Message, Request, Response, Role
from vnag.gateways.anthropic_gateway import AnthropicGateway


def main() -> None:
    """"""
    # 直接写入配置
    # setting: dict = {
    #     "base_url": "",
    #     "api_key": ""
    # }

    # 读取配置文件
    setting: dict = load_json("connect_anthropic.json")

    # 创建接口实例
    gateway = AnthropicGateway()

    # 初始化接口
    gateway.init(setting)

    # 创建请求对象
    request: Request = Request(
        model="claude-3-7-sonnet-20250219",
        messages=[
            Message(role=Role.USER, content="Hello, World!"),
        ],
        temperature=0,
        max_tokens=1024,
    )

    # 调用接口并输出结果
    response: Response = gateway.invoke(request)

    print(response.content)
    print(response.usage)


if __name__ == "__main__":
    main()
