from datetime import datetime, timedelta
from uuid import uuid4

from tinydb import TinyDB, Query

from .utility import get_file_path


# 已删除会话的保留天数
DELETED_SESSION_RETENTION_DAYS = 30


class SessionManager:
    """会话管理器（gateway内部组件）"""

    def __init__(self) -> None:
        """构造函数"""
        self.db_path = get_file_path("chat_sessions.json")
        self.db = TinyDB(str(self.db_path))
        self.sessions_table = self.db.table('sessions')
        self.messages_table = self.db.table('messages')
        self.current_session_id: str | None = None


        # 自动加载或创建默认会话
        self._ensure_current_session()

    def create_session(self, title: str = "新会话") -> str:
        """创建新会话"""
        session_id = str(uuid4())
        # 使用带毫秒的时间戳，避免重复
        now = datetime.now().isoformat(timespec='milliseconds')
        session_data = {
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
        session_id = self.get_current_session_id()

        message_data = {
            'session_id': session_id,
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(timespec='milliseconds')
        }

        self.messages_table.insert(message_data)

        # 更新会话的最后更新时间
        Session = Query()
        self.sessions_table.update({
            'updated_at': datetime.now().isoformat(timespec='milliseconds')
        }, Session.id == session_id)

    def get_current_history(self) -> list[dict[str, str]]:
        """获取当前会话的历史消息"""
        if not self.current_session_id:
            return []

        messages = self.messages_table.search(Query().session_id == self.current_session_id)
        messages.sort(key=lambda x: x['timestamp'])

        return [
            {'role': msg['role'], 'content': msg['content']}
            for msg in messages
        ]

    def get_all_sessions(self) -> list[dict]:
        """获取所有未删除的会话"""
        sessions = self.sessions_table.search(Query().deleted == False)
        return sorted(sessions, key=lambda x: x['updated_at'], reverse=True)

    def switch_session(self, session_id: str) -> bool:
        """切换到指定会话"""
        Session = Query()
        session = self.sessions_table.get(Session.id == session_id)

        if session and not session.get('deleted', False):
            self.current_session_id = session_id
            return True

        return False

    def update_session_title(self, session_id: str, title: str) -> bool:
        """更新会话标题"""
        Session = Query()
        result = self.sessions_table.update({
            'title': title,
            'updated_at': datetime.now().isoformat(timespec='milliseconds')
        }, Session.id == session_id)

        return len(result) > 0

    def delete_session(self, session_id: str) -> bool:
        """软删除会话"""
        Session = Query()
        result = self.sessions_table.update({
            'deleted': True,
            'updated_at': datetime.now().isoformat(timespec='milliseconds')
        }, Session.id == session_id)

        if len(result) > 0 and session_id == self.current_session_id:
            self.current_session_id = None

        return len(result) > 0

    def clear_current_session(self) -> None:
        """清空当前会话"""
        if self.current_session_id:
            Message = Query()
            self.messages_table.remove(Message.session_id == self.current_session_id)

    def new_session(self) -> str:
        """创建新会话并切换"""
        return self.create_session()

    def save_session(self, chat_history: list[dict[str, str]]) -> None:
        """保存会话历史（gateway接口）"""
        if not chat_history:
            return

        session_id = self.get_current_session_id()

        # 清空当前会话的消息
        Message = Query()
        self.messages_table.remove(Message.session_id == session_id)

        # 保存新的消息历史
        for message in chat_history:
            message_data = {
                'session_id': session_id,
                'role': message['role'],
                'content': message['content'],
                'timestamp': datetime.now().isoformat(timespec='milliseconds')
            }
            self.messages_table.insert(message_data)

        # 更新会话时间戳和自动生成标题
        Session = Query()
        update_data = {
            'updated_at': datetime.now().isoformat(timespec='milliseconds')
        }

        # 如果会话有内容，尝试自动生成标题
        if chat_history:
            # 获取当前会话信息
            session = self.sessions_table.get(Session.id == session_id)

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
        self.sessions_table.update(update_data, Session.id == session_id)

    def load_session(
        self,
        session_id: str | None = None
    ) -> list[dict[str, str]]:
        """加载会话历史（gateway接口）"""
        target_session_id = session_id or self.get_current_session_id()

        messages = self.messages_table.search(Query().session_id == target_session_id)
        messages.sort(key=lambda x: x['timestamp'])

        chat_history = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in messages
        ]

        return chat_history

    def _ensure_current_session(self) -> None:
        """确保有当前会话"""
        if not self.current_session_id:
            # 尝试获取最近的会话
            sessions = self.get_all_sessions()
            if sessions:
                self.current_session_id = sessions[0]['id']
            else:
                # 创建默认会话
                self.current_session_id = self.create_session("默认会话")

    def cleanup_deleted_sessions(self) -> int:
        """清理已删除的会话

        Returns:
            清理的会话数量
        """
        # 计算截止日期
        cutoff_date = (datetime.now() - timedelta(days=DELETED_SESSION_RETENTION_DAYS)).isoformat()

        # 查找需要删除的会话
        Session = Query()
        deleted_sessions = self.sessions_table.search(
            (Session.deleted == True) & (Session.updated_at < cutoff_date)
        )

        if not deleted_sessions:
            return 0

        # 删除会话及其消息
        count = 0
        for session in deleted_sessions:
            session_id = session['id']

            # 删除会话的消息
            Message = Query()
            self.messages_table.remove(Message.session_id == session_id)

            # 删除会话本身
            self.sessions_table.remove(Session.id == session_id)
            count += 1

        return count

    def restore_session(self, session_id: str) -> bool:
        """恢复已删除的会话

        Returns:
            是否成功恢复
        """
        Session = Query()
        result = self.sessions_table.update({
            'deleted': False,
            'updated_at': datetime.now().isoformat(timespec='milliseconds')
        }, Session.id == session_id)

        return len(result) > 0

    def get_deleted_sessions(self) -> list[dict]:
        """获取所有已删除的会话"""
        Session = Query()
        sessions = self.sessions_table.search(Session.deleted == True)
        return sorted(sessions, key=lambda x: x['updated_at'], reverse=True)

    def _permanent_delete_session(self, session_id: str) -> bool:
        """永久删除单个会话（内部方法）

        Args:
            session_id: 会话ID

        Returns:
            是否成功删除
        """
        # 确保会话存在且已被标记为删除
        Session = Query()
        session = self.sessions_table.get((Session.id == session_id) & (Session.deleted == True))

        if not session:
            return False

        # 删除会话的消息
        Message = Query()
        self.messages_table.remove(Message.session_id == session_id)

        # 删除会话本身
        self.sessions_table.remove(Session.id == session_id)

        return True

    def export_session(self, session_id: str | None = None) -> tuple[str, list[dict]]:
        """导出会话

        返回：(会话标题, 会话历史记录)
        """
        target_session_id = session_id or self.get_current_session_id()

        # 获取会话信息
        Session = Query()
        session = self.sessions_table.get(Session.id == target_session_id)
        if not session:
            return ("未知会话", [])

        # 获取会话消息
        messages = self.messages_table.search(Query().session_id == target_session_id)
        messages.sort(key=lambda x: x['timestamp'])

        # 格式化消息
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'role': msg['role'],
                'content': msg['content'],
                'timestamp': msg['timestamp']
            })

        return (session['title'], formatted_messages)
