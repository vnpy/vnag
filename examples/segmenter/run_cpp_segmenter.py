from pathlib import Path

from vnag.segmenters.cpp_segmenter import CppSegmenter


def main() -> None:
    """运行简单的文本分段器"""
    segmenter = CppSegmenter()

    filepath: Path = Path("../rag/knowledge/include/ctp/ThostFtdcMdApi.h").resolve()
    with open(filepath, encoding="gbk", errors="ignore") as f:
        text: str = f.read()

    file_type: str = filepath.suffix.lower().lstrip(".")
    metadata: dict[str, str] = {
        "filename": filepath.name,
        "source": str(filepath),
        "file_type": file_type
    }

    segments = segmenter.parse(text, metadata)

    for seg in segments:
        print("-" * 30)
        print(seg.text)
        print(seg.metadata)


if __name__ == "__main__":
    main()
