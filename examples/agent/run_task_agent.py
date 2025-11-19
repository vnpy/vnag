"""
本脚本用于演示和测试 AgentEngine 和 TaskAgent 的核心功能。

它会初始化一个 Agent 引擎，并创建一个任务型智能体，然后向其发送两个不同的用户请求， 分别用于触发本地工具和MCP工具的调用。

请确保您已在.vnag/connect_openai.json文件中添加了接口配置，同时在.vnag/mcp_config.json文件中添加了MCP工具配置。
"""

from vnag.utility import load_json
from vnag.gateways.openai_gateway import OpenaiGateway
from vnag.engine import AgentEngine
from vnag.object import Profile
from vnag.agent import TaskAgent


def main() -> None:
    """"""
    # 读取配置文件
    try:
        setting: dict = load_json("connect_openai.json")
    except FileNotFoundError:
        print("错误：未找到 connect_openai.json 配置文件。")
        print("请在 .vnag 目录下创建该文件，并填入您的 OpenAI API 配置。")
        return

    # 创建接口实例
    gateway: OpenaiGateway = OpenaiGateway()

    # 初始化接口
    gateway.init(setting)

    # 初始化引擎
    engine: AgentEngine = AgentEngine(gateway)
    engine.init()

    # 打印现有资源，帮助用户决定配置参数
    print("\n" + "="*50)
    print("现有资源列表")
    print("="*50)

    # 打印已有模型
    all_models: list[str] = engine.list_models()
    print(f"\n可用模型数量: {len(all_models)}")
    for model in all_models:
        print(f"  - {model}")

    # 打印已有配置
    all_profiles: list = engine.get_all_profiles()
    print(f"\n已有配置数量: {len(all_profiles)}")
    for _profile in all_profiles:
        print(f"  - {_profile.name}")

    # 打印已有智能体
    all_agents: list = engine.get_all_agents()
    print(f"\n已有智能体数量: {len(all_agents)}")
    for _agent in all_agents:
        print(f"  - {_agent.name} (ID: {_agent.id})")

    # 打印可用工具
    all_tools: list = engine.get_tool_schemas()
    print(f"\n可用工具数量: {len(all_tools)}")
    for _tool in all_tools:
        print(f"  - {_tool.name}: {_tool.description}")

    print("\n" + "="*50)
    print("请在下方配置参数区域填写参数")
    print("="*50 + "\n")

    # 配置参数（可根据上面打印的资源列表填写）
    PROFILE_NAME: str = "任务型智能体"  # 配置名称，如果已存在则复用
    MODEL_NAME: str = "qwen/qwen-max"  # 模型名称，从上面的模型列表中选择
    AGENT_ID: str = ""  # 留空表示创建新智能体，或填入已有的智能体ID以复用会话

    # 创建智能体配置
    # 注意：MCP工具需要在mcp_config.json中配置对应的服务器才能使用
    profile: Profile = Profile(
        name=PROFILE_NAME,
        prompt="你是一个智能的任务型助理，能够根据用户需求调用本地工具和MCP工具来完成任务。",
        tools=[
            "day_of_week",                  # 本地工具：获取星期几
            "filesystem_list_directory",    # MCP工具：列出目录（filesystem服务器）
        ],
        temperature=0,
        max_tokens=10000,
        max_iterations=10
    )

    # 检查配置是否已存在，不存在则添加
    # 注意：如果配置已存在且需要更新内容，使用 engine.update_profile(profile) 代替
    if not engine.get_profile(profile.name):
        engine.add_profile(profile)

    # 获取或创建智能体
    if AGENT_ID:
        agent: TaskAgent | None = engine.get_agent(AGENT_ID)
        if not agent:
            print(f"未找到智能体 {AGENT_ID}，创建新的智能体")
            agent = engine.create_agent(profile)
    else:
        agent = engine.create_agent(profile)

    agent.set_model(MODEL_NAME)

    print(f"当前配置: {agent.profile.name}")
    print(f"当前模型: {agent.model}")
    print(f"当前智能体ID: {agent.id}")

    # 测试调用本地工具
    print("\n--- 测试调用本地工具 ---\n")

    for delta in agent.stream("今天星期几？"):
        if delta.content:
            print(delta.content, end="", flush=True)

    print("\n")

    # 测试调用 MCP 工具
    print("\n--- 测试调用 MCP 工具 ---\n")

    for delta in agent.stream("列出当前目录下的所有文件和文件夹。"):
        if delta.content:
            print(delta.content, end="", flush=True)

    print("\n")


if __name__ == "__main__":
    main()
