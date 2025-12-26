"""Gateway 注册表"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vnag.gateway import BaseGateway

from .openai_gateway import OpenaiGateway
from .anthropic_gateway import AnthropicGateway
from .dashscope_gateway import DashscopeGateway
from .deepseek_gateway import DeepseekGateway
from .minimax_gateway import MinimaxGateway
from .bailian_gateway import BailianGateway
from .openrouter_gateway import OpenrouterGateway


# Gateway 类型名称到类的映射
GATEWAY_CLASSES: dict[str, type["BaseGateway"]] = {
    OpenaiGateway.default_name: OpenaiGateway,
    AnthropicGateway.default_name: AnthropicGateway,
    DashscopeGateway.default_name: DashscopeGateway,
    DeepseekGateway.default_name: DeepseekGateway,
    MinimaxGateway.default_name: MinimaxGateway,
    BailianGateway.default_name: BailianGateway,
    OpenrouterGateway.default_name: OpenrouterGateway,
}


def get_gateway_names() -> list[str]:
    """获取所有可用的 gateway 名称列表"""
    return list(GATEWAY_CLASSES.keys())


def get_gateway_class(name: str) -> type["BaseGateway"]:
    """根据名称获取 gateway 类，如果名称不存在则返回 OpenaiGateway（最通用）"""
    return GATEWAY_CLASSES.get(name, OpenaiGateway)
