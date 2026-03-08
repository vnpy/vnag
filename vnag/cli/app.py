"""CLI 入口与主循环"""

import argparse
from collections.abc import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory

from ..engine import AgentEngine
from ..agent import TaskAgent
from ..object import Profile
from ..utility import TEMP_DIR
from .factory import create_gateway, get_cli_value
from .bridge import StreamBridge
from .renderer import Renderer
from .commands import handle_command
from .completer import CliCompleter


# 输入历史文件路径
HISTORY_FILE = TEMP_DIR / "cli_history.txt"


def _parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="vnag-cli",
        description="vnag CLI 终端交互界面",
    )

    # 非交互模式
    parser.add_argument("--task", default="", help="执行单次任务后退出")

    return parser.parse_args()


def _create_agent(engine: AgentEngine) -> TaskAgent:
    """根据 cli_setting.json 创建 TaskAgent 实例"""
    # 从配置读取 profile 和 model
    profile_name: str = get_cli_value("profile_name")
    model_name: str = get_cli_value("model_name")

    # 查找 Profile，不存在则使用第一个
    profile: Profile | None = None
    if profile_name:
        profile = engine.get_profile(profile_name)

    if not profile:
        profiles: list[Profile] = engine.get_all_profiles()
        profile = profiles[0]

    # 创建新会话
    agent: TaskAgent = engine.create_agent(profile, save=True)

    # 设置模型
    if model_name:
        agent.set_model(model_name)

    return agent


def _make_toolbar(agent_ref: list[TaskAgent]) -> Callable[[], HTML]:
    """创建底部状态栏（通过 list 引用实现 agent 切换后自动更新）"""
    def toolbar() -> HTML:
        agent: TaskAgent = agent_ref[0]
        return HTML(
            f"  <b>{agent.profile.name}</b>"
            f"  │  {agent.model or '未设置'}"
            f"  │  msgs: {len(agent.messages)}"
        )
    return toolbar


def main() -> None:
    """CLI 主函数"""
    # 抑制日志输出到终端（文件日志不受影响）
    import vnag.tracer as _tracer
    _tracer._stdout_enabled = False

    args: argparse.Namespace = _parse_args()

    # 创建 Gateway（从 cli_setting.json 读取配置）
    gateway = create_gateway()

    # 初始化引擎
    engine: AgentEngine = AgentEngine(gateway)
    engine.init()

    # 创建智能体
    agent: TaskAgent = _create_agent(engine)

    # 初始化渲染器和桥接
    renderer: Renderer = Renderer()
    bridge: StreamBridge = StreamBridge(agent, renderer)

    # 非交互模式：执行单次任务后退出
    if args.task:
        bridge.run(args.task)
        return

    # 用 list 包装 agent 引用，使 toolbar 和主循环能同步更新
    agent_ref: list[TaskAgent] = [agent]

    # 交互模式
    session: PromptSession = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        completer=CliCompleter(),
        bottom_toolbar=_make_toolbar(agent_ref),
    )

    renderer.show_welcome(agent)

    while True:
        try:
            user_input: str = session.prompt(
                HTML("<ansigreen><b>You › </b></ansigreen>")
            ).strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        # 斜杠命令
        if user_input.startswith("/"):
            try:
                agent, bridge = handle_command(
                    user_input, engine, agent, bridge, renderer,
                )
                agent_ref[0] = agent
            except EOFError:
                break
            continue

        # 普通对话
        bridge.run(user_input)

    renderer.show_goodbye()
