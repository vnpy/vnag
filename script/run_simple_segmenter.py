from vnag.segmenters.simple_segmenter import SimpleSegmenter


def main() -> None:
    """运行简单的文本分段器"""
    segmenter = SimpleSegmenter()

    text = "这是一个简单的文本分段器，按固定长度切分文本，并支持重叠。"

    metadata = {"source": "test"}

    segments = segmenter.parse(text, metadata)

    for segment in segments:
        print(segment.text)


if __name__ == "__main__":
    main()
