from pathlib import Path
from typing import NamedTuple
from collections.abc import Iterator

import pypdf


class DocumentChunk(NamedTuple):
    """文档分块"""
    text: str
    metadata: dict[str, str]


class DocumentService:
    """文档处理服务

    说明：知识库仅接收并入库 Markdown（.md）。
    其它格式（.txt/.pdf）仅用于聊天附件的临时解析，不进入知识库。
    """

    def __init__(self) -> None:
        """构造函数"""
        self.chunk_size: int = 3000
        # 支持多格式读取（用户聊天附件解析）；知识库仅入库 .md
        self.supported_formats: list = [".md", ".txt", ".pdf", ".py"]

    def read_file_text(self, file_path: str) -> str:
        """读取原文（聊天附件解析用）：支持 .md/.txt/.pdf，返回纯文本。"""
        path: Path = Path(file_path)
        ext: str = path.suffix.lower()
        if ext not in self.supported_formats:
            raise ValueError(f"不支持的类型：{ext}")
        if ext in [".md", ".txt"]:
            return self._read_text_file(path)
        return self._read_pdf_file(path)

    def process_file(self, file_path: str) -> list[DocumentChunk]:
        """处理单个文件用于知识库入库：仅对 .md 进行分块。"""
        path: Path = Path(file_path)

        extension: str = path.suffix.lower()

        text: str = self._read_text_file(path)

        # 创建文档分块（仅 .md）
        chunks: list = self._create_chunks_markdown(text, {
            'source': str(file_path),
            'filename': path.name,
            'file_type': extension
        })
        return chunks

    def _read_text_file(self, path: Path) -> str:
        """读取文本文件"""
        text: str = path.read_text(encoding='utf-8')
        return text

    def _read_pdf_file(self, path: Path) -> str:
        """读取PDF文件"""
        text: str = ""

        with open(path, 'rb') as file:
            reader: pypdf.PdfReader = pypdf.PdfReader(file)
            for page in reader.pages:
                page_text: str = page.extract_text()
                if page_text is None:
                    page_text = ""
                text += page_text + "\n"

        return text

    def _create_chunks_markdown(self, text: str, metadata: dict[str, str]) -> list[DocumentChunk]:
        """Markdown 结构化分块。

        设计目标：
        - 标题优先：以行首的 #/##/### 等 Markdown 标题作为分段边界；
        - 保护代码：代码栅栏内（``` 或 ~~~ 包围）不解析标题，也不拆分代码；
        - 控制大小：段内内容先按空行聚合，超过 chunk_size 再进行定长切分（不重叠）。

        参数：
        - text：已读取的 Markdown 文本；
        - metadata：基础元数据（如 source/filename/file_type），本函数补充：
          - chunk_index：片段全局序号（0..N-1）
          - section_title/section_order/section_part：标题与分片信息（便于检索还原）

        返回：
        - DocumentChunk 列表，按原文顺序排列，chunk_index 为 0..N-1。

        复杂度与实现说明：
        - 单次线性扫描实现（生成器驱动），避免多次整体 split 带来的大拷贝；
        - chunk_size 按“字符”计（后续可替换为 token 计数而不改外部 API）。

        边界与示例：
        - 代码块中的 # 不触发分段：
          ```
          ```python\n# not a heading\n```  → 视为同一段
          ```
        - 连续多个标题：每个标题单独成段，即便段体为空也保留一个最小片段。
        """
        # 逐段（按标题）→ 逐片（按大小）流式产出，最后收集为列表
        chunks: list = []
        idx: int = 0
        sections_iter: Iterator = self._iter_markdown_sections(text)
        section_order: int = 0
        for sec in sections_iter:
            # 提取标题文本（去除开头 # 与空格），用于检索/展示关联
            section_title: str = self._extract_title(sec)
            pieces: list = list(self._iter_packed_chunks(sec))
            total: int = len(pieces)
            for j, piece in enumerate(pieces):
                # 为每个片段复制基础元数据，并补充顺序索引
                chunk_metadata: dict = metadata.copy()
                chunk_metadata["chunk_index"] = str(idx)
                # 额外携带段级信息，便于检索显示（标题与分片序号）
                if section_title:
                    chunk_metadata["section_title"] = section_title
                chunk_metadata["section_order"] = str(section_order)
                chunk_metadata["section_part"] = f"{j + 1}/{total}"
                chunks.append(DocumentChunk(text=piece, metadata=chunk_metadata))
                idx += 1
            section_order += 1
        return chunks

    def _extract_title(self, section_text: str) -> str:
        """从段文本首行提取标题（去除 # 与前后空白）。"""
        if section_text:
            first_line: str = section_text.splitlines()[0]
        else:
            first_line = ""

        i: int = 0
        while i < len(first_line) and first_line[i] == '#':
            i += 1

        title: str = first_line[i:].strip()
        return title

    def _iter_markdown_sections(self, text: str) -> Iterator[str]:
        """逐段产出 Markdown 片段（标题为界，保护代码块）。

        规则：
        - 栅栏开始/结束：以行首 ``` 或 ~~~ 识别，支持 ```lang 形式；
        - 标题识别：仅在“非代码块”状态下，行首 # 视为新段开始；
        - 聚合策略：将上一个段落的累积行以 \n 连接产出（末尾 strip 去除多余空白）。

        该生成器只做“按照标题分段”，不考虑 chunk_size；
        大小控制由 _iter_packed_chunks 负责。
        """
        in_code: bool = False  # 是否处于代码栅栏内
        current: list = []
        for line in text.splitlines():
            stripped: str = line.strip()
            # 识别代码栅栏：兼容 ```lang / ~~~
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_code = not in_code
                current.append(line)
                continue
            # 非代码块内的行首 # 触发新段（标题）
            if (not in_code) and stripped.startswith("#"):
                if current:
                    joined: str = "\n".join(current).strip()  # 输出上一段
                    if joined:
                        yield joined
                    current = []
                current.append(line)
            else:
                current.append(line)
        if current:
            joined = "\n".join(current).strip()  # 收尾：输出最后一段
            if joined:
                yield joined

    def _iter_packed_chunks(self, sec: str) -> Iterator[str]:
        """将单个段（含标题+正文）打包为多个不超过 chunk_size 的片段。

        规则：
        - 先按空行拆分为自然段（paragraphs）；
        - 依次累加 paragraph，超过 chunk_size 则立即 flush 当前缓冲；
        - 对于“单个 paragraph 本身超过 chunk_size”的情况，按固定大小进行 while 切片；
        - 片段之间不重叠，保持顺序不变。
        """
        # 段本身不超限：直接返回
        if len(sec) <= self.chunk_size:
            yield sec
            return

        # 先按空行拆为自然段，再聚合装箱
        paragraphs: list = [p for p in sec.split("\n\n") if p.strip()]
        buf: list = []
        acc_len: int = 0
        for p in paragraphs:
            p_len: int = len(p) + (2 if buf else 0)  # 追加时补偿段间空行
            if acc_len + p_len <= self.chunk_size:
                if buf:
                    buf.append("")
                buf.append(p)
                acc_len += p_len
                continue

            # 超限：先 flush 缓冲为一个片段
            if buf:
                assembled: str = "\n".join(buf).strip()
                if assembled:
                    yield assembled
                buf = []
                acc_len = 0

            # 单个自然段超限：定长切片（不重叠）
            if len(p) > self.chunk_size:
                i: int = 0
                n: int = len(p)
                while i < n:
                    sub: str = p[i:i + self.chunk_size].strip()
                    if sub:
                        yield sub
                    i += self.chunk_size
            else:
                # 重置后将当前段放入新缓冲
                buf.append(p)
                acc_len = len(p)

        # 收尾：flush 剩余缓冲
        if buf:
            assembled = "\n".join(buf).strip()
            if assembled:
                yield assembled
