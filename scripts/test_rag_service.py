"""RAGService 简单功能测试。

条件：
- 不触发重型初始化（不加载向量库/模型）。
- 每个功能函数各 1 个最小用例。

期望：
- 输出结构与内容满足最小正确性。
"""

from pathlib import Path
import pytest
from typing import Any, cast
from vnag.rag_service import RAGService
from vnag.template import CHAT_PROMPT_TEMPLATE
from vnag.document_service import DocumentChunk, DocumentService


class _RAGServiceNoInit(RAGService):
    def __init__(self) -> None:
        """测试桩：跳过父类初始化，避免真实知识库构建。"""
        # 跳过父类初始化，避免知识库构建
        pass


def test_prepare_chat_messages_basic() -> None:
    """给定用户消息，返回 CHAT 模板包装后的单条消息。"""
    svc = _RAGServiceNoInit()
    messages = [{"role": "user", "content": "Q"}]

    out = svc.prepare_chat_messages(messages, user_files=None)

    assert isinstance(out, list) and len(out) == 1  # 仅替换末条内容，不增删消息
    expected = CHAT_PROMPT_TEMPLATE.format(question="Q")
    assert out[0]["content"] == expected            # 模板渲染正确（问题被格式化）


def test_prepare_rag_messages_basic() -> None:
    """给定用户问题与检索结果，返回含知识库上下文的 RAG prompt。"""
    class _VS:
        def similarity_search(
            self,
            query: str,
            k: int = 3,
        ) -> list[dict[str, Any]]:  # noqa: ARG002
            """为测试模拟的相似度搜索"""
            documents: list[dict[str, Any]] = []
            documents.append({"text": "DOC1", "metadata": {}, "distance": 0.0})
            documents.append({"text": "DOC2", "metadata": {}, "distance": 0.1})
            return documents

        def get_document_count(self) -> int:
            """返回模拟计数，确保 prepare_rag_messages 的最小路径完整。"""
            return 2

    svc = _RAGServiceNoInit()
    svc.vector_service = cast(Any, _VS())
    messages = [{"role": "user", "content": "问题?"}]

    out = svc.prepare_rag_messages(messages, user_files=None)

    assert isinstance(out, list) and len(out) == 1  # 仍为单条消息
    last = out[-1]
    assert last["role"] == "user"                   # 保持角色一致（仅替换内容）
    content = last["content"]
    assert "问题" in content                        # 含原始问题文本
    assert "知识库文档 1:" in content               # 含检索上下文序号前缀
    assert "DOC1" in content                       # 含首条检索文段


def test_add_documents_success() -> None:
    """add_documents：当有分块时返回 True 且调用向量入库。"""
    class _DS(DocumentService):
        def process_file(
            self,
            file_path: str,
        ) -> list[DocumentChunk]:  # noqa: D401, ARG002
            """为测试模拟的文档处理"""
            chunks: list = [
                DocumentChunk(
                    text="t",
                    metadata={"filename": "f.md", "chunk_index": "0"},
                )
            ]
            return chunks

    class _VS:
        def __init__(self) -> None:  # 简单标记器
            self.called = False  # 初始未调用

        def add_documents(
            self,
            chunks: list[DocumentChunk],
        ) -> None:  # noqa: D401
            self.called = bool(chunks)  # 有分块则视为已调用

    svc = _RAGServiceNoInit()
    svc.document_service = _DS()
    svc.vector_service = cast(Any, _VS())

    ok = svc.add_documents(["a.md"])            # 最小路径
    assert ok is True  # 有分块时应成功
    assert (
        svc.vector_service.called is True       # type: ignore[attr-defined]
    )                                           # 标记向量入库被触发


def test_add_documents_empty() -> None:
    """add_documents：空列表返回 False。"""
    svc = _RAGServiceNoInit()
    ok = svc.add_documents([])
    assert ok is False                          # 空列表应直接返回 False


def test_get_document_count() -> None:
    """get_document_count：应返回底层向量服务计数。"""
    class _VS:
        def get_document_count(self) -> int:
            return 7

    svc = _RAGServiceNoInit()
    svc.vector_service = cast(Any, _VS())
    assert svc.get_document_count() == 7        # 透传底层计数


def test__process_user_files_mix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_process_user_files：包含成功、格式不支持与读取失败三种情况。"""
    # 成功：存在的 txt 文件
    okf = tmp_path / "ok.txt"
    okf.write_text("OK-CONTENT", encoding="utf-8")

    # PDF：通过 monkeypatch 模拟两页文本 "P1"、"P2"
    unsup = tmp_path / "u.pdf"
    unsup.write_bytes(b"%PDF-1.4\n")

    class _FakePage:
        def __init__(self, t: str) -> None:
            self._t = t

        def extract_text(self) -> str:
            return self._t

    class _FakeReader:
        def __init__(self, f: Any) -> None:  # noqa: ANN001 - 测试桩
            """构造函数"""
            self.pages = [_FakePage("P1"), _FakePage("P2")]

    import pypdf as _pp

    monkeypatch.setattr(_pp, "PdfReader", lambda f: _FakeReader(f))

    # 读取失败：不存在的 txt
    missing = tmp_path / "missing.txt"

    svc = _RAGServiceNoInit()
    # 现在 _process_user_files 依赖 DocumentService 读取原文
    svc.document_service = DocumentService()
    paths = [str(okf), str(unsup), str(missing)]
    out = svc._process_user_files(paths)

    assert "OK-CONTENT" in out       # 成功读取的 txt 内容应包含
    assert "P1" in out               # PDF 文本被提取并拼接
    assert "读取失败" in out          # 不存在/异常时给出失败提示
