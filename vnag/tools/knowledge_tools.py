from typing import Any
from pathlib import Path

from vnag.local import LocalTool
from vnag.utility import get_folder_path
from vnag.factory import get_embedder_for_knowledge, list_knowledge_bases as _list_kb
from vnag.vectors.duckdb_vector import DuckVector


def list_knowledge_bases() -> list[str]:
    """
    获取本地已有的向量知识库名称列表。

    Returns:
        知识库名称列表，如 ["ctp_api", "vnpy_docs"]
    """
    return _list_kb()


def query_knowledge(
    db_name: str,
    query: str,
    k: int = 5
) -> list[dict[str, Any]]:
    """
    在指定的知识库中查询与问题相关的知识片段。

    Args:
        db_name: 知识库名称
        query: 查询问题
        k: 返回的片段数量，默认5

    Returns:
        相关知识片段列表，每个包含:
        - text: 片段文本
        - metadata: 元数据（source, chunk_index, section_title等）
        - score: 相似度分数（越小越相似）
    """
    # 检查知识库是否存在
    db_folder: Path = get_folder_path("duckdb_vector")
    db_path: Path = db_folder.joinpath(f"{db_name}.duckdb")

    if not db_path.exists():
        return [{"error": f"知识库 '{db_name}' 不存在"}]

    try:
        # 根据知识库配置获取对应的 embedder
        embedder = get_embedder_for_knowledge(db_name)
        vector = DuckVector(name=db_name, embedder=embedder)

        # 查询
        segments = vector.retrieve(query, k=k)

        # 转换为字典列表
        results: list[dict[str, Any]] = []
        for seg in segments:
            results.append({
                "text": seg.text,
                "metadata": seg.metadata,
                "score": seg.score
            })

        return results

    except ValueError as e:
        return [{"error": str(e)}]
    except Exception as e:
        return [{"error": f"查询失败: {str(e)}"}]


# 注册工具
list_knowledge_bases_tool = LocalTool(list_knowledge_bases)
query_knowledge_tool = LocalTool(query_knowledge)
