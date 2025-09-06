"""AgentGateway 简单功能测试（无真实网络）。

条件：
- 不访问外部 API；通过 monkeypatch/注入假客户端与假 RAG 服务；
- 仅覆盖关键路径：缺失初始化的报错提示、流式输出基本流程。

期望：
- 当 client 未初始化时，invoke_streaming 首个产出为提示文本；
- 当注入假 client 与假 RAG 后，invoke_streaming 能正确产出拼接的增量文本。
"""

from __future__ import annotations

from typing import Any, cast

from vnag.gateway import AgentGateway


class _FakeDelta:
    """流式增量中的 delta 载体（仅含 content）。"""
    def __init__(self, content: str) -> None:
        """初始化增量内容。"""
        self.content = content


class _FakeChoice:
    """仿 OpenAI choice 结构，持有一条 delta。"""
    def __init__(self, content: str) -> None:
        """用给定内容构造一条 delta。"""
        self.delta = _FakeDelta(content)


class _FakeChunk:
    """单个流式块，包含一个 choice。"""
    def __init__(self, content: str) -> None:
        """构造一个仅含单项 choice 的块。"""
        self.choices = [_FakeChoice(content)]


class _FakeStream:
    """返回若干增量 chunk 的可迭代对象。"""

    def __init__(self, pieces: list[str]) -> None:
        """保存待迭代的增量片段。"""
        self._pieces = pieces

    def __iter__(self) -> Any:
        """逐个产出 _FakeChunk。"""
        for p in self._pieces:
            yield _FakeChunk(p)


class _FakeChatCompletions:
    """仿 OpenAI chat.completions 接口，仅流式（stream=True）。"""
    def __init__(self, pieces: list[str]) -> None:
        """保存将要作为流返回的片段。"""
        self._pieces = pieces

    def create(
        self,
        *,
        model: str,
        messages: list[dict],
        **kwargs: Any,
    ) -> Any:
        """仅支持 stream=True，返回可迭代流。"""
        # 仅在 stream=True 时返回可迭代流
        if kwargs.get("stream"):
            return _FakeStream(self._pieces)
        raise NotImplementedError


class _FakeClient:
    """仿 OpenAI 客户端对象，仅提供 chat.completions.create。"""
    def __init__(self, pieces: list[str]) -> None:
        """用给定片段初始化 chat.completions 接口。"""
        self.chat = type("_C", (), {"completions": _FakeChatCompletions(pieces)})()


class _FakeRAG:
    """最小假 RAG：直接回传消息列表（不做改写）。"""

    def prepare_chat_messages(
        self,
        messages: list[dict],
        user_files: list[str] | None = None,
    ) -> list[dict]:
        """CHAT 分支：返回原消息。"""
        return messages

    def prepare_rag_messages(
        self,
        messages: list[dict],
        user_files: list[str] | None = None,
    ) -> list[dict]:
        """RAG 分支：返回原消息。"""
        return messages


def test_invoke_streaming_when_client_missing() -> None:
    """client 未初始化时应直接产出提示文本。"""
    g = AgentGateway()
    # 不调用 init；保持 client=None 与 model_name 可能为空。
    out = list(g.invoke_streaming(messages=[{"role": "user", "content": "hi"}]))
    assert out and "未初始化" in out[0]  # 首个产出包含“未初始化”提示


def test_invoke_streaming_basic_flow() -> None:
    """注入假 client 与假 RAG，流式应按顺序产出增量文本并可拼接。"""
    g = AgentGateway()
    g.model_name = "fake-model"
    g._rag_service = cast(Any, _FakeRAG())
    g.client = cast(Any, _FakeClient(["A", "B", "C"]))  # 三段增量
    # 可选：设置 max_tokens/temperature，不影响本用例正确性
    g.settings.update({
        "max_tokens": 10,
        "temperature": 0.1,
    })

    pieces: list[str] = list(
        g.invoke_streaming(
            messages=[{"role": "user", "content": "ping"}],
            use_rag=False,
        )
    )

    assert pieces == ["A", "B", "C"]     # 三段增量顺序一致
    full: str = "".join(pieces)
    assert full == "ABC"                 # 拼接后的内容匹配预期


