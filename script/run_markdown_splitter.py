from vnag.splitters.markdown_splitter import MarkdownSplitter
from vnag.utility import read_text_file


def main() -> None:
    """从文件读取 Markdown 文本并分块"""
    # 直接写入Markdown文件路径，例如：r"E:\\docs\\note.md"
    FILE_PATH: str = r"D:\test\.vnag\docs\community\info\veighna_station.md"

    # 读取文件内容
    text: str = read_text_file(FILE_PATH)

    # 创建分块器
    splitter = MarkdownSplitter(chunk_size=120)
    metadata = {"source": FILE_PATH, "file_type": "md"}

    # 分块
    chunks = splitter.split_text(text, metadata)

    # 打印示例结果
    print(f"chunks: {len(chunks)}")
    for i, ch in enumerate(chunks[:6]):
        print(f"[{i}] len={len(ch.text)} title={ch.metadata.get('section_title','')} part={ch.metadata.get('section_part','')}\n{ch.text[:120]}\n---")


if __name__ == "__main__":
    main()
