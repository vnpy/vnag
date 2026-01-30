"""知识库工具模块"""
from typing import Any

from vnag.local import LocalTool
from vnag.knowledge import list_knowledge_bases as _list_knowledge_bases
from vnag.knowledge import get_knowledge_vector


def list_knowledge_bases() -> list[dict[str, str]]:
    """
    获取本地已有的知识库列表。

    Returns:
        知识库列表，每个元素包含:
        - name: 知识库名称
        - description: 知识库描述
    """
    return _list_knowledge_bases()


def query_knowledge_base(
    name: str,
    query: str,
    k: int = 5
) -> list[dict[str, Any]]:
    """
    在指定的知识库中查询与问题相关的知识片段。

    Args:
        name: 知识库名称
        query: 查询问题
        k: 返回的片段数量，默认5

    Returns:
        相关知识片段列表，每个包含:
        - text: 片段文本
        - metadata: 元数据（source, chunk_index, section_title等）
        - score: 相似度分数（越小越相似）
    """
    try:
        vector = get_knowledge_vector(name)
        segments = vector.retrieve(query, k=k)

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
query_knowledge_base_tool = LocalTool(query_knowledge_base)
