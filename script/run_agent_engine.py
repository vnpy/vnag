"""
本脚本用于演示和测试 AgentEngine 的核心功能。

它会初始化一个 Agent 引擎，并向其发送两个不同的用户请求， 分别用于触发本地工具和MCP工具的调用。

请确保您已在.vnag/connect_openai.json文件中添加了接口配置，同时在.vnag/mcp_config.json文件中添加了MCP工具配置。
"""

from vnag.engine import AgentEngine
from vnag.gateways.openai_gateway import OpenaiGateway
from vnag.object import Message, Role
from vnag.utility import load_json


def main() -> None:
    """"""
    # 初始化 Gateway
    try:
        setting = load_json("connect_openai.json")
    except FileNotFoundError:
        print("错误：未找到 connect_openai.json 配置文件。")
        print("请在项目根目录下创建该文件，并填入您的 OpenAI API 配置。")
        return

    gateway = OpenaiGateway()
    gateway.init(setting)

    # 初始化 Agent Engine
    engine = AgentEngine(gateway)
    engine.init()

    # 测试调用本地工具
    print("\n--- 测试调用本地工具 ---\n")
    messages_local = [
        Message(
            role=Role.USER,
            content="今天星期几？"
        )
    ]

    for delta in engine.stream(messages_local, model="gpt-4o"):
        if delta.content:
            print(delta.content, end="", flush=True)
    print("\n")

    # 测试调用MCP工具
    print("\n--- 测试调用MCP工具 ---\n")
    messages_mcp = [
        Message(
            role=Role.USER,
            content="列出当前目录下的所有文件和文件夹。"
        )
    ]

    for delta in engine.stream(messages_mcp, model="gpt-4o"):
        if delta.content:
            print(delta.content, end="", flush=True)
    print("\n")


if __name__ == "__main__":
    main()
