"""CLI 配置管理与 Gateway 创建（不依赖 Qt/UI 模块）"""

from typing import Any

from ..gateway import BaseGateway
from ..gateways import get_gateway_class
from ..utility import load_json, save_json


CLI_SETTING_FILENAME: str = "cli_setting.json"


def load_cli_setting() -> dict[str, str]:
    """加载 CLI 配置"""
    return load_json(CLI_SETTING_FILENAME)


def save_cli_setting(setting: dict[str, str]) -> None:
    """保存 CLI 配置"""
    save_json(CLI_SETTING_FILENAME, setting)


def get_cli_value(key: str, default: str = "") -> str:
    """获取 CLI 配置项"""
    setting: dict[str, str] = load_cli_setting()
    return setting.get(key, default)


def set_cli_value(key: str, value: str) -> None:
    """设置 CLI 配置项并持久化"""
    setting: dict[str, str] = load_cli_setting()
    setting[key] = value
    save_cli_setting(setting)


def create_gateway() -> BaseGateway:
    """
    根据 cli_setting.json 中的 gateway_name 创建 Gateway 实例

    连接参数从 .vnag/connect_{type}.json 加载（与 GUI 共用）。
    """
    setting: dict[str, str] = load_cli_setting()
    gateway_name: str = setting.get("gateway_name", "OpenAI")

    # 加载连接配置（与 GUI 共用同一份文件）
    connect_filename: str = f"connect_{gateway_name.lower()}.json"
    connect_setting: dict[str, Any] = load_json(connect_filename)

    # 创建并初始化
    gateway_cls: type[BaseGateway] = get_gateway_class(gateway_name)
    gateway: BaseGateway = gateway_cls()
    gateway.init(connect_setting)

    return gateway
