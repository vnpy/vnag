from vnag.segmenters.cpp_segmenter import CppSegmenter


def main() -> None:
    """运行简单的文本分段器"""
    segmenter = CppSegmenter()

    src_path = r".\knowledge\include\ctp\ThostFtdcMdApi.h"
    with open(src_path, encoding="gbk", errors="ignore") as f:
        text: str = f.read()

    metadata = {"source": src_path}

    segments = segmenter.parse(text, metadata)

    for seg in segments:
        print("-" * 30)
        print(seg.text)
        print(seg.metadata)


if __name__ == "__main__":
    main()
