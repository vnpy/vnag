from vnag.object import Segment
from vnag.vectors.chromadb_vector import ChromaVector


def main() -> None:
    """执行向量检索"""
    # 创建向量库
    vector: ChromaVector = ChromaVector()

    # 执行查询
    segments: list[Segment] = vector.retrieve(query_text="如何实现 VeighNa Station 登录", k=5)
    for segment in segments:
        print("-" * 30)
        print(f"# 相关性得分: {segment.score}")
        print(f"# metadata元数据: {segment.metadata}")
        print(f"# 文本内容: {segment.text}")


if __name__ == "__main__":
    main()
