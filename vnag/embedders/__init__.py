"""Embedder 注册表"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vnag.embedder import BaseEmbedder



# 与各 embedder 的 default_name 一致，供名称列表与分支匹配共用
_OPENAI = "OpenAI"
_DASHSCOPE = "DashScope"
_SENTENCE = "Sentence"


def get_embedder_names() -> list[str]:
    """获取所有可用的 embedder 名称列表"""
    return [_OPENAI, _DASHSCOPE, _SENTENCE]


def get_embedder_class(name: str) -> type["BaseEmbedder"]:
    """根据名称获取 embedder 类，如果名称不存在则返回 OpenaiEmbedder"""
    if name == _OPENAI:
        from .openai_embedder import OpenaiEmbedder
        return OpenaiEmbedder
    elif name == _DASHSCOPE:
        from .dashscope_embedder import DashscopeEmbedder
        return DashscopeEmbedder
    elif name == _SENTENCE:
        from .sentence_embedder import SentenceEmbedder
        return SentenceEmbedder
    else:
        from .openai_embedder import OpenaiEmbedder
        return OpenaiEmbedder
