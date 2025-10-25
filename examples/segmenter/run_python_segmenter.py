from vnag.segmenters.python_segmenter import PythonSegmenter


def main() -> None:
    """运行简单的文本分段器"""
    segmenter = PythonSegmenter()

    with open("./knowledge/backtesting.py", encoding="utf-8") as f:
        text: str = f.read()

    metadata = {"source": "backtesting.py"}

    segments = segmenter.parse(text, metadata)

    for segment in segments:
        print("-" * 30)
        print(segment.text)
        print(segment.metadata)


if __name__ == "__main__":
    main()
