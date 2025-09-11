from vnag.segmenters.markdown_segmenter import MarkdownSegmenter


def main() -> None:
    """运行简单的文本分段器"""
    segmenter = MarkdownSegmenter()

    with open("veighna_station.md", encoding="utf-8") as f:
        text: str = f.read()

    metadata = {"source": "veighna_station.md"}

    segments = segmenter.parse(text, metadata)

    for segment in segments:
        print("-" * 30)
        print(segment.text)
        print(segment.metadata)


if __name__ == "__main__":
    main()
