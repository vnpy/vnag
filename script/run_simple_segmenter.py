from vnag.segmenters.simple_segmenter import SimpleSegmenter


def main() -> None:
    """运行简单的文本分段器"""
    segmenter = SimpleSegmenter()

    with open("./knowledge/backtesting.py", encoding="utf-8") as f:
        text: str = f.read()

    metadata = {"source": "test"}

    segments = segmenter.parse(text, metadata)

    for segment in segments:
        print(segment.text)


if __name__ == "__main__":
    main()
