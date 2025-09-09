import re

from vnag.splitter import BaseSplitter, DocumentChunk


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
        1) 按 def/class 作为粗分界，得到符号级块（保留签名在块开头）
        2) 对超出 chunk_size 的块，在块内按 空行→换行→空格 做一次轻量补切
        3) 不跨函数/类拆分，不做重叠；原样透传外部 metadata
        """
        base_meta: dict[str, str] = metadata.copy()  # 不注入额外字段，保持风格一致

        # 先按符号级（def/class）粗分
        blocks: list[str] = self.split_by_headers(text)

        # 对每个符号块做一次轻量补切，并装配为 DocumentChunk
        chunks: list[DocumentChunk] = []
        idx: int = 0
        section_order: int = 0

        for block in blocks:
            section_title: str = self.extract_title(block)
            pieces: list[str] = self.pack_section(block)
            total: int = len(pieces)

            for j, piece in enumerate(pieces):
                chunk_meta: dict[str, str] = base_meta.copy()
                chunk_meta["chunk_index"] = str(idx)
                if section_title:
                    chunk_meta["section_title"] = section_title
                chunk_meta["section_order"] = str(section_order)
                chunk_meta["section_part"] = f"{j + 1}/{total}"

                chunks.append(DocumentChunk(text=piece, metadata=chunk_meta))
                idx += 1

            section_order += 1

        return chunks

    def split_by_headers(self, text: str) -> list[str]:
        """按 def/class 作为粗分界

        说明：
        - 使用正则匹配可选装饰器行 + def/class 头部（MULTILINE）
        - 组装 [start, end) 范围，首段（文件头到第一个符号）若非空也保留为一个块
        - 不进行任何内容修改，保证符号行出现在各自块的开头
        """
        # 用正则找到所有 def/class 的起始位置
        pattern = re.compile(r"^\s*(?:@.+\n)*\s*(def|class)\s", re.MULTILINE)
        starts: list[int] = [m.start() for m in pattern.finditer(text)]

        if not starts:
            return [text]

        # 组装块范围
        starts = [0] + starts  # 确保从文件头开始
        ranges: list[tuple[int, int]] = []
        for i in range(len(starts)):
            s = starts[i]
            e = starts[i + 1] if i + 1 < len(starts) else len(text)
            if s == 0:
                # 文件头到第一个符号之间可能有导入/常量，保留为单独块
                if e > s:
                    ranges.append((s, e))
            else:
                ranges.append((s, e))

        # 去除可能的重复与无效范围
        merged: list[str] = []
        for s, e in ranges:
            seg = text[s:e]
            if seg.strip():
                merged.append(seg)
        return merged

    def extract_title(self, block: str) -> str:
        """提取代码块标题：def/class 名称；若无则返回 "module"""
        # 按行分割
        lines = block.splitlines()

        for raw in lines:
            # 去除首尾空白
            stripped = raw.strip()

            if not stripped:
                continue

            # 跳过装饰器
            if stripped.startswith("@"):
                continue

            # 提取def名称
            if stripped.startswith("def "):
                name = stripped[4:]
                name = name.split("(")[0].split(":")[0].strip()
                return f"def {name}"

            # 提取class名称
            if stripped.startswith("class "):
                name = stripped[6:]
                name = name.split("(")[0].split(":")[0].strip()
                return f"class {name}"

            break

        return "module"

    def pack_section(self, sec: str) -> list[str]:
        """对单个符号块进行轻量补切：空行→换行→空格

        规则：
        - 若块长度不超过 chunk_size，直接返回原块；
        - 否则先按空行聚合，不足再按行切分，极端超长行退化为定长切；
        - 不做重叠，不跨函数/类；保持实现与 MarkdownSplitter 的“轻补切”风格一致
        """
        if len(sec) <= self.chunk_size:
            return [sec]

        # 空行装箱
        paragraphs: list[str] = []
        for p in sec.split("\n\n"):
            if p.strip():
                paragraphs.append(p)

        paragraph_chunks: list[str] = self.pack_paragraphs(paragraphs, self.chunk_size)

        # 对仍超限的片段按行装箱
        line_chunks: list[str] = []
        for segment in paragraph_chunks:
            if len(segment) <= self.chunk_size:
                line_chunks.append(segment)
                continue
            line_chunks.extend(self.pack_lines(segment.splitlines(), self.chunk_size))

        # 兜底：极端超长行定长切片
        fixed_chunks: list[str] = []
        for segment in line_chunks:
            if len(segment) <= self.chunk_size:
                fixed_chunks.append(segment)
            else:
                fixed_chunks.extend(self.split_by_length(segment, self.chunk_size))

        return fixed_chunks


