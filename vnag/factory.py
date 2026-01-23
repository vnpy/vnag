from typing import Any, TYPE_CHECKING
from pathlib import Path
from datetime import datetime

if TYPE_CHECKING:
    from .gateway import BaseGateway
    from .embedder import BaseEmbedder

from .utility import load_json, save_json, get_folder_path
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


# ============================================================
# Embedder 相关
# ============================================================

# Embedder 类型列表
EMBEDDER_TYPES: list[str] = ["OpenAI", "DashScope"]

# Embedder 默认配置（不含 API 密钥）
EMBEDDER_DEFAULTS: dict[str, dict[str, str]] = {
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "model_name": "text-embedding-3-small"
    },
    "DashScope": {
        "model_name": "text-embedding-v3"
    }
}


def load_embedder_setting(embedder_type: str) -> dict[str, Any]:
    """加载指定 embedder 类型的统一配置（主要是 API 密钥）"""
    filename: str = f"embedder_{embedder_type.lower()}.json"
    saved: dict[str, Any] = load_json(filename)

    # 合并默认配置
    defaults: dict[str, str] = EMBEDDER_DEFAULTS.get(embedder_type, {})
    result: dict[str, Any] = {**defaults, **saved}

    return result


def save_embedder_setting(embedder_type: str, setting: dict[str, Any]) -> None:
    """保存指定 embedder 类型的统一配置"""
    filename: str = f"embedder_{embedder_type.lower()}.json"
    save_json(filename, setting)


def create_embedder_from_config(
    embedder_type: str,
    config: dict[str, Any]
) -> "BaseEmbedder":
    """根据完整配置创建 embedder 实例

    Args:
        embedder_type: embedder 类型 (OpenAI / DashScope)
        config: 完整配置，包含 api_key, base_url(可选), model_name

    Returns:
        BaseEmbedder 实例
    """
    from .embedder import BaseEmbedder
    from .embedders.openai_embedder import OpenaiEmbedder
    from .embedders.dashscope_embedder import DashscopeEmbedder

    embedder: BaseEmbedder
    if embedder_type == "OpenAI":
        embedder = OpenaiEmbedder(
            api_key=config["api_key"],
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            model_name=config["model_name"]
        )
    elif embedder_type == "DashScope":
        embedder = DashscopeEmbedder(
            api_key=config["api_key"],
            model_name=config["model_name"]
        )
    else:
        raise ValueError(f"不支持的 embedder 类型: {embedder_type}")

    return embedder


# ============================================================
# 知识库元数据管理
# ============================================================

def get_knowledge_metadata_path(kb_name: str) -> Path:
    """获取知识库元数据文件路径"""
    db_folder: Path = get_folder_path("duckdb_vector")
    return db_folder.joinpath(f"{kb_name}.json")


def load_knowledge_metadata(kb_name: str) -> dict[str, Any] | None:
    """加载知识库元数据

    Args:
        kb_name: 知识库名称

    Returns:
        元数据字典，不存在则返回 None
    """
    import json
    meta_path: Path = get_knowledge_metadata_path(kb_name)

    if not meta_path.exists():
        return None

    try:
        with open(meta_path, encoding="utf-8") as f:
            return dict(json.load(f))
    except (json.JSONDecodeError, OSError):
        return None


def save_knowledge_metadata(kb_name: str, metadata: dict[str, Any]) -> None:
    """保存知识库元数据

    Args:
        kb_name: 知识库名称
        metadata: 元数据字典
    """
    import json
    meta_path: Path = get_knowledge_metadata_path(kb_name)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)


def delete_knowledge_metadata(kb_name: str) -> None:
    """删除知识库元数据"""
    meta_path: Path = get_knowledge_metadata_path(kb_name)
    if meta_path.exists():
        meta_path.unlink()


def list_knowledge_bases() -> list[str]:
    """列出所有知识库名称

    基于元数据文件（.json）列出知识库，而不是数据库文件（.duckdb），
    因为知识库创建时只生成元数据，数据库文件在导入文档时才创建。
    """
    db_folder: Path = get_folder_path("duckdb_vector")
    meta_files: list[Path] = list(db_folder.glob("*.json"))
    return [f.stem for f in meta_files]


def create_knowledge_base(
    kb_name: str,
    embedder_type: str,
    base_url: str,
    model_name: str,
    description: str = ""
) -> dict[str, Any]:
    """创建新知识库（保存元数据）

    Args:
        kb_name: 知识库名称
        embedder_type: Embedder 类型
        base_url: API 地址（OpenAI 类型时使用）
        model_name: 模型名称
        description: 描述

    Returns:
        创建的元数据字典
    """
    metadata: dict[str, Any] = {
        "name": kb_name,
        "embedder_type": embedder_type,
        "model_name": model_name,
        "description": description,
        "created_at": datetime.now().isoformat()
    }

    # OpenAI 类型需要保存 base_url
    if embedder_type == "OpenAI":
        metadata["base_url"] = base_url

    save_knowledge_metadata(kb_name, metadata)
    return metadata


def get_embedder_for_knowledge(kb_name: str) -> "BaseEmbedder":
    """根据知识库配置获取对应的 Embedder 实例

    Args:
        kb_name: 知识库名称

    Returns:
        BaseEmbedder 实例

    Raises:
        ValueError: 知识库不存在或配置无效
    """
    # 加载知识库元数据
    metadata: dict[str, Any] | None = load_knowledge_metadata(kb_name)
    if metadata is None:
        raise ValueError(f"知识库 '{kb_name}' 不存在或配置丢失")

    embedder_type: str = metadata["embedder_type"]

    # 加载统一的 API 密钥配置
    embedder_setting: dict[str, Any] = load_embedder_setting(embedder_type)

    # 合并配置：知识库特定配置 + 统一密钥
    config: dict[str, Any] = {
        "api_key": embedder_setting.get("api_key", ""),
        "model_name": metadata["model_name"]
    }

    # OpenAI 类型使用知识库指定的 base_url
    if embedder_type == "OpenAI":
        config["base_url"] = metadata.get(
            "base_url",
            embedder_setting.get("base_url", "https://api.openai.com/v1")
        )

    return create_embedder_from_config(embedder_type, config)
