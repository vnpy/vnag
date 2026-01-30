from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .gateway import BaseGateway

from .utility import load_json, save_json
from .gateways import get_gateway_class
from .gateway import BaseGateway
from .ui.setting import load_gateway_type


# ============================================================
# Gateway 相关
# ============================================================

def load_gateway_setting(gateway_type: str) -> dict[str, Any]:
    """加载指定 gateway 的连接设置"""
    filename: str = f"connect_{gateway_type.lower()}.json"
    return load_json(filename)


def save_gateway_setting(gateway_type: str, setting: dict[str, Any]) -> None:
    """保存指定 gateway 的连接设置"""
    filename: str = f"connect_{gateway_type.lower()}.json"
    save_json(filename, setting)


def create_gateway() -> BaseGateway:
    """根据当前配置创建AI服务接口实例"""
    # 加载当前选择的 gateway 类型
    gateway_type: str = load_gateway_type()

    # 加载连接设置
    gateway_cls: type[BaseGateway] = get_gateway_class(gateway_type)
    setting: dict[str, Any] = load_gateway_setting(gateway_type)

    # 创建实例并初始化
    gateway: BaseGateway = gateway_cls()
    gateway.init(setting)

    return gateway
