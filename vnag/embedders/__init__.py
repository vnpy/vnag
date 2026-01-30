"""Embedder 注册表"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vnag.embedder import BaseEmbedder

from .openai_embedder import OpenaiEmbedder
from .dashscope_embedder import DashscopeEmbedder
from .sentence_embedder import SentenceEmbedder


# Embedder 类型名称到类的映射
EMBEDDER_CLASSES: dict[str, type["BaseEmbedder"]] = {
    OpenaiEmbedder.default_name: OpenaiEmbedder,
    DashscopeEmbedder.default_name: DashscopeEmbedder,
    SentenceEmbedder.default_name: SentenceEmbedder,
}


def get_embedder_names() -> list[str]:
    """获取所有可用的 embedder 名称列表"""
    return list(EMBEDDER_CLASSES.keys())


def get_embedder_class(name: str) -> type["BaseEmbedder"]:
    """根据名称获取 embedder 类，如果名称不存在则返回 OpenaiEmbedder"""
    return EMBEDDER_CLASSES.get(name, OpenaiEmbedder)
