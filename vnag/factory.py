from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .gateway import BaseGateway
    from .embedder import BaseEmbedder

from .utility import load_json, save_json
from .gateways import get_gateway_class
from .gateway import BaseGateway
from .ui.setting import load_gateway_type, load_embedder_type


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


# ============================================================
# Embedder 相关
# ============================================================

# Embedder 类型列表
EMBEDDER_TYPES: list[str] = ["OpenAI", "DashScope"]

# Embedder 默认配置
EMBEDDER_DEFAULTS: dict[str, dict[str, str]] = {
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model_name": "text-embedding-3-small"
    },
    "DashScope": {
        "api_key": "",
        "model_name": "text-embedding-v3"
    }
}

# 模块级缓存: (embedder_type, setting_hash, embedder_instance)
_embedder_cache: tuple[str, str, "BaseEmbedder"] | None = None


def load_embedder_setting(embedder_type: str) -> dict[str, Any]:
    """加载指定 embedder 的配置"""
    filename: str = f"embedder_{embedder_type.lower()}.json"
    saved: dict[str, Any] = load_json(filename)

    # 合并默认配置
    defaults: dict[str, str] = EMBEDDER_DEFAULTS.get(embedder_type, {})
    result: dict[str, Any] = {**defaults, **saved}

    return result


def save_embedder_setting(embedder_type: str, setting: dict[str, Any]) -> None:
    """保存指定 embedder 的配置"""
    filename: str = f"embedder_{embedder_type.lower()}.json"
    save_json(filename, setting)


def _compute_setting_hash(embedder_type: str, setting: dict[str, Any]) -> str:
    """计算配置的哈希值，用于缓存判断"""
    import hashlib
    import json
    content: str = f"{embedder_type}:{json.dumps(setting, sort_keys=True)}"
    return hashlib.md5(content.encode()).hexdigest()


def create_embedder(embedder_type: str | None = None) -> "BaseEmbedder":
    """根据配置创建 embedder 实例

    Args:
        embedder_type: embedder 类型，为 None 时使用当前配置的类型

    Returns:
        BaseEmbedder 实例
    """
    from .embedder import BaseEmbedder
    from .embedders.openai_embedder import OpenaiEmbedder
    from .embedders.dashscope_embedder import DashscopeEmbedder

    # 获取类型
    if embedder_type is None:
        embedder_type = load_embedder_type()

    # 加载配置
    setting: dict[str, Any] = load_embedder_setting(embedder_type)

    # 创建实例
    embedder: BaseEmbedder
    if embedder_type == "OpenAI":
        embedder = OpenaiEmbedder(
            api_key=setting["api_key"],
            base_url=setting["base_url"],
            model_name=setting["model_name"]
        )
    elif embedder_type == "DashScope":
        embedder = DashscopeEmbedder(
            api_key=setting["api_key"],
            model_name=setting["model_name"]
        )
    else:
        raise ValueError(f"不支持的 embedder 类型: {embedder_type}")

    return embedder


def get_embedder() -> "BaseEmbedder":
    """获取 embedder 实例（带缓存）

    如果配置未改变，返回缓存实例；否则创建新实例。

    Returns:
        BaseEmbedder 实例
    """
    global _embedder_cache

    # 获取当前配置
    embedder_type: str = load_embedder_type()
    setting: dict[str, Any] = load_embedder_setting(embedder_type)
    current_hash: str = _compute_setting_hash(embedder_type, setting)

    # 检查缓存是否有效
    if _embedder_cache is not None:
        cached_type, cached_hash, cached_embedder = _embedder_cache
        if cached_type == embedder_type and cached_hash == current_hash:
            return cached_embedder

    # 创建新实例并缓存
    from .embedder import BaseEmbedder
    embedder: BaseEmbedder = create_embedder(embedder_type)
    _embedder_cache = (embedder_type, current_hash, embedder)

    return embedder


def clear_embedder_cache() -> None:
    """清除 embedder 缓存"""
    global _embedder_cache
    _embedder_cache = None
