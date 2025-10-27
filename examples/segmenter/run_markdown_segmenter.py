from pathlib import Path

from vnag.segmenters.markdown_segmenter import MarkdownSegmenter


def main() -> None:
    """运行简单的文本分段器"""
    segmenter = MarkdownSegmenter()

    filepath: Path = Path("../rag/knowledge/veighna_station.md").resolve()
    with open(filepath, encoding="utf-8") as f:
        text: str = f.read()

    file_type: str = filepath.suffix.lower().lstrip(".")
    metadata: dict[str, str] = {
        "filename": filepath.name,
        "source": str(filepath),
        "file_type": file_type
    }

    segments = segmenter.parse(text, metadata)

    for segment in segments:
        print("-" * 30)
        print(segment.text)
        print(segment.metadata)


if __name__ == "__main__":
    main()
