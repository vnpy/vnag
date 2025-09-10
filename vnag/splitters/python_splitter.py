import re
import ast
from vnag.splitter import BaseSplitter, DocumentChunk
# 用来找到一个函数/类定义块起点的正则常量
PY_DEF_CLASS_PATTERN = re.compile(r"^\s*(?:@.+\n)*\s*(def|class)\s", re.MULTILINE)

class PythonSplitter(BaseSplitter):
    """
    说明：知识库仅接收并入库 Python（.py）
    """

    def __init__(self, chunk_size: int = 3000) -> None:
        """构造函数"""
        self.chunk_size: int = chunk_size

    def split_text(self, text: str, metadata: dict[str, str]) -> list[DocumentChunk]:
        """对传入的 Python 源码进行分块"""
        chunks: list[DocumentChunk] = self.create_chunks_python(text, metadata)
        return chunks

    def create_chunks_python(self, text: str, metadata: dict[str, str]) -> list[DocumentChunk]:
        """Python 结构化分块

        流程：
        - 先按 def/class（含 async def）做结构化初切，得到“代码单元”
        - 段内内容先按空行聚合，超过 chunk_size 再进行定长切分（不重叠）
        - 不跨函数/类拆分；为每段补元数据后输出 DocumentChunk
        """
        # 先尝试 AST 初切；失败则回退到正则分块
        try:
            blocks_with_context: list = self.split_by_ast(text)
        except Exception:
            blocks_with_context = self.split_by_regex(text)

        # 按块拆细并装配为 DocumentChunk
        chunks: list[DocumentChunk] = []
        idx: int = 0
        section_order: int = 0

        for block_text, section_title, container_class, qualified_name in blocks_with_context:
            # 对单个章节段：若长度超过 chunk_size，则按空行聚合后再切
            section_chunks: list[str] = self.pack_section(block_text)
            total_pieces: int = len(section_chunks)

            for j, chunk_text in enumerate(section_chunks):    # 逐段封装元数据
                chunk_meta: dict[str, str] = metadata.copy()   # 基础信息（来源/文件名/类型）
                chunk_meta["chunk_index"] = str(idx)           # 全局片段序号

                # 标题（class/def/...）
                if section_title:
                    chunk_meta["section_title"] = section_title
                chunk_meta["section_order"] = str(section_order)        # 块在文件中的顺序
                chunk_meta["section_part"] = f"{j + 1}/{total_pieces}"  # 当前块内分段序号
                chunk_meta["container_class"] = container_class         # 所属类（顶层为空）
                chunk_meta["qualified_name"] = qualified_name           # 文件内标识（如 Bar.foo）

                chunks.append(DocumentChunk(text=chunk_text, metadata=chunk_meta))  # 入库片段
                idx += 1  # 递增全局索引

            section_order += 1

        return chunks

    def extract_title(self, block: str) -> str:
        """提取代码块标题：def/class 名称；若无则返回 "module"

        说明：
        - 逐行扫描，跳过空行与装饰器行；
        - 命中以 "def " 或 "class " 开头的标题行后，解析名称并返回；
        - 未命中则视为模块片段
        """
        lines: list[str] = block.splitlines()  # 不保留换行，逐行处理语义
        title: str = "module"

        for raw_line in lines:
            stripped: str = raw_line.strip()
            if not stripped:
                continue

            # 跳过装饰器
            if stripped.startswith("@"):  # 装饰器不作为标题
                continue

            # 提取def名称
            if stripped.startswith("def "):
                symbol_name: str = stripped[4:]  # 去掉前缀“def ”
                # 从括号/冒号之前截断，得到裸函数名
                symbol_name = symbol_name.split("(")[0].split(":")[0].strip()
                title = f"def {symbol_name}"
                break

            # 提取class名称
            if stripped.startswith("class "):
                symbol_name = stripped[6:]  # 去掉前缀“class ”
                # 从括号/冒号之前截断，得到裸类名
                symbol_name = symbol_name.split("(")[0].split(":")[0].strip()
                title = f"class {symbol_name}"
                break

            break

        return title

    def split_by_headers(self, text: str) -> list[str]:
        """按 def/class 作为粗分界

        说明：
        - 使用正则匹配可选装饰器行 + def/class 头部（MULTILINE）
        - 组装 [start, end) 范围，首段（文件头到第一个符号）若非空也保留为一个块
        - 不进行任何内容修改，保证符号行出现在各自块的开头
        """
        # 用正则找到所有 def/class 的起始位置
        starts: list[int] = []
        for match in PY_DEF_CLASS_PATTERN.finditer(text):
            starts.append(match.start())  # 记录每个代码单元头部的字符起点

        if not starts:
            return [text]

        # 直接生成 [start, next_start) 文本并过滤空白
        indices: list[int] = [0]
        for pos in starts:
            indices.append(pos)
        indices.append(len(text))

        blocks: list[str] = []
        for i in range(len(indices) - 1):
            start_pos: int = indices[i]
            end_pos: int = indices[i + 1]
            segment: str = text[start_pos:end_pos]
            if segment.strip():
                blocks.append(segment)

        return blocks

    def split_by_regex(self, text: str) -> list:
        """正则分块：生成 (block_text, section_title, container_class, qualified_name)

        说明：无法可靠判定方法的容器类，此处不设置 container_class（置为空字符串）
        - class 块:   (title="class X", container_class="", qualified_name="X")
        - def 块:     (title="def f",   container_class="", qualified_name="f")
        - module 块:  (title="module",   container_class="", qualified_name="<module>")
        """
        raw_blocks: list[str] = self.split_by_headers(text)  # 仅按符号粗切，暂不含容器语义
        blocks_with_context: list = []

        for block_text in raw_blocks:
            title = self.extract_title(block_text)  # 基于首行语义推断标题种类

            if title.startswith("class "):
                # 提取 class 名称
                parts = title.split(" ", 1)
                if len(parts) == 2:
                    name = parts[1]
                else:
                    name = ""
                blocks_with_context.append((block_text, title, "", name))  # container_class 置空

            elif title.startswith("def "):
                # 提取 def 名称
                parts = title.split(" ", 1)
                if len(parts) == 2:
                    name = parts[1]
                else:
                    name = ""
                blocks_with_context.append((block_text, title, "", name))

            else:
                # 提取 module 名称
                blocks_with_context.append((block_text, "module", "", "<module>"))  # 文件头/游离片段

        return blocks_with_context

    def split_by_ast(self, text: str) -> list:
        """
        使用 AST 初切，返回 (block_text, section_title, container_class, qualified_name) 列表
        - section_title: "class X" / "def f" / "async def g" / "module"
        - container_class: 顶层为空字符串，方法为类名
        - qualified_name: "X.f" / "f" / "<module>"
        """
        syntax_tree = ast.parse(text)                  # 语法树：精确掌握类/函数边界与行号
        source_lines = text.splitlines(keepends=True)  # 字符串列表：保留换行，便于按行切片

        blocks_with_context: list = []

        # 收集顶层定义及其行范围
        definition_events: list = []                   # (start_line, end_line, section_title, container, qualified_name)

        for node in syntax_tree.body:                  # 顶层定义（类/函数）
            # 类定义
            if isinstance(node, ast.ClassDef):
                class_name = node.name                 # 类名
                start_line = self.calc_start_line(node)                  # 起点：含装饰器
                end_line = self.get_end_line(node)                       # 终点：统一获取 end_lineno/lineno
                section_title = f"class {class_name}"                    # 标题
                container = ""                                           # 容器
                qualified_name = class_name                              # 标记
                definition_events.append((start_line, end_line, section_title, container, qualified_name))

                # 类内方法
                for method_node in node.body:
                    if isinstance(method_node, ast.FunctionDef | ast.AsyncFunctionDef):
                        # 含装饰器：起点使用最早装饰器行
                        self.append_function_event(definition_events, method_node, class_name)

            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # 顶层函数：容器为空字符串
                self.append_function_event(definition_events, node, "")

        # 基于起始行排序
        definition_events.sort(key=lambda event: event[0])

        # 模块头：文件起点到第一个定义之前的区域
        if definition_events:
            first_start_line = definition_events[0][0]
            if first_start_line > 1:
                module_text = "".join(source_lines[0:first_start_line - 1])  # 行号转切片索引（AST起始行号为1）
                if module_text.strip():
                    blocks_with_context.append((module_text, "module", "", "<module>"))
        else:
            # 没有任何定义，整个文件作为模块块
            blocks_with_context = [(text, "module", "", "<module>")]
            return blocks_with_context

        # 逐块切片
        for event_index, (start_line, end_line, section_title, container_name, qualified_name) in enumerate(definition_events):

            # 如果还有下一个块，则终止位置为下一个块的起始行号减1
            if event_index + 1 < len(definition_events):
                real_end_line = definition_events[event_index + 1][0] - 1
            # 如果没有下一个块，则终止位置为当前块的结束行号
            else:
                real_end_line = end_line

            # 切片
            block_text = self.slice_source_by_lines(source_lines, start_line, real_end_line)  # 含头含尾

            if block_text.strip():
                blocks_with_context.append((block_text, section_title, container_name, qualified_name))

        return blocks_with_context

    def calc_start_line(self, node: ast.AST) -> int:
        """若存在装饰器，起始行取最小装饰器行；否则取定义行"""
        lines: list[int] = []  # 收集所有装饰器行号
        if hasattr(node, "decorator_list"):
            for deco in node.decorator_list:
                # 如果装饰器有行号，则添加到列表
                if hasattr(deco, "lineno"):
                    lines.append(deco.lineno)
        if lines:
            # 如果列表不为空，则取最小行号
            result_line: int = min(lines)  # 起点落到最靠前的装饰器
        else:
            result_line = getattr(node, "lineno", 1)  # 无装饰器则取定义行
        return result_line

    def get_end_line(self, node: ast.AST) -> int:
        """统一 AST 结束行号获取：优先 end_lineno，不存在则退化为 lineno"""
        end_line: int = getattr(node, "end_lineno", getattr(node, "lineno", 1))
        return end_line

    def append_function_event(
        self,
        events: list,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        container_name: str,
    ) -> None:
        """添加函数/方法定义事件：在收集阶段生成标题与限定名"""
        if isinstance(node, ast.AsyncFunctionDef):
            function_name: str = node.name
            kind: str = "async def"
        else:
            function_name = node.name
            kind = "def"

        start_line: int = self.calc_start_line(node)
        end_line: int = self.get_end_line(node)
        section_title: str = f"{kind} {function_name}"
        if container_name:
            qualified_name: str = f"{container_name}.{function_name}"
        else:
            qualified_name = function_name
        events.append((start_line, end_line, section_title, container_name, qualified_name))

    def slice_source_by_lines(self, source_lines: list, start_line: int, end_line: int) -> str:
        """按行号切片源文本（end_line 为包含行的行号）"""
        start_index: int = max(0, start_line - 1)  # 1-based -> 0-based
        end_index: int = max(start_index, end_line)  # 右边界为包含行号
        sliced_text: str = "".join(source_lines[start_index:end_index])  # 保留换行
        return sliced_text
