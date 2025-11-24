from vnag.embedders.sentence_embedder import SentenceEmbedder
from vnag.object import Segment
from vnag.vectors.chromadb_vector import ChromaVector


def main() -> None:
    """执行向量检索"""
    # 创建向量库（必须与写入时使用相同的 name 和 embedder）
    embedder: SentenceEmbedder = SentenceEmbedder("BAAI/bge-large-zh-v1.5")
    vector: ChromaVector = ChromaVector(name="bge", embedder=embedder)

    # 如使用 DashScope 写入，检索时也需使用相同的 name：
    # from vnag.embedders.dashscope_embedder import DashscopeEmbedder
    # embedder = DashscopeEmbedder(api_key="your_api_key", model_name="text-embedding-v3")
    # vector = ChromaVector(name="dashscope", embedder=embedder)

    # 如使用 OpenRouter 写入，检索时也需使用相同的 name：
    # from vnag.embedders.openai_embedder import OpenAIEmbedder
    # embedder = OpenAIEmbedder(
    #     base_url="https://openrouter.ai/api/v1",
    #     api_key="your_api_key",
    #     model_name="qwen/qwen3-embedding-8b"
    # )
    # vector = ChromaVector(name="openai", embedder=embedder)

    # 执行查询
    segments: list[Segment] = vector.retrieve(query_text="如何实现 VeighNa Station 登录", k=5)
    for segment in segments:
        print("-" * 30)
        print(f"# 相关性得分: {segment.score}")
        print(f"# metadata元数据: {segment.metadata}")
        print(f"# 文本内容: {segment.text}")


if __name__ == "__main__":
    main()
