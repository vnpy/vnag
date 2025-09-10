from vnag.splitters.python_splitter import PythonSplitter
from vnag.utility import read_text_file


def main() -> None:
    """从文件读取 Python 源码并分块"""
    # 直接写入Python文件路径，例如：r"E:\\code\\demo.py"
    FILE_PATH: str = r"E:\GitHub\vnag\vnag\gateway.py"

    # 读取文件内容
    text: str = read_text_file(FILE_PATH)

    # 创建分块器
    splitter = PythonSplitter(chunk_size=120)
    metadata = {"source": FILE_PATH, "file_type": "py"}

    # 分块
    chunks = splitter.split_text(text, metadata)

    print(f"chunks: {len(chunks)}")
    # 打印示例结果
    for i, ch in enumerate(chunks[:6]):
        md = ch.metadata
        print(
            f"[{i}] len={len(ch.text)} "
            f"title={md.get('section_title','')} "
            f"order={md.get('section_order','')} "
            f"part={md.get('section_part','')} "
            f"container={md.get('container_class','')} "
            f"qname={md.get('qualified_name','')}\n"
            f"{ch.text[:120]}\n---"
        )


if __name__ == "__main__":
    main()
