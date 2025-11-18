from vnag.utility import load_json
from vnag.object import Message, Request, Response, Role, ToolSchema
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
    gateway: AnthropicGateway = AnthropicGateway()

    # 初始化接口
    gateway.init(setting)

    # 列出支持模型
    model_names: list[str] = gateway.list_models()
    print(model_names)

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

    # 定义工具
    get_weather_schema: ToolSchema = ToolSchema(
        name="get_current_weather",
        description="获取指定地点的当前天气情况",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "城市和省份，例如：上海, 北京",
                },
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
        },
    )

    # 创建工具调用请求
    tool_request: Request = Request(
        model="claude-3-opus-20240229",
        messages=[Message(role=Role.USER, content="今天上海的天气如何？")],
        tool_schemas=[get_weather_schema],
        max_tokens=1024,
    )

    # 调用接口
    tool_response: Response = gateway.invoke(tool_request)

    # 打印工具调用结果
    if tool_response.message and tool_response.message.tool_calls:
        print("工具调用:")
        for tc in tool_response.message.tool_calls:
            print(f"  ID: {tc.id}")
            print(f"  Name: {tc.name}")
            print(f"  Arguments: {tc.arguments}")
    else:
        print("模型回复:")
        print(tool_response.content)

    print(f"用量统计: {tool_response.usage}")


if __name__ == "__main__":
    main()
