from pathlib import Path

from vnag.segmenters.simple_segmenter import SimpleSegmenter


def main() -> None:
    """运行简单的文本分段器"""
    segmenter = SimpleSegmenter(chunk_size=500)

    filepath: Path = Path("../rag/knowledge/backtesting.py").resolve()
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


if __name__ == "__main__":
    main()
