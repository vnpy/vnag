# Segmenter 分段器

分段器负责把原始文档切分成适合检索的片段（`Segment`）。

## BaseSegmenter 基类

VNAG 的分段器统一接口是 `parse()`：

```python
from vnag.object import Segment
from vnag.segmenter import BaseSegmenter


class BaseSegmenter:
    def parse(self, text: str, metadata: dict) -> list[Segment]:
        """解析并返回 Segment 列表。"""
        raise NotImplementedError
```

建议你在 `metadata` 里至少提供：

- `source`：文档来源（通常是绝对路径字符串）。**注意：ChromaDB 向量库强制要求此字段**，它会使用 `source + chunk_index` 来生成唯一的文档 ID。

:::{note}
`Segment.metadata` 的类型是 `dict[str, str]`，所有值必须是字符串类型。如需存储非字符串数据，请先转换为字符串。
:::

## SimpleSegmenter

通用文本分段：按固定长度切分，支持 overlap。

```python
from vnag.segmenters.simple_segmenter import SimpleSegmenter

segmenter = SimpleSegmenter(chunk_size=1000, overlap=100)
segments = segmenter.parse("长文本...", metadata={"source": "doc.txt"})
```

## MarkdownSegmenter

按 Markdown 标题组织章节，并对超长章节做二次分块。

```python
from vnag.segmenters.markdown_segmenter import MarkdownSegmenter

segmenter = MarkdownSegmenter(chunk_size=2000)
segments = segmenter.parse("# 标题\n内容...", metadata={"source": "README.md"})
```

## PythonSegmenter

按 Python AST 的类/函数结构切分，并对超长章节做二次分块。

```python
from vnag.segmenters.python_segmenter import PythonSegmenter

segmenter = PythonSegmenter(chunk_size=2000)
segments = segmenter.parse("def f():\n  pass\n", metadata={"source": "a.py"})
```

## CppSegmenter

按 C++ AST（libclang）切分。

```python
from vnag.segmenters.cpp_segmenter import CppSegmenter

segmenter = CppSegmenter(chunk_size=2000)
segments = segmenter.parse("int main() {}", metadata={"source": "a.cpp"})
```


