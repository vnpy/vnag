import ast
from typing import Any
from collections.abc import Generator

from vnag.object import Segment
from vnag.segmenter import BaseSegmenter


class PythonSegmenter(BaseSegmenter):
    """
    Python 代码分段器，它利用抽象语法树（AST）来创建结构化的、
    符合语法结构的文本段。
    """

    def __init__(self, chunk_size: int = 2000) -> None:
        """
        初始化 PythonSegmenter。

        参数:
            chunk_size: 每个文本块的最大长度，默认为 2000。
        """
        self.chunk_size: int = chunk_size

    def parse(self, text: str, metadata: dict[str, Any]) -> list[Segment]:
        """
        将输入的 Python 源码分割成一系列结构化的 Segment。

        处理流程:
        1. 调用 `ast_split` 函数，按顶层函数和类定义将源码分割成逻辑章节。
        2. 对于过长的章节，调用 `pack_lines` 按代码行进行打包，确保每个块不超过 `chunk_size`。
        3. 为每个最终的文本块创建 `Segment` 对象，并附加元数据。
        """
        if not text.strip():
            return []

        segments: list[Segment] = []
        segment_index: int = 0
        section_order: int = 0

        # 基于 AST 将代码分割成函数/类定义的章节
        sections: Generator[tuple[str, str], None, None] = ast_split(text)

        for title, content in sections:
            if not content.strip():
                continue

            chunks: list[str]
            # 如果一个章节内容过长，则调用行打包函数进一步切分
            if len(content) > self.chunk_size:
                chunks = pack_lines(content.splitlines(), self.chunk_size)
            else:
                chunks = [content]

            total_chunks: int = len(chunks)
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue

                # 为每个文本块创建独立的元数据副本，并添加分段信息
                chunk_meta: dict[str, Any] = metadata.copy()
                chunk_meta["chunk_index"] = str(segment_index)
                chunk_meta["section_title"] = title
                chunk_meta["section_order"] = str(section_order)
                chunk_meta["section_part"] = f"{i + 1}/{total_chunks}"

                segments.append(Segment(text=chunk, metadata=chunk_meta))
                segment_index += 1

            section_order += 1

        return segments


def ast_split(text: str) -> Generator[tuple[str, str], None, None]:
    """
    使用 AST 将 Python 代码分割成基于顶层定义的章节。

    该函数会依次产出 (yield) 在模块顶层定义的每个函数、类以及它们之间的
    模块级代码块。

    参数:
        text: 待分割的 Python 源码字符串。

    返回:
        一个生成器，每次产出一个元组 (章节标题, 章节内容)。
        标题可能是 "module" 或 "class MyClass", "def my_func"。
    """
    try:
        tree: ast.Module = ast.parse(text)
    except SyntaxError:
        yield "module", text
        return

    lines: list[str] = text.splitlines(keepends=True)
    last_node_end_line: int = 0

    # 产出第一个节点（函数/类）之前的模块级代码
    if tree.body:
        first_node: ast.AST = tree.body[0]
        first_node_start_line: int = first_node.lineno - 1
        if first_node_start_line > 0:
            module_header: str = "".join(lines[0:first_node_start_line]).strip()
            if module_header:
                yield "module", module_header
            last_node_end_line = first_node_start_line

    # 遍历所有顶层节点，产出函数、类以及它们之间的代码
    for node in tree.body:
        node_start_line: int = node.lineno - 1

        # 产出当前节点与上一个节点之间的模块级代码
        if node_start_line > last_node_end_line:
            inter_code: str = "".join(
                lines[last_node_end_line:node_start_line]
            ).strip()
            if inter_code:
                yield "module", inter_code

        # 产出当前节点自身的代码
        node_end_line: int = getattr(node, "end_lineno", node_start_line)
        node_code: str = "".join(lines[node_start_line:node_end_line]).strip()

        title_prefix: str
        if isinstance(node, ast.ClassDef):
            title_prefix = "class"
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            title_prefix = "def"
        else:
            # 对于非函数/类的其他顶层语句（如赋值、导入等），将其归为模块代码
            if node_code:
                yield "module", node_code
            last_node_end_line = node_end_line
            continue

        title: str = f"{title_prefix} {node.name}"
        yield title, node_code
        last_node_end_line = node_end_line

    # 产出最后一个节点之后的模块级代码
    if last_node_end_line < len(lines):
        remaining_code: str = "".join(lines[last_node_end_line:]).strip()
        if remaining_code:
            yield "module", remaining_code


def pack_lines(lines: list[str], chunk_size: int) -> list[str]:
    """
    将代码行列表打包成不超过指定大小的文本块。

    该函数模拟将代码行一个个放入箱子（文本块）的过程，以尽可能填满每个箱子。

    参数:
        lines: 待打包的字符串代码行列表。
        chunk_size: 每个文本块的最大长度。

    返回:
        一个由打包好的文本块字符串组成的列表。

    注意:
        - 代码行之间使用 `\n` 连接，拼接长度会计入总长度。
        - 该函数不处理单行超长的情况，单个超长行会自成一个块。
    """
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_len: int = 0

    for line in lines:
        separator_len: int = 1 if buffer else 0
        line_len: int = len(line)

        # 检查将当前行加入缓冲区后是否会超长
        if buffer_len + line_len + separator_len <= chunk_size:
            # 未超长：加入缓冲区
            buffer.append(line)
            buffer_len += line_len + separator_len
            continue

        # 已超长：先将当前缓冲区打包成块
        if buffer:
            assembled_chunk: str = "\n".join(buffer).strip()
            if assembled_chunk:
                chunks.append(assembled_chunk)

        # 然后将当前行作为新缓冲区的开始
        buffer = [line]
        buffer_len = line_len

    # 清空最后一个缓冲区中剩余的内容
    if buffer:
        assembled_chunk: str = "\n".join(buffer).strip()
        if assembled_chunk:
            chunks.append(assembled_chunk)

    return chunks
