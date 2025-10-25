import ast
from ast import stmt
from typing import Any
from collections.abc import Generator, Sequence

from vnag.object import Segment
from vnag.segmenter import BaseSegmenter, pack_section


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
        2. 调用 `pack_section` 进行三层分块，确保每个块不超过 `chunk_size`。
        3. 为每个最终的文本块创建 `Segment` 对象，并附加元数据。
        """
        if not text.strip():
            return []

        segments: list[Segment] = []
        segment_index: int = 0
        section_order: int = 0

        # 基于 AST 将代码分割成函数/类定义的章节
        sections: Generator[tuple[str, str, str, str, str], None, None] = ast_split(text)

        for title, content, section_type, summary, signature in sections:
            if not content.strip():
                continue

            # 调用三层分块策略函数，对章节内容进行切分
            chunks: list[str] = pack_section(content, self.chunk_size)

            total_chunks: int = len(chunks)
            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue

                # 为每个文本块创建独立的元数据副本，并添加分段信息
                chunk_meta: dict[str, Any] = metadata.copy()
                chunk_meta["chunk_index"] = str(segment_index)
                chunk_meta["section_title"] = title
                chunk_meta["section_type"] = section_type
                if summary:
                    chunk_meta["summary"] = summary
                if signature:
                    chunk_meta["signature"] = signature
                chunk_meta["section_order"] = str(section_order)
                chunk_meta["section_part"] = f"{i + 1}/{total_chunks}"

                segments.append(Segment(text=chunk, metadata=chunk_meta))
                segment_index += 1

            section_order += 1

        return segments


def ast_split(text: str) -> Generator[tuple[str, str, str, str, str], None, None]:
    """
    使用 AST 将 Python 代码递归地分割成基于函数和类的章节。

    该函数会依次产出 (yield) 在模块顶-层及类内部定义的每个函数、类，
    以及它们之间的代码块。对于类内部的方法，其标题会自动添加类名作为前缀。

    参数:
        text: 待分割的 Python 源码字符串。

    返回:
        一个生成器，每次产出一个元组 (章节标题, 章节内容, 章节类型, 摘要, 签名)。
    """
    try:
        tree: ast.Module = ast.parse(text)
    except SyntaxError:
        # 如果代码有语法错误，AST 解析会失败。
        # 作为回退策略，将整个文件视为一个单独的 "module" 块。
        yield "module", text, "module", "", ""
        return

    lines: list[str] = text.splitlines(keepends=True)

    # --- 主流程开始 ---
    # 1. 产出文件头部（第一个 AST 节点之前）的代码。
    module_body = tree.body
    if module_body:
        first_node_start_line: int = module_body[0].lineno - 1
        if first_node_start_line > 0:
            module_header: str = "".join(lines[0:first_node_start_line]).strip()
            if module_header:
                yield "module", module_header, "module", "", ""

    # 2. 从顶层开始递归遍历整个 AST。
    yield from traverse_body(module_body, lines)

    # 3. 产出文件尾部（最后一个 AST 节点之后）的代码。
    if module_body:
        last_node_end_line: int = getattr(module_body[-1], "end_lineno", -1)
        if last_node_end_line != -1 and last_node_end_line < len(lines):
            remaining_code: str = "".join(lines[last_node_end_line:]).strip()
            if remaining_code:
                yield "module", remaining_code, "module", "", ""


def traverse_body(
    body_nodes: Sequence[stmt],
    lines: list[str],
    prefix: str = ""
) -> Generator[tuple[str, str, str, str, str], None, None]:
    """递归遍历 AST 节点体，产出代码块。"""
    # 如果节点体为空，则直接返回。
    if not body_nodes:
        return

    # 将 last_end_line 初始化为第一个节点开始之前的位置。
    # AST 行号是 1-based，我们的索引是 0-based。
    last_end_line: int = body_nodes[0].lineno - 1

    # 遍历当前层级的所有节点
    for node in body_nodes:
        start_line: int = node.lineno - 1
        end_line: int = getattr(node, "end_lineno", start_line)

        # 产出上一个节点到当前节点之间的代码（例如注释或模块级代码）。
        if start_line > last_end_line:
            inter_code: str = "".join(lines[last_end_line:start_line]).strip()
            if inter_code:
                title: str = f"{prefix}module" if prefix else "module"
                yield title, inter_code, "module", "", ""

        # --- 处理当前节点 ---
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            # 如果是函数或异步函数，直接产出整个函数体。
            node_code: str = "".join(lines[start_line:end_line]).strip()
            section_type: str = get_function_type(node, prefix)
            summary: str = ast.get_docstring(node) or ""
            signature: str = get_signature_string(node)
            yield f"{prefix}{node.name}", node_code, section_type, summary, signature

        elif isinstance(node, ast.ClassDef):
            # 如果是类定义，需要递归处理。
            # 找到类的 "头部" 结束的位置（即第一个方法或子类开始前）。
            header_end_line: int = end_line
            if node.body:
                # 如果类体不为空，头部结束于第一个子节点开始之前。
                header_end_line = node.body[0].lineno - 1

            # 产出类的头部（class ...:、文档字符串、类变量等）。
            header_code: str = "".join(lines[start_line:header_end_line]).strip()
            if header_code:
                summary = ast.get_docstring(node) or ""
                yield f"{prefix}{node.name}", header_code, "class", summary, ""

            # 递归调用自身，处理类体中的方法和嵌套类。
            # 新的前缀是当前类名 + "."
            new_prefix: str = f"{prefix}{node.name}."
            yield from traverse_body(node.body, lines, prefix=new_prefix)

            # 产出类定义结束花括号之后，但在 end_lineno 之前的所有内容
            # (这部分通常是空的，但为了严谨而保留)
            if node.body:
                last_child_end_line = getattr(node.body[-1], "end_lineno", -1)
                if last_child_end_line != -1 and end_line > last_child_end_line:
                    footer_code = "".join(lines[last_child_end_line:end_line]).strip()
                    if footer_code:
                        # 页脚部分没有独立的文档字符串，因此摘要为空。
                        yield f"{prefix}{node.name}", footer_code, "class", "", ""
        else:
            # 对于其他类型的顶层语句（如赋值、导入等），将其归为模块代码。
            node_code = "".join(lines[start_line:end_line]).strip()
            if node_code:
                title = f"{prefix}module" if prefix else "module"
                yield title, node_code, "module", "", ""

        # 更新上一个节点的结束位置
        last_end_line = end_line


def get_function_type(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    prefix: str
) -> str:
    """根据上下文和装饰器判断函数类型。"""
    # 如果没有前缀，说明是模块顶层的独立函数。
    if not prefix:
        return "function"

    # 有前缀，说明在类内部，是某种方法。
    # 检查特定的装饰器来进一步细化类型。
    for decorator in node.decorator_list:
        # 装饰器可以是简单的名称（如 @staticmethod）或调用（如 @app.route('/')）。
        # 这里我们只关心 ast.Name 类型的装饰器。
        if isinstance(decorator, ast.Name):
            if decorator.id == 'classmethod':
                return "class_method"
            if decorator.id == 'staticmethod':
                return "static_method"

    # 如果没有找到特定的装饰器，则为普通的实例方法。
    return "method"


def get_signature_string(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """从一个函数 AST 节点重建其接口签名字符串。"""
    # ast.unparse 在 Python 3.9+ 中可用，用于将 AST 节点转换回源代码字符串。
    if not hasattr(ast, 'unparse'):
        return ""  # 如果环境不支持 ast.unparse，则优雅地失败。

    parts = []
    args = node.args

    # 1. 处理仅限位置的参数 (e.g., "a, b, /")
    if args.posonlyargs:
        for arg in args.posonlyargs:
            part = arg.arg
            if arg.annotation:
                part += f": {ast.unparse(arg.annotation)}"
            parts.append(part)
        parts.append("/")

    # 2. 处理常规参数 (e.g., "c, d=1")
    num_args_with_defaults = len(args.defaults)
    first_arg_with_default_idx = len(args.args) - num_args_with_defaults
    for i, arg in enumerate(args.args):
        part = arg.arg
        if arg.annotation:
            part += f": {ast.unparse(arg.annotation)}"
        if i >= first_arg_with_default_idx:
            default_val = args.defaults[i - first_arg_with_default_idx]
            part += f" = {ast.unparse(default_val)}"
        parts.append(part)

    # 3. 处理 *args
    if args.vararg:
        part = f"*{args.vararg.arg}"
        if args.vararg.annotation:
            part += f": {ast.unparse(args.vararg.annotation)}"
        parts.append(part)

    # 4. 处理仅限关键字的参数 (e.g., "*, e, f=2")
    if args.kwonlyargs:
        if not args.vararg:
            parts.append("*")
        for i, arg in enumerate(args.kwonlyargs):
            part = arg.arg
            if arg.annotation:
                part += f": {ast.unparse(arg.annotation)}"
            kw_default_val = args.kw_defaults[i]
            if kw_default_val is not None:
                part += f" = {ast.unparse(kw_default_val)}"
            parts.append(part)

    # 5. 处理 **kwargs
    if args.kwarg:
        part = f"**{args.kwarg.arg}"
        if args.kwarg.annotation:
            part += f": {ast.unparse(args.kwarg.annotation)}"
        parts.append(part)

    # 组合成最终签名
    signature = f"({', '.join(parts)})"
    if node.returns:
        signature += f" -> {ast.unparse(node.returns)}"

    return signature
