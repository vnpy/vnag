from pathlib import Path

from vnag.segmenters.python_segmenter import PythonSegmenter


def main() -> None:
    """运行简单的文本分段器"""
    segmenter = PythonSegmenter()

    base_dir: Path = Path(__file__).resolve().parent.parent
    filepath: Path = (base_dir / "rag/knowledge/backtesting.py").resolve()
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
