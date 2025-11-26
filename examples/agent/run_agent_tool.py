"""
本脚本用于演示和测试 AgentTool 的 Multi-Agent 功能。

它会初始化一个 Agent 引擎，创建一个子智能体并封装为 AgentTool，
然后创建一个主智能体来调用该子智能体，实现 Multi-Agent 协作。

请确保您已在.vnag/connect_openai.json文件中添加了接口配置。
"""

from vnag.utility import load_json
from vnag.gateways.openai_gateway import OpenaiGateway
from vnag.engine import AgentEngine
from vnag.object import Profile
from vnag.agent import TaskAgent, AgentTool


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

    # 打印可用工具（注册 AgentTool 前）
    all_tools: list = engine.get_tool_schemas()
    print(f"\n可用工具数量: {len(all_tools)}")
    for _tool in all_tools:
        print(f"  - {_tool.name}: {_tool.description}")

    print("\n" + "="*50)
    print("请在下方配置参数区域填写参数")
    print("="*50 + "\n")

    # 配置参数（可根据上面打印的资源列表填写）
    MODEL_NAME: str = "qwen/qwen-max"  # 模型名称，从上面的模型列表中选择

    # ==================== 创建子智能体 ====================
    # 子智能体：专门负责翻译任务
    sub_profile: Profile = Profile(
        name="翻译助手",
        prompt="你是一个专业的翻译助手，擅长中英文互译。请根据用户的请求进行翻译，只返回翻译结果，不要添加额外的解释。",
        tools=[],  # 子智能体不使用其他工具
        temperature=0,
        max_tokens=2000,
        max_iterations=1
    )

    # 将子智能体封装为 AgentTool
    translator_tool: AgentTool = AgentTool(
        engine=engine,
        profile=sub_profile,
        model=MODEL_NAME,   # 子智能体使用的模型
        name="translator",  # 工具名称将变为 agent_translator
        description="专业翻译助手，可以进行中英文互译"
    )

    # 注册 AgentTool 到引擎
    engine.register_tool(translator_tool)

    # 打印注册后的工具列表
    print("\n--- 注册 AgentTool 后的工具列表 ---")
    all_tools = engine.get_tool_schemas()
    print(f"可用工具数量: {len(all_tools)}")
    for _tool in all_tools:
        print(f"  - {_tool.name}: {_tool.description}")

    # ==================== 创建主智能体 ====================
    # 主智能体：可以调用翻译助手
    main_profile: Profile = Profile(
        name="主控智能体",
        prompt="你是一个智能助手，当用户需要翻译时，请调用翻译助手工具来完成任务。",
        tools=[
            "agent_translator",  # 使用刚注册的 AgentTool
        ],
        temperature=0,
        max_tokens=10000,
        max_iterations=5
    )

    # 创建主智能体
    main_agent: TaskAgent = engine.create_agent(main_profile)
    main_agent.set_model(MODEL_NAME)

    print(f"\n当前配置: {main_agent.profile.name}")
    print(f"当前模型: {main_agent.model}")
    print(f"当前智能体ID: {main_agent.id}")

    # ==================== 测试 Multi-Agent 调用 ====================
    print("\n--- 测试 Multi-Agent 调用（主智能体调用翻译助手） ---\n")

    for delta in main_agent.stream("请帮我把这句话翻译成英文：人工智能正在改变世界。"):
        if delta.content:
            print(delta.content, end="", flush=True)

    print("\n")

    # 再测试一次英译中
    print("\n--- 测试英译中 ---\n")

    for delta in main_agent.stream("请把这句话翻译成中文：The future belongs to those who believe in the beauty of their dreams."):
        if delta.content:
            print(delta.content, end="", flush=True)

    print("\n")


if __name__ == "__main__":
    main()

