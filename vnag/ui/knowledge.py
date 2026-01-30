"""知识库管理模块"""
from typing import Any
from pathlib import Path
from datetime import datetime
import json

from ..utility import get_folder_path, get_file_path
from ..embedder import BaseEmbedder


# 知识库存储目录
KNOWLEDGE_DIR: str = "knowledge"


def _get_metadata_path(name: str) -> Path:
    """获取知识库元数据文件路径"""
    folder: Path = get_folder_path(KNOWLEDGE_DIR)
    return folder.joinpath(f"{name}.json")


def _get_db_path(name: str) -> Path:
    """获取知识库数据库文件路径"""
    return get_file_path(f"{name}.duckdb")


def list_knowledge_bases() -> list[dict[str, str]]:
    """列出所有知识库

    Returns:
        知识库列表，每个元素包含 name 和 description
    """
    folder: Path = get_folder_path(KNOWLEDGE_DIR)
    result: list[dict[str, str]] = []

    for f in folder.glob("*.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                meta: dict[str, Any] = json.load(fp)
                result.append({
                    "name": meta["name"],
                    "description": meta.get("description", "")
                })
        except Exception:
            pass

    return result


def create_knowledge_base(
    name: str,
    embedder_type: str,
    embedder_setting: dict[str, Any],
    description: str = ""
) -> None:
    """创建知识库

    Args:
        name: 知识库名称
        embedder_type: Embedder 类型（OpenAI / DashScope / Sentence）
        embedder_setting: Embedder 构造参数
        description: 知识库描述
    """
    path: Path = _get_metadata_path(name)
    if path.exists():
        raise ValueError(f"知识库 '{name}' 已存在")

    metadata: dict[str, Any] = {
        "name": name,
        "description": description,
        "embedder_type": embedder_type,
        "embedder_setting": embedder_setting,
        "created_at": datetime.now().isoformat()
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)


def load_knowledge_base(name: str) -> dict[str, Any] | None:
    """加载知识库元数据

    Args:
        name: 知识库名称

    Returns:
        元数据字典，不存在则返回 None
    """
    path: Path = _get_metadata_path(name)
    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            return dict(json.load(f))
    except (json.JSONDecodeError, OSError):
        return None


def delete_knowledge_base(name: str) -> None:
    """删除知识库

    Args:
        name: 知识库名称
    """
    # 删除元数据文件
    _get_metadata_path(name).unlink(missing_ok=True)

    # 删除数据库文件
    _get_db_path(name).unlink(missing_ok=True)

    # 删除 WAL 文件
    wal_path: Path = _get_db_path(name).with_suffix(".duckdb.wal")
    wal_path.unlink(missing_ok=True)


def _create_embedder(embedder_type: str, setting: dict[str, Any]) -> BaseEmbedder:
    """根据类型和配置创建 Embedder 实例"""
    if embedder_type == "OpenAI":
        from ..embedders.openai_embedder import OpenaiEmbedder
        return OpenaiEmbedder(**setting)
    elif embedder_type == "DashScope":
        from ..embedders.dashscope_embedder import DashscopeEmbedder
        return DashscopeEmbedder(**setting)
    elif embedder_type == "Sentence":
        from ..embedders.sentence_embedder import SentenceEmbedder
        return SentenceEmbedder(**setting)
    else:
        raise ValueError(f"不支持的 Embedder 类型: {embedder_type}")


def get_knowledge_vector(name: str):
    """获取知识库向量存储（自动创建专属 Embedder）

    Args:
        name: 知识库名称

    Returns:
        DuckVector 实例
    """
    from ..vectors.duckdb_vector import DuckVector

    metadata: dict[str, Any] | None = load_knowledge_base(name)
    if metadata is None:
        raise ValueError(f"知识库 '{name}' 不存在")

    embedder_type: str = metadata["embedder_type"]
    setting: dict[str, Any] = metadata["embedder_setting"]

    # 创建专属 Embedder
    embedder: BaseEmbedder = _create_embedder(embedder_type, setting)

    # 创建向量存储，使用知识库专用目录
    return DuckVector(name=name, embedder=embedder)
