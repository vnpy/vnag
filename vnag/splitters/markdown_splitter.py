from collections.abc import Iterator

from vnag.splitter import BaseSplitter, DocumentChunk


class MarkdownSplitter(BaseSplitter):
    """文档处理服务

    说明：知识库仅接收并入库 Markdown（.md）
    """

    def __init__(self, chunk_size: int = 3000) -> None:
        """构造函数"""
        super().__init__(chunk_size)

    def split_text(self, text: str, metadata: dict[str, str]) -> list[DocumentChunk]:
        """对传入的 Markdown 文本进行结构化分块"""
        chunks: list[DocumentChunk] = self.create_chunks_markdown(text, metadata)
        return chunks

    def create_chunks_markdown(self, text: str, metadata: dict[str, str]) -> list[DocumentChunk]:
        """Markdown 结构化分块

        设计目标：
        - 标题优先：以行首的 #/##/### 等 Markdown 标题作为分段边界
        - 保护代码：代码栅栏内（``` 或 ~~~ 包围）不解析标题，也不拆分代码
        - 控制大小：段内内容先按空行聚合，超过 chunk_size 再进行定长切分（不重叠）

        参数：
        - text：已读取的 Markdown 文本
        - metadata：基础元数据（如 source/filename/file_type），本函数补充：
          - chunk_index：片段全局序号（0..N-1）
          - section_title/section_order/section_part：标题与分片信息（便于检索还原）

        返回：
        - DocumentChunk 列表，按原文顺序排列，chunk_index 为 0..N-1

        复杂度与实现说明：
        - 单次线性扫描实现（生成器驱动），避免多次整体 split 带来的大拷贝
        - chunk_size 按“字符”计（后续可替换为 token 计数而不改外部 API）

        边界与示例：
        - 代码块中的 # 不触发分段：
          ```
          ```python\n# not a heading\n```  → 视为同一段
          ```
        - 连续多个标题：每个标题单独成段，即便段体为空也保留一个最小片段
        """
        # 逐段（按标题）→ 逐片（按大小）流式产出，最后收集为列表
        chunks: list = []
        idx: int = 0
        section_order: int = 0
        sections_iter: Iterator = self.iter_markdown_sections(text)

        for sec in sections_iter:
            # 提取标题文本（去除开头 # 与空格），用于检索/展示关联
            section_title: str = self.extract_title(sec)

            # 对单个章节段：若长度超过 chunk_size，则按空行聚合后再切
            section_chunks: list[str] = self.pack_section(sec)
            total: int = len(section_chunks)

            for j, chunk_text in enumerate(section_chunks):
                # 为每个片段复制基础元数据，并补充顺序索引
                chunk_metadata: dict = metadata.copy()
                chunk_metadata["chunk_index"] = str(idx)

                # 额外携带段级信息，便于检索显示（标题与分片序号）
                if section_title:
                    chunk_metadata["section_title"] = section_title
                chunk_metadata["section_order"] = str(section_order)
                chunk_metadata["section_part"] = f"{j + 1}/{total}"

                # 收集片段：保证原文顺序与章节划分信息
                chunks.append(DocumentChunk(text=chunk_text, metadata=chunk_metadata))
                idx += 1

            section_order += 1

        return chunks

    def extract_title(self, section_text: str) -> str:
        """从段文本首行提取标题（去除 # 与前后空白）"""
        if section_text:
            first_line: str = section_text.splitlines()[0]
        else:
            first_line = ""

        # 提取标题
        i: int = 0
        while i < len(first_line) and first_line[i] == '#':
            i += 1

        title: str = first_line[i:].strip()
        return title

    def iter_markdown_sections(self, text: str) -> Iterator[str]:
        """逐段产出 Markdown 片段（标题为界，保护代码块）

        规则：
        - 栅栏开始/结束：以行首 ``` 或 ~~~ 识别，支持 ```lang 形式
        - 标题识别：仅在“非代码块”状态下，行首 # 视为新段开始
        - 聚合策略：将上一个段落的累积行以 \n 连接产出（末尾 strip 去除多余空白）

        该生成器只做“按照标题分段”，不考虑 chunk_size
        大小控制由 pack_section 负责
        """
        in_code: bool = False  # 代码栅栏状态：在 fenced code 内部不解析标题
        current: list = []     # 当前累计的行缓冲

        for line in text.splitlines():
            stripped: str = line.strip()
            # 识别代码栅栏：兼容 ```lang / ~~~
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_code = not in_code          # 进入或退出 fenced code
                current.append(line)           # 栅栏本身保留在内容中
                continue

            # 非代码块内的行首 # 触发新段（标题）
            if (not in_code) and stripped.startswith("#"):
                if current:                         # 若已有累计内容，先输出为上一段
                    joined: str = "\n".join(current).strip()
                    if joined:
                        yield joined
                    current = []
                current.append(line)               # 新段以标题行开头
            else:
                current.append(line)               # 普通行累加

        if current:
            joined = "\n".join(current).strip()   # 收尾：剩余缓冲作为最后一段
            if joined:
                yield joined
