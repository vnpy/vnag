"""CLI 斜杠命令处理"""

from ..agent import TaskAgent
from ..engine import AgentEngine
from ..object import Profile
from .bridge import StreamBridge
from .factory import set_cli_value
from .renderer import Renderer


def handle_command(
    raw: str,
    engine: AgentEngine,
    agent: TaskAgent,
    bridge: StreamBridge,
    renderer: Renderer,
) -> tuple[TaskAgent, StreamBridge]:
    """
    处理斜杠命令，返回 (agent, bridge) 元组。

    /profile 等命令可能创建新的 agent，需要同步更新 bridge。
    """
    parts: list[str] = raw.split(maxsplit=1)
    cmd: str = parts[0].lower()
    arg: str = parts[1] if len(parts) > 1 else ""

    if cmd == "/help":
        renderer.console.print(
            "可用命令:\n"
            "  /help              显示帮助\n"
            "  /clear             清空屏幕\n"
            "  /model <name>      切换模型\n"
            "  /profile <name>    切换 Profile\n"
            "  /retry             重发上一轮\n"
            "  /sessions          列出会话\n"
            "  /title             生成标题\n"
            "  /stats             会话统计\n"
            "  /exit              退出"
        )

    elif cmd == "/clear":
        renderer.console.clear()

    elif cmd == "/model":
        if arg:
            agent.set_model(arg)
            set_cli_value("model_name", arg)
            renderer.show_info(f"模型已切换为: {arg}")
        else:
            renderer.show_info(f"当前模型: {agent.model}")

    elif cmd == "/profile":
        if not arg:
            renderer.show_info(f"当前 Profile: {agent.profile.name}")
        else:
            profile: Profile | None = engine.get_profile(arg)
            if profile:
                agent = engine.create_agent(profile, save=True)
                bridge = StreamBridge(agent, renderer)
                set_cli_value("profile_name", arg)
                renderer.show_info(f"已切换到 Profile: {arg}")
                renderer.show_welcome(agent)
            else:
                renderer.show_error(f"未找到 Profile: {arg}")

    elif cmd == "/retry":
        prompt: str = agent.pop_round()
        if prompt:
            bridge.run(prompt)
        else:
            renderer.show_info("没有可重发的对话")

    elif cmd == "/sessions":
        for a in engine.get_all_agents():
            marker: str = "→" if a.id == agent.id else " "
            renderer.console.print(f"  {marker} {a.id}  {a.name}")

    elif cmd == "/title":
        try:
            title: str = agent.generate_title()
            if title:
                agent.rename(title)
                renderer.show_info(f"标题已更新: {title}")
        except Exception as e:
            renderer.show_error(f"生成标题失败: {e}")

    elif cmd == "/stats":
        msg_count: int = len(agent.messages)
        renderer.console.print(f"  消息数: {msg_count}  |  Session: {agent.id}")

    elif cmd == "/exit":
        raise EOFError

    else:
        renderer.show_info(f"未知命令: {cmd}，输入 /help 查看帮助")

    return agent, bridge
