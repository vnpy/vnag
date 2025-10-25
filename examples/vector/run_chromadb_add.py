from vnag.object import Segment
from vnag.segmenters.markdown_segmenter import MarkdownSegmenter
from vnag.vectors.chromadb_vector import ChromaVector


def main() -> None:
    """将指定 Markdown 文件切分后写入本地 Chroma 向量库"""
    # 读取文件内容
    filename: str = "veighna_station.md"
    with open(f"./knowledge/{filename}", encoding="utf-8") as f:
        text: str = f.read()

    # 拆分文本为块
    segmenter: MarkdownSegmenter = MarkdownSegmenter(chunk_size=2000)
    segments: list[Segment] = segmenter.parse(text, metadata={"filename": filename})
    print(f"总块数: {len(segments)}")

    # 写入向量库
    vector: ChromaVector = ChromaVector()
    vector.add_segments(segments)
    print(f"写入完成，向量库中共有 {vector.count} 个块")


if __name__ == "__main__":
    main()
