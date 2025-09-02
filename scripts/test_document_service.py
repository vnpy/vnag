"""DocumentService 简单功能测试。

条件：
- 仅测试 .md 的最小功能路径，避免外部依赖；

期望：
- 返回至少一条分块，且基础元数据字段正确。
"""

from pathlib import Path

from vnag.document_service import DocumentService, DocumentChunk


def test_process_file_md_basic(tmp_path: Path) -> None:
    """简单功能测试：处理 .md，返回非空分块与必要元数据。"""
    p = tmp_path / "a.md"
    p.write_text("# Title\n\nHello world.", encoding="utf-8")

    ds = DocumentService()
    chunks = ds.process_file(str(p))

    assert isinstance(chunks, list) and len(chunks) >= 1  # 非空列表
    c0: DocumentChunk = chunks[0]  # 首块
    assert isinstance(c0.text, str) and len(c0.text) > 0  # 文本非空
    assert c0.metadata.get("filename") == "a.md"  # 文件名
    assert c0.metadata.get("file_type") == ".md"  # 类型
    assert c0.metadata.get("source") == str(p)  # 源路径
    assert c0.metadata.get("chunk_index") == "0"  # 索引0


def test_markdown_headings_chunking(tmp_path: Path) -> None:
    """Markdown 标题应触发结构化分块：#/##/### 各成一段。"""
    md = (
        "# H1\n"
        "para1\n\n"
        "## H2\n"
        "para2\n\n"
        "### H3\n"
        "para3\n"
    )
    p = tmp_path / "t.md"
    p.write_text(md, encoding="utf-8")
    ds = DocumentService()
    chunks = ds.process_file(str(p))
    assert len(chunks) == 3  # 三个标题对应三段
    assert chunks[0].text.lstrip().startswith("# H1")  # 首段以 H1 开头
    assert chunks[1].text.lstrip().startswith("## H2")  # 次段以 H2 开头
    assert chunks[2].text.lstrip().startswith("### H3")  # 末段以 H3 开头


def test_markdown_code_fence_protection(tmp_path: Path) -> None:
    """代码块应被完整保留在同一段内，不在 ``` 中间断开。"""
    md = (
        "# Sec\n\n"
        "````\n"
        "print('a')\n"
        "line2\n"
        "````\n\n"
        "tail\n"
    )
    # 用三反引号会和本测试文件混淆，这里用四个作为占位，仍会被识别为 fenced 栅栏
    p = tmp_path / "c.md"
    p.write_text(md, encoding="utf-8")
    ds = DocumentService()
    chunks = ds.process_file(str(p))
    assert len(chunks) == 1  # 无新标题，因此整体应为一段
    t = chunks[0].text
    assert t.count("````") == 2  # 起止栅栏都在，未被拆断
    assert "print('a')" in t and "line2" in t  # 代码内容完整


def test_markdown_long_paragraph_split(tmp_path: Path) -> None:
    """超出 chunk_size 的长段应被定长切分为多段（仅 .md）。"""
    long = "A" * 120  # 单一超长段，无句点
    md = "# H\n\n" + long
    p = tmp_path / "l.md"
    p.write_text(md, encoding="utf-8")
    ds = DocumentService()
    ds.chunk_size = 50  # 收紧阈值以触发切分
    chunks = ds.process_file(str(p))
    assert len(chunks) >= 2  # 应产生至少两段
    assert sum(len(c.text) for c in chunks) >= len("# H\n\n" + long) - 5  # 长度基本覆盖原文
