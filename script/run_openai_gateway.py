from vnag.utility import load_json
from vnag.object import Message, Request, Response, Role, ToolSchema
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

    # 列出支持模型
    model_names: list[str] = gateway.list_models()
    print(model_names)

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

    # 定义工具
    get_weather_schema = ToolSchema(
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
    tool_request = Request(
        model="gpt-4o",
        messages=[Message(role=Role.USER, content="上海今天天气如何?")],
        tools_schemas=[get_weather_schema],
    )

    # 调用接口
    tool_response = gateway.invoke(tool_request)

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

    # 流式调用并输出结果
    stream_request: Request = Request(
        model="gpt-4o",
        messages=[
            Message(
                role=Role.USER,
                content="Give me an introduction of Python programming language"
            ),
        ],
        temperature=1,
        max_tokens=10000,
    )

    for chunk in gateway.stream(stream_request):
        if chunk.content:
            print(chunk.content, end="", flush=True)

        if chunk.finish_reason:
            print(f"\n结束原因: {chunk.finish_reason.value}")

        if chunk.usage:
            print(f"\n用量统计: {chunk.usage}")


if __name__ == "__main__":
    main()
