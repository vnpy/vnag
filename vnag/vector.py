from abc import ABC, abstractmethod

from .object import Segment


class BaseVector(ABC):
    """
    向量存储的抽象基类。

    该接口定义了所有向量存储实现必须遵循的统一规范，
    涵盖了文档的增删改查以及核心的相似性检索功能。
    """

    @abstractmethod
    def add_segments(self, segments: list[Segment]) -> list[str]:
        """
        将一批文档块添加到向量存储中。

        此方法负责接收文档块，在内部完成文本的向量化，
        并将其与元数据一同存入数据库。

        Args:
            segments (list[Segment]): 需要添加的文档块对象列表。

        Returns:
            list[str]: 成功存入的文档块的ID列表。
        """
        pass

    @abstractmethod
    def retrieve(self, query_text: str, k: int = 5, filter: dict | None = None) -> list[Segment]:
        """
        根据给定的文本查询，执行相似性检索。

        这是 RAG 流程的核心，用于根据用户问题找回最相关的知识片段。

        Args:
            query_text (str): 用于搜索的自然语言查询字符串。
            k (int, optional): 希望返回的最相似结果的数量。默认为 5。
            filter (dict | None, optional): 元数据过滤条件。默认为 None。

        Returns:
            list[Segment]: 检索结果的列表，按相关性排序。
        """
        pass

    @abstractmethod
    def delete_segments(self, segment_ids: list[str]) -> bool:
        """
        根据文档ID列表，从存储中删除一个或多个文档。

        Args:
            segment_ids (list[str]): 要删除的文档的唯一ID列表。

        Returns:
            bool: 如果所有指定的文档都成功删除或原本就不存在，则返回 True。
                  如果在删除过程中发生错误，则返回 False。
        """
        pass

    @abstractmethod
    def get_segments(self, segment_ids: list[str]) -> list[Segment]:
        """
        根据文档ID列表，直接获取原始的文档块。

        此方法用于精确查找，而非语义搜索。

        Args:
            segment_ids (list[str]): 要获取的文档的唯一ID列表。

        Returns:
            list[Segment]: 找到的 Segment 对象列表。
                                 如果某个ID不存在，则结果中不包含该项。
        """
        pass

    @property
    @abstractmethod
    def count(self) -> int:
        """
        获取向量存储中的文档总数（只读属性）。
        """
        pass
