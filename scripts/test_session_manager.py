"""SessionManager 简单功能测试。
条件：
- 使用 monkeypatch 将 TinyDB 数据文件指向临时目录，互不干扰；
- 每个公开函数各 1 个最小用例（内部方法适量覆盖）。
期望：
- 基础增删改查与导出/清理行为正确。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from collections.abc import Callable

import pytest

from vnag.session_manager import SessionManager, DELETED_SESSION_RETENTION_DAYS


@pytest.fixture()
def make_manager(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[], SessionManager]:
    """返回一个工厂：为每个用例创建隔离的 SessionManager。"""

    def _factory() -> SessionManager:
        """创建并返回指向临时 TinyDB 文件的 SessionManager 实例。"""
        dbfile = tmp_path / "chat_sessions.json"

        def _fake_get_file_path(name: str) -> Path:  # noqa: D401
            return dbfile

        # 替换路径解析，确保 TinyDB 指向临时文件
        monkeypatch.setattr(
            "vnag.session_manager.get_file_path",
            _fake_get_file_path,
        )
        return SessionManager()

    return _factory


def test_create_and_get_current_session_id(
    make_manager: Callable[[], SessionManager],
) -> None:
    """初始化后应有默认会话，且能获取当前会话ID。"""
    sm = make_manager()
    sid = sm.get_current_session_id()
    assert isinstance(sid, str) and len(sid) > 0          # 返回字符串且非空


def test_add_and_get_history(
    make_manager: Callable[[], SessionManager],
) -> None:
    """新增消息后，历史应包含该消息。"""
    sm = make_manager()
    sm.add_message("user", "hi")
    hist = sm.get_current_history()
    assert hist == [{"role": "user", "content": "hi"}]  # 与新增内容一致


def test_get_all_sessions_and_switch(
    make_manager: Callable[[], SessionManager],
) -> None:
    """创建第二个会话，列表应≥2；可切换到该会话。"""
    sm = make_manager()
    first = sm.get_current_session_id()
    second = sm.create_session("S2")
    sessions = sm.get_all_sessions()
    assert len(sessions) >= 2                              # 至少两条会话
    assert sm.switch_session(first) is True                # 可切回第一个
    assert sm.switch_session(second) is True               # 可切到第二个


def test_update_and_delete_and_restore(
    make_manager: Callable[[], SessionManager],
) -> None:
    """更新标题→删除→恢复，应分别成功。"""
    sm = make_manager()
    sid = sm.get_current_session_id()
    assert sm.update_session_title(sid, "T") is True      # 标题更新成功
    assert sm.delete_session(sid) is True                  # 标记删除成功
    deleted = sm.get_deleted_sessions()
    assert any(s["id"] == sid for s in deleted)          # 在已删除列表中
    assert sm.restore_session(sid) is True                 # 恢复成功


def test_save_and_load_session(
    make_manager: Callable[[], SessionManager],
) -> None:
    """save_session 后，load_session 返回一致的消息内容。"""
    sm = make_manager()
    chat = [
        {"role": "user", "content": "Q"},
        {"role": "assistant", "content": "A"},
    ]
    sm.save_session(chat)
    loaded = sm.load_session()
    assert loaded == chat                                   # 全量覆盖保存


def test_cleanup_deleted_sessions(
    make_manager: Callable[[], SessionManager],
) -> None:
    """超过保留期的删除会话应被清理；force_all 忽略时间限制。"""
    sm = make_manager()
    # 创建两个会话并标记删除
    s1 = sm.create_session("S1")
    s2 = sm.create_session("S2")
    sm.delete_session(s1)
    sm.delete_session(s2)

    # 手动回退一个会话的 updated_at 超过保留期
    cutoff = datetime.now() - timedelta(
        days=DELETED_SESSION_RETENTION_DAYS + 1
    )
    old = cutoff.isoformat(timespec="milliseconds")
    from tinydb import Query

    Session = Query()
    sm.sessions_table.update(
        {"updated_at": old},
        Session.id == s1,
    )

    # 非强制清理：仅清理超期的
    n = sm.cleanup_deleted_sessions(force_all=False)
    assert n == 1                                           # 仅超期的被清理

    # 强制清理：清理剩余的
    n2 = sm.cleanup_deleted_sessions(force_all=True)
    assert n2 >= 1                                          # 强制清理剩余


def test_export_session(
    make_manager: Callable[[], SessionManager],
) -> None:
    """导出返回标题与消息。"""
    sm = make_manager()
    sm.add_message("user", "X")
    title, msgs = sm.export_session(None)
    assert isinstance(title, str) and len(msgs) >= 1        # 标题为字符串且有消息