def test_prepare_messages_chat_calls_rag() -> None:
    """use_rag=False 时应调用 RAG 的 chat 分支并回传结果。"""
    class _R:
        def __init__(self) -> None:
            self.called = False

        def prepare_chat_messages(
            self,
            messages: list[dict],
            user_files: list[str] | None = None,
        ) -> list[dict]:
            """标记被调用并返回固定结构。"""
            self.called = True
            return [{"role": "user", "content": "X"}]

        def prepare_rag_messages(
            self,
            messages: list[dict],
            user_files: list[str] | None = None,
        ) -> list[dict]:
            """RAG 分支：直接返回原消息。"""
            return messages

    g = AgentGateway()
    g._rag_service = cast(Any, _R())
    out = g._prepare_messages(
        messages=[{"role": "user", "content": "q"}],
        use_rag=False,
        user_files=None,
    )
    assert isinstance(out, list) and out[0]["content"] == "X"    # chat 分支生效
    assert cast(Any, g._rag_service).called is True              # 已调用 chat 分支


def test_prepare_messages_rag_calls_rag() -> None:
    """use_rag=True 时应调用 RAG 的 rag 分支并回传结果。"""
    class _R:
        def __init__(self) -> None:
            self.called = False

        def prepare_chat_messages(self, messages: list[dict], user_files: list | None = None) -> list[dict]:
            """CHAT 分支：直接返回原消息。"""
            return messages

        def prepare_rag_messages(self, messages: list[dict], user_files: list | None = None) -> list[dict]:
            """标记被调用并返回固定结构。"""
            self.called = True
            return [{"role": "user", "content": "Y"}]

    g = AgentGateway()
    g._rag_service = cast(Any, _R())
    out = g._prepare_messages(
        messages=[{"role": "user", "content": "q"}],
        use_rag=True,
        user_files=None,
    )
    assert isinstance(out, list) and out[0]["content"] == "Y"     # rag 分支生效
    assert cast(Any, g._rag_service).called is True               # 已调用 rag 分支


def test_send_message_updates_history_and_saves(monkeypatch: Any) -> None:  # noqa: ANN001
    """send_message 应在历史中追加 user/assistant，并触发保存。"""
    # 注入流式客户端
    class _FakeChatCompletions2:
        def create(
            self,
            *,
            model: str,
            messages: list[dict],
            **kwargs: Any,
        ) -> Any:  # noqa: D401
            """仅支持 stream=True，返回可迭代流。"""
            assert kwargs.get("stream") is True
            return _FakeStream(["O", "K"])  # 产出两段，最终应拼为 "OK"

    class _FakeClient2:
        def __init__(self) -> None:
            self.chat = type("_CC", (), {"completions": _FakeChatCompletions2()})()

    g = AgentGateway()
    g.model_name = "fake"
    g.client = cast(Any, _FakeClient2())
    g._rag_service = cast(Any, _FakeRAG())

    class _SM:
        def __init__(self) -> None:
            self.saved: list[dict] | None = None

        def save_session(self, chat_history: list[dict]) -> None:
            """保存历史"""
            self.saved = list(chat_history)

    g._session_manager = cast(Any, _SM())

    pieces = list(g.send_message("hi", use_rag=False))
    assert pieces == ["O", "K"]                                  # 产出增量内容
    assert g.chat_history[-1]["content"] == "OK"                 # assistant 聚合为 OK
    assert cast(Any, g._session_manager).saved is not None       # 已触发保存


def test_clear_and_get_history_triggers_save() -> None:
    """clear_history 应清空历史并触发保存。"""
    g = AgentGateway()
    g.chat_history.extend([
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
    ])

    class _SM:
        def __init__(self) -> None:
            self.n: int = 0

        def save_session(self, chat_history: list[dict]) -> None:
            """保存历史会话"""
            self.n += 1
            assert chat_history == []                           # 被清空

    g._session_manager = cast(Any, _SM())
    g.clear_history()
    assert g.chat_history == []                                 # 内存历史为空
    assert cast(Any, g._session_manager).n == 1                 # 保存被调用一次

