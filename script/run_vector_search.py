from vnag.vector_service import VectorService


# 要先运行run_vector_add.py，将文件添加到向量库中
def main() -> None:
    """在本地 Chroma 向量库中进行相似度搜索"""
    vs = VectorService()

    query: str = "VeighNa Station 登录"
    k: int = 5

    results = vs.similarity_search(query=query, k=k)

    print(f"query={query}")
    print(f"topk={k}")
    for i, r in enumerate(results):
        text = r.get("text", "")
        meta = r.get("metadata", {})
        dist = r.get("distance", None)
        print(f"[{i}] dist={dist}\nmeta={meta}\n{text[:200]}\n---")


if __name__ == "__main__":
    main()
