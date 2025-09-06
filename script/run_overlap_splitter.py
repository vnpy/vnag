from pathlib import Path
from vnag.splitters.overlap_splitter import OverlapSplitter
from vnag.utility import read_text_file


def main() -> None:
    """从文件读取文本并使用 OverlapSplitter 分块"""
    # 直接写入文本文件路径，例如：r"E:\docs\note.txt"
    # 读取文件内容
    FILE_PATH: str = r"D:\test\.vnag\docs\community\info\veighna_station.md"

    # 读取文件内容
    text: str = read_text_file(FILE_PATH)

    # 创建分块器
    splitter = OverlapSplitter(chunk_size=200, overlap=40)
    file_type: str = Path(FILE_PATH).suffix.lstrip(".").lower()
    metadata = {"source": FILE_PATH, "file_type": file_type}

    # 分块
    chunks = splitter.split_text(text, metadata)

    # 打印分块结果（这里打印完整ch.text才能看到overlap效果）
    print(f"chunks: {len(chunks)}")
    for i, ch in enumerate(chunks[:6]):
        print(
            f"[{i}] len={len(ch.text)} title={ch.metadata.get('section_title','')} "
            f"part={ch.metadata.get('section_part','')}\n{ch.text}\n---"
        )


if __name__ == "__main__":
    main()


