from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Any

from tinydb import TinyDB, Query, where
from tinydb.table import Table

from .utility import get_file_path


# 已删除会话的保留天数
DELETED_SESSION_RETENTION_DAYS = 30


class SessionManager:
    """会话管理器（gateway内部组件）"""

    def __init__(self) -> None:
        """构造函数"""
        self.db_path: Path = get_file_path("chat_sessions.json")
        self.db: TinyDB = TinyDB(str(self.db_path))
        self.sessions_table: Table = self.db.table('sessions')
        self.messages_table: Table = self.db.table('messages')
        self.current_session_id: str | None = None

        # 自动加载或创建默认会话
        self._ensure_current_session()

    def _get_datetime(self) -> str:
        """返回当前时间（ISO8601，毫秒精度）。"""
        value: str = datetime.now().isoformat(timespec='milliseconds')
        return value

    def _get_session(self, session_id: str) -> Any:
        """获取单个会话记录。"""
        session: Any = self.sessions_table.get(Query().id == session_id)
        return session

    def _update_session(self, session_id: str, data: dict) -> bool:
        """更新会话字段。"""
        result: list = self.sessions_table.update(data, Query().id == session_id)
        success: bool = len(result) > 0
        return success

    def _search_sessions(self, expr) -> list[dict]:  # type: ignore[no-untyped-def]
        """按表达式查询会话列表。"""
        sessions: list = self.sessions_table.search(expr)
        return sessions

    def _get_messages(self, session_id: str) -> list[dict]:
        """获取指定会话的消息列表（按时间排序）。"""
        records: list = self.messages_table.search(Query().session_id == session_id)
        records.sort(key=lambda x: x['timestamp'])
        return records

    def _remove_messages(self, session_id: str) -> None:
        """删除指定会话的全部消息。"""
        self.messages_table.remove(Query().session_id == session_id)

    def _format_messages(self, records: list[dict]) -> list[dict[str, str]]:
        """将消息记录转为对外结构。"""
        items: list[dict[str, str]] = []
        for msg in records:
            items.append({'role': msg['role'], 'content': msg['content']})
        return items

    def create_session(self, title: str = "新会话") -> str:
        """创建新会话"""
        session_id: str = str(uuid4())
        # 使用带毫秒的时间戳，避免重复
        now: str = self._get_datetime()
        session_data: dict = {
            'id': session_id,
            'title': title,
            'created_at': now,
            'updated_at': now,
            'deleted': False
        }

        self.sessions_table.insert(session_data)
        self.current_session_id = session_id

        return session_id

    def get_current_session_id(self) -> str:
        """获取或创建当前会话ID"""
        if not self.current_session_id:
            self.current_session_id = self.create_session()
        return self.current_session_id

    def add_message(self, role: str, content: str) -> None:
        """添加消息到当前会话"""
        session_id: str = self.get_current_session_id()

        message_data: dict = {
            'session_id': session_id,
            'role': role,
            'content': content,
            'timestamp': self._get_datetime()
        }

        self.messages_table.insert(message_data)

        # 更新会话的最后更新时间
        self._update_session(session_id, {'updated_at': self._get_datetime()})

    def get_current_history(self) -> list[dict[str, str]]:
        """获取当前会话的历史消息"""
        if not self.current_session_id:
            return []

        messages: list = self._get_messages(self.current_session_id)
        formatted: list[dict[str, str]] = self._format_messages(messages)
        return formatted

    def get_all_sessions(self) -> list[dict]:
        """获取所有未删除的会话"""
        sessions: list = self.sessions_table.search(where('deleted') == False)  # noqa: E712
        ordered: list = sorted(sessions, key=lambda x: x['updated_at'], reverse=True)
        return ordered

    def switch_session(self, session_id: str) -> bool:
        """切换到指定会话"""
        session: Any = self._get_session(session_id)
        success: bool = False
        if session and not session.get('deleted', False):
            self.current_session_id = session_id
            success = True
        return success

    def update_session_title(self, session_id: str, title: str) -> bool:
        """更新会话标题"""
        data: dict = {'title': title, 'updated_at': self._get_datetime()}
        success: bool = self._update_session(session_id, data)
        return success

    def delete_session(self, session_id: str) -> bool:
        """软删除会话"""
        data: dict = {'deleted': True, 'updated_at': self._get_datetime()}
        success: bool = self._update_session(session_id, data)
        if success and session_id == self.current_session_id:
            self.current_session_id = None
        return success

    def save_session(self, chat_history: list[dict[str, str]]) -> None:
        """保存会话历史（gateway接口）"""
        if not chat_history:
            return

        session_id: str = self.get_current_session_id()

        # 清空当前会话的消息
        self._remove_messages(session_id)

        # 保存新的消息历史
        for message in chat_history:
            message_data: dict = {
                'session_id': session_id,
                'role': message['role'],
                'content': message['content'],
                'timestamp': self._get_datetime()
            }
            self.messages_table.insert(message_data)

        # 更新会话时间戳和自动生成标题
        update_data: dict = {'updated_at': self._get_datetime()}

        # 如果会话有内容，尝试自动生成标题
        if chat_history:
            # 获取当前会话信息
            session: Any = self._get_session(session_id)

            # 如果标题是默认的或者还没有设置自动标题
            if session and (session['title'] == "新会话" or session['title'] == "默认会话"):
                # 从用户第一条消息生成标题
                user_messages = [msg for msg in chat_history if msg['role'] == 'user']
                if user_messages:
                    # 取第一条用户消息的前20个字符作为标题
                    first_msg = user_messages[0]['content']
                    title = first_msg[:20] + ("..." if len(first_msg) > 20 else "")
                    update_data['title'] = title

        # 更新会话
        self._update_session(session_id, update_data)

    def load_session(
        self,
        session_id: str | None = None
    ) -> list[dict[str, str]]:
        """加载会话历史（gateway接口）"""
        if session_id:
            target_session_id: str = session_id
        else:
            target_session_id = self.get_current_session_id()
        messages: list = self._get_messages(target_session_id)
        chat_history: list[dict[str, str]] = self._format_messages(messages)
        return chat_history

    def _ensure_current_session(self) -> None:
        """确保有当前会话"""
        if not self.current_session_id:
            # 尝试获取最近的会话
            sessions: list = self.get_all_sessions()
            if sessions:
                self.current_session_id = sessions[0]['id']
            else:
                # 创建默认会话
                self.current_session_id = self.create_session("默认会话")

    def cleanup_deleted_sessions(self, force_all: bool = False) -> int:
        """清理已删除的会话

        Args:
            force_all: 是否强制清理所有已删除的会话（忽略30天限制）

        Returns:
            清理的会话数量
        """
        if force_all:
            deleted_sessions: list = self.sessions_table.search(where('deleted') == True)  # noqa: E712
            cutoff_date: str = (
                datetime.now() - timedelta(days=DELETED_SESSION_RETENTION_DAYS)
            ).isoformat()
            expr = (where('deleted') == True) & (where('updated_at') < cutoff_date)        # noqa: E712
            deleted_sessions = self.sessions_table.search(expr)

        if not deleted_sessions:
            count_empty: int = 0
            return count_empty

        # 删除会话及其消息
        count: int = 0
        for session in deleted_sessions:
            session_id: str = session['id']
            self._remove_messages(session_id)
            self.sessions_table.remove(Query().id == session_id)
            count += 1
        return count

    def restore_session(self, session_id: str) -> bool:
        """恢复已删除的会话

        Returns:
            是否成功恢复
        """
        data: dict = {'deleted': False, 'updated_at': self._get_datetime()}
        success: bool = self._update_session(session_id, data)
        return success

    def get_deleted_sessions(self) -> list[dict]:
        """获取所有已删除的会话"""
        sessions: list = self.sessions_table.search(where('deleted') == True)  # noqa: E712
        ordered: list = sorted(sessions, key=lambda x: x['updated_at'], reverse=True)
        return ordered

    def _permanent_delete_session(self, session_id: str) -> bool:
        """永久删除单个会话（内部方法）

        Args:
            session_id: 会话ID

        Returns:
            是否成功删除
        """
        # 确保会话存在且已被标记为删除
        session: Any = self._get_session(session_id)
        if not session or not session.get('deleted', False):
            return False

        # 删除会话的消息
        self._remove_messages(session_id)

        # 删除会话本身
        self.sessions_table.remove(Query().id == session_id)
        return True

    def export_session(self, session_id: str | None = None) -> tuple[str, list[dict]]:
        """导出会话

        返回：(会话标题, 会话历史记录)
        """
        if session_id:
            target_session_id: str = session_id
        else:
            target_session_id = self.get_current_session_id()

        # 获取会话信息
        session: Any = self._get_session(target_session_id)
        if not session:
            return ("未知会话", [])

        # 获取会话消息
        messages: list = self._get_messages(target_session_id)

        # 格式化消息
        formatted_messages: list = []
        for msg in messages:
            formatted_messages.append({
                'role': msg['role'],
                'content': msg['content'],
                'timestamp': msg['timestamp']
            })

        return (session['title'], formatted_messages)
