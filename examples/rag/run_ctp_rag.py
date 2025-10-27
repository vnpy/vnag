from pathlib import Path

from vnag.embedders.sentence_embedder import SentenceEmbedder
from vnag.object import Message, Request, Role, Segment
from vnag.utility import load_json
from vnag.gateways.openai_gateway import OpenaiGateway
from vnag.segmenters.cpp_segmenter import CppSegmenter
from vnag.vectors.chromadb_vector import ChromaVector


def import_knowledge(vector: ChromaVector) -> None:
    """
    遍历 CTP 头文件目录，使用 CppSegmenter 解析并将其插入向量数据库。

    该函数会扫描 `./knowledge/include/ctp` 目录下的所有 `.h` 文件，
    使用 GBK 编码读取文件内容，然后通过 CppSegmenter 将代码解析
    为结构化的知识片段（Segment），最后将这些片段存入 ChromaDB
    向量数据库中，以便后续的检索操作。

    Args:
        vector (ChromaVector): 向量数据库的实例。
    """
    segmenter: CppSegmenter = CppSegmenter()

    # 构建知识库目录的绝对路径，确保在任何工作目录下都能正确找到
    knowledge_path: Path = Path("./knowledge/include/ctp")
    print(f"开始从目录 {knowledge_path} 导入知识库...")

    # 遍历所有.h头文件
    header_files: list[Path] = list(knowledge_path.glob("*.h"))
    print(f"发现 {len(header_files)} 个 .h 文件，开始解析入库...")

    for h_file in header_files:
        # CTP的头文件通常使用GBK编码
        with open(h_file, encoding="gbk") as f:
            text: str = f.read()

        # 解析文件内容
        file_type: str = h_file.suffix.lower().lstrip(".")
        metadata: dict = {
            "filename": str(h_file.name),
            "source": str(h_file.resolve()),
            "file_type": file_type
        }
        segments: list[Segment] = segmenter.parse(text, metadata)

        # 将解析出的知识片段写入向量库
        if segments:
            vector.add_segments(segments)
            print(f"成功处理文件: {h_file.name}, 新增 {len(segments)} 个知识片段。")


def query_vector(vector: ChromaVector, question: str, k: int = 5) -> list[Segment]:
    """
    从向量数据库中查询与问题相关的知识片段。

    Args:
        vector (ChromaVector): 向量数据库的实例。
        question (str): 用户提出的问题。
        k (int): 希望返回的相关知识片段数量。

    Returns:
        list[Segment]: 查询到的相关知识片段列表。
    """
    print(f"\n正在执行向量检索，查询: '{question}'...")
    segments: list[Segment] = vector.retrieve(query_text=question, k=k)

    print(f"检索完成，找到 {len(segments)} 个相关片段。")
    for i, segment in enumerate(segments):
        print("-" * 30)
        print(f"相关片段 {i+1}:")
        print(f"  - 相关性得分: {segment.score:.4f}")
        print(f"  - 来源: {segment.metadata.get('source', 'N/A')}")
    print("-" * 30)

    return segments


def generate_answer(
    gateway: OpenaiGateway,
    vector: ChromaVector,
    question: str,
    model: str = "gpt-4o",
) -> str:
    """
    生成问题的回答。

    该函数首先调用 query_vector 从向量数据库中检索与问题相关的上下文信息，
    然后将这些信息与原始问题组合成一个提示（Prompt），最后通过 OpenAI
    的语言模型生成最终的回答。

    Args:
        gateway (OpenaiGateway): AI 模型的调用接口。
        vector (ChromaVector): 向量数据库的实例。
        question (str): 用户提出的问题。
        model (str): 希望使用的 AI 模型名称。

    Returns:
        str: AI 模型生成的回答。
    """
    # 1. 从向量库查询相关知识
    segments: list[Segment] = query_vector(vector, question)

    # 2. 构建Prompt
    context: str = "\n\n".join([seg.text for seg in segments])
    prompt: str = (
        "你是一个专业的CTP（Comprehensive Transaction Platform）专家。"
        "请基于下面提供的CTP API头文件代码片段作为知识库，用中文回答用户的问题。\n"
        "如果知识库内容与问题无关，请明确告知并拒绝回答。\n\n"
        f"--- 知识库 ---\n{context}\n\n"
        f"--- 用户问题 ---\n{question}\n"
    )

    # 3. 创建AI请求
    request: Request = Request(
        model=model,
        messages=[
            Message(role=Role.USER, content=prompt),
        ],
        temperature=0.2,  # 设置较低的温度以获得更稳定、更精确的回答
    )

    # 4. 调用AI模型生成回答
    print("\n正在调用 AI 模型生成回答...")
    response: str = ""
    for chunk in gateway.stream(request):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            response += chunk.content

    print("\n" + "=" * 50)
    return response


def main() -> None:
    """
    CTP RAG Demo主程序入口。
    """
    # 1. 初始化向量数据库
    # ChromaVector 默认会在当前工作目录下创建并使用 chroma 文件夹进行数据持久化
    embedder: SentenceEmbedder = SentenceEmbedder("BAAI/bge-large-zh-v1.5")
    vector: ChromaVector = ChromaVector(name="ctp", embedder=embedder)

    print(f"向量数据库初始化完成，当前知识总数：{vector.count}")

    # 2. 导入知识库（如果为空）
    # 为避免重复导入，可以增加判断逻辑，例如只在数据库为空时执行
    if not vector.count:
        import_knowledge(vector)
        print(f"知识库导入完成，当前知识总数：{vector.count}")

    # 3. 初始化AI网关
    setting: dict = load_json("connect_openai.json")

    gateway: OpenaiGateway = OpenaiGateway()
    gateway.init(setting)
    print("\nAI 网关初始化成功。")

    # 4. 提出问题并生成回答
    question: str = "请问CTP API中的用户登录功能，发起请求和返回收到的数据字段分别有哪些？"
    print(f"\n用户问题: {question}")

    answer: str = generate_answer(gateway, vector, question)
    print(f"\n最终回答:\n{answer}")


if __name__ == "__main__":
    main()
